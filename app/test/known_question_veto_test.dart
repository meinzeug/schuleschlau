import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/api.dart';

import 'learning_room_test.dart' as room;

Future<void> tap(WidgetTester tester, String text) async {
  await tester.ensureVisible(find.text(text));
  await tester.tap(find.text(text));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 450));
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('child can set aside known question without an answer', (
    tester,
  ) async {
    final server = room.SavedRound();
    Json? submitted;
    final handle = await room.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/learning-session') &&
            request.method == 'GET') {
          return room.jsonReply({'revision': 3});
        }
        if (request.url.path.endsWith('/learning-session/skip') &&
            request.method == 'POST') {
          submitted = Json.from(jsonDecode(request.body));
          server.value['status'] = 'paused';
          return room.jsonReply(server.value);
        }
        return server.handle(request);
      },
    );
    await tap(tester, 'Hilfe');
    await tap(tester, 'Mehr Hilfe');
    await tap(tester, 'Das haben wir schon gemacht');
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    expect(
      find.textContaining('zählt noch nicht als Nachweis'),
      findsOneWidget,
    );
    expect(submitted, isNull);
    await tap(tester, 'Aufgabe zur Seite legen');
    await tester.pumpAndSettle();
    expect(submitted?['question_id'], 'cat');
    expect(submitted?['reason'], 'already_done');
    expect(submitted?['revision'], 3);
    expect(submitted?['request_key'], isA<String>());
    expect(server.answers, 0);
    await handle.close();
  });

  testWidgets('cancelling the child veto does not send a skip', (tester) async {
    final server = room.SavedRound();
    var skips = 0;
    final handle = await room.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/learning-session/skip')) skips++;
        return server.handle(request);
      },
    );
    await tap(tester, 'Hilfe');
    await tap(tester, 'Mehr Hilfe');
    await tap(tester, 'Das haben wir schon gemacht');
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    await tap(tester, 'Abbrechen');
    await tester.pumpAndSettle();
    expect(skips, 0);
    expect(server.answers, 0);
    await handle.close();
  });

  testWidgets('child sets a round aside and explicitly restores it', (
    tester,
  ) async {
    final server = room.SavedRound();
    server.value['round_deferred'] = false;
    Json? deferred, restored;
    final handle = await room.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/learning-session') &&
            request.method == 'GET') {
          return room.jsonReply({
            'revision': server.value['round_deferred'] == true ? 4 : 3,
          });
        }
        if (request.url.path.endsWith('/learning-session/defer')) {
          deferred = Json.from(jsonDecode(request.body));
          server.value['round_deferred'] = true;
          server.value['status'] = 'paused';
          return room.jsonReply(server.value);
        }
        if (request.url.path.endsWith('/learning-session/restore')) {
          restored = Json.from(jsonDecode(request.body));
          server.value['round_deferred'] = false;
          return room.jsonReply(server.value);
        }
        return server.handle(request);
      },
    );
    await tester.tap(find.byTooltip('Mehr zur Runde'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 450));
    await tap(tester, 'Diese Runde haben wir schon gemacht');
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 200));
    }
    expect(find.textContaining('Elternaufträge bleiben offen'), findsOneWidget);
    await tap(tester, 'Runde zur Seite legen');
    await tester.pumpAndSettle();
    expect(deferred?['revision'], 3);
    expect(deferred?['reason'], 'already_done');
    expect(server.hints, 0);
    expect(find.text('Runde zur Seite gelegt'), findsOneWidget);
    expect(server.answers, 0);
    await tap(tester, 'Runde wieder aufnehmen');
    await tester.pumpAndSettle();
    expect(restored?['revision'], 4);
    expect(find.text('Lernen fortsetzen'), findsOneWidget);
    expect(server.answers, 0);
    await handle.close();
  });

  testWidgets('veto menu remains reachable at 320 pixels with enlarged text', (
    tester,
  ) async {
    final server = room.SavedRound();
    server.value['round_deferred'] = false;
    final handle = await room.openRound(tester, server, textScale: 2);
    expect(find.byTooltip('Mehr zur Runde'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.byTooltip('Mehr zur Runde'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 450));
    expect(find.text('Diese Runde haben wir schon gemacht'), findsOneWidget);
    expect(server.hints, 0);
    expect(server.answers, 0);
    expect(tester.takeException(), isNull);
    await handle.close();
  });

  for (final width in [320.0, 390.0]) {
    testWidgets(
      'secondary options stay explicit at $width pixels and 2x text',
      (tester) async {
        final server = room.SavedRound();
        server.value['round_deferred'] = false;
        final handle = await room.openRound(tester, server, textScale: 2);
        tester.view.physicalSize = Size(width, 844);
        await tester.pump();
        await tester.tap(find.byTooltip('Mehr zur Runde'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 450));
        expect(
          find.text('Diese Runde haben wir schon gemacht'),
          findsOneWidget,
        );
        expect(find.text('Das haben wir schon gemacht'), findsOneWidget);
        expect(find.text('Erklärung ansehen'), findsOneWidget);
        expect(find.text('Passendes Erklärvideo'), findsNothing);
        expect(find.text('Für später aufheben'), findsNothing);
        expect(server.hints, 0);
        expect(server.answers, 0);
        await tap(tester, 'Weitere Möglichkeiten');
        expect(find.text('Passendes Erklärvideo'), findsOneWidget);
        expect(find.text('Für später aufheben'), findsOneWidget);
        expect(find.text('Die Aufgabe passt nicht'), findsOneWidget);
        expect(find.text('Vorwissen & Lernziele'), findsOneWidget);
        expect(server.hints, 0);
        expect(server.answers, 0);
        expect(tester.takeException(), isNull);
        await handle.close();
      },
    );
  }
}
