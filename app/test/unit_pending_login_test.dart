import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/unit_screen.dart';

import 'grouped_answer_unit_test.dart' as grouped;
import 'learning_room_test.dart' as room;

class SwitchableStorage extends FlutterSecureStorage {
  bool unavailable = true;

  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (unavailable) throw StateError('test storage unavailable');
    await super.write(key: key, value: value);
  }
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets('opening a round during login does not read or start time', (
    tester,
  ) async {
    final server = room.SavedRound();
    late int intent;
    final h = await room.openRound(
      tester,
      server,
      beforeMount: (state) => intent = state.beginAuthentication(),
    );
    expect(server.calls, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    h.state.cancelAuthentication(intent);
    await tester.pump(const Duration(seconds: 21));
    expect(server.calls, isEmpty);
    await room.tapText(tester, 'Runde neu laden');
    expect(server.calls.where((c) => c == 'GET /api/units/unit'), hasLength(1));
    expect(find.text('Was bedeutet cat?'), findsOneWidget);
  });

  testWidgets(
    'login protects unsent answer and prevents stale submission or time',
    (tester) async {
      final server = room.SavedRound(
        questions: [room.question('cat', type: 'short')],
      );
      server.value['learning_session'] = grouped.savedSession();
      final h = await room.openRound(tester, server);
      final field = find.byType(TextField);
      await tester.enterText(field, 'Eigene Antwort');
      await tester.pump();
      final action = tester.widget<FilledButton>(
        find.byKey(const ValueKey('learning-primary-action')),
      );
      expect(action.onPressed, isNotNull);
      final prior = server.calls.length;
      final intent = h.state.beginAuthentication();
      action.onPressed!();
      await tester.pump();
      expect(server.answers, 0);
      expect(find.text('Anmeldung läuft …'), findsOneWidget);
      expect(find.text('Eigene Antwort'), findsNothing);
      await tester.pump(const Duration(seconds: 21));
      expect(server.calls.length, prior);
      expect(server.answers, 0);
      h.state.cancelAuthentication(intent);
      await tester.pump();
      expect(server.calls.length, prior);
      await tester.tap(find.text('Runde neu laden'));
      for (var i = 0; i < 20; i++) {
        await tester.pump(const Duration(milliseconds: 50));
      }
      final dynamic visibleState = tester.state(find.byType(UnitScreen));
      expect(
        visibleState.resumingAuthentication,
        false,
        reason:
            'calls: ${server.calls}; loading: ${visibleState.loading}; draft: ${visibleState.savingDraft}',
      );
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'Eigene Antwort',
      );
      expect(server.answers, 0);
    },
  );

  testWidgets('a delayed old answer action cannot submit after reopening', (
    tester,
  ) async {
    final server = room.SavedRound(
      questions: [room.question('cat', type: 'short')],
    );
    server.value['learning_session'] = grouped.savedSession();
    final h = await room.openRound(tester, server);
    await tester.enterText(find.byType(TextField), 'Katze');
    await tester.pump();
    final heartbeat = Completer<http.Response>();
    server.delayedHeartbeat = heartbeat;
    tester
        .widget<FilledButton>(
          find.byKey(const ValueKey('learning-primary-action')),
        )
        .onPressed!();
    await tester.pump();
    expect(server.delayedHeartbeat, isNull);
    final intent = h.state.beginAuthentication();
    h.state.cancelAuthentication(intent);
    await tester.pump();
    await tester.tap(find.text('Runde neu laden'));
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    heartbeat.complete(
      room.jsonReply({'status': 'active', 'active_seconds_approx': 120}),
    );
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(server.answers, 0);
    expect(server.calls.where((call) => call.endsWith('/answer')), isEmpty);
    expect(find.text('Was bedeutet cat?'), findsOneWidget);
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      'Katze',
    );
  });
  testWidgets('a failed local save keeps the answer for a deliberate retry', (
    tester,
  ) async {
    final storage = SwitchableStorage();
    final server = room.SavedRound(
      questions: [room.question('cat', type: 'short')],
    );
    server.value['learning_session'] = grouped.savedSession();
    final h = await room.openRound(tester, server, storage: storage);
    await tester.enterText(find.byType(TextField), 'Meine Antwort');
    await tester.pump();
    final intent = h.state.beginAuthentication();
    h.state.cancelAuthentication(intent);
    await tester.pump();
    await tester.tap(find.text('Runde neu laden'));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(
      find.text(
        'Deine Eingabe ist noch nicht gespeichert. Versuche es erneut.',
      ),
      findsOneWidget,
    );
    expect(find.text('Was bedeutet cat?'), findsNothing);
    expect(server.answers, 0);
    storage.unavailable = false;
    await tester.tap(find.text('Runde neu laden'));
    for (var i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      'Meine Antwort',
    );
    expect(server.answers, 0);
  });
}
