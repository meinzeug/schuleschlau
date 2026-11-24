import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
// Pinned plugin codec; the synthetic export is intercepted without a file.
// ignore: implementation_imports
import 'package:file_saver/src/messages.g.dart' show FileSaverHostApi;
import 'package:schulpilot/parent_export_dialog.dart';

import 'parent_saved_tools_ux90_test.dart' as saved;
import 'parent_messages_ux88_test.dart' show tap;

Future<void> mountExport(WidgetTester tester, saved.Fixture f) async {
  await f.mount(
    tester,
    (context) => TextButton(
      onPressed: () => showParentChildExport(context, f.state, {
        'id': 'synthetic-child',
        'display_name': 'Künstliches Kind',
      }),
      child: const Text('Öffnen'),
    ),
  );
  await tap(tester, find.text('Öffnen'));
}

void main() {
  testWidgets('open child export closes when a new login starts', (
    tester,
  ) async {
    final f = saved.Fixture();
    await mountExport(tester, f);
    expect(find.text('Daten von Künstliches Kind exportieren'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.requests, isEmpty);
  });

  for (final change in ['login-intent', 'session-token']) {
    for (final success in [true, false]) {
      testWidgets(
        'late ${success ? 'export' : 'error'} is discarded after $change',
        (tester) async {
          final f = saved.Fixture();
          final response = Completer<http.Response>();
          f.respond = (_) => response.future;
          var saves = 0;
          final channel = BasicMessageChannel<Object?>(
            'dev.flutter.pigeon.file_saver.FileSaverHostApi.saveAs',
            FileSaverHostApi.pigeonChannelCodec,
          );
          if (!kIsWeb) {
            tester.binding.defaultBinaryMessenger
                .setMockDecodedMessageHandler<Object?>(channel, (_) async {
                  saves++;
                  return ['synthetic-memory-only'];
                });
            addTearDown(
              () => tester.binding.defaultBinaryMessenger
                  .setMockDecodedMessageHandler<Object?>(channel, null),
            );
          }
          await mountExport(tester, f);
          await tester.ensureVisible(
            find.text('Kinderexport ausdrücklich speichern'),
          );
          await tester.tap(find.text('Kinderexport ausdrücklich speichern'));
          await tester.pump();
          expect(f.requests, hasLength(1));
          expect(f.requests.single.method, 'GET');
          if (change == 'login-intent') {
            f.state.beginAuthentication();
          } else {
            f.state.api.token = 'another-synthetic-session';
          }
          response.complete(
            success
                ? http.Response.bytes([80, 75, 3, 4], 200)
                : http.Response(
                    '{"detail":"Alter privater Fehler"}',
                    503,
                    headers: {'content-type': 'application/json'},
                  ),
          );
          await tester.pumpAndSettle();
          expect(saves, 0);
          expect(find.text('Alter privater Fehler'), findsNothing);
          expect(
            find.textContaining('Der Kinderexport wurde gespeichert'),
            findsNothing,
          );
        },
      );
    }
  }

  testWidgets(
    'a current explicit export still sends exactly one save request',
    (tester) async {
      final f = saved.Fixture();
      f.respond = (_) async => http.Response.bytes([80, 75, 3, 4], 200);
      var saves = 0;
      final channel = BasicMessageChannel<Object?>(
        'dev.flutter.pigeon.file_saver.FileSaverHostApi.saveAs',
        FileSaverHostApi.pigeonChannelCodec,
      );
      tester.binding.defaultBinaryMessenger
          .setMockDecodedMessageHandler<Object?>(channel, (_) async {
            saves++;
            return ['synthetic-memory-only'];
          });
      addTearDown(
        () => tester.binding.defaultBinaryMessenger
            .setMockDecodedMessageHandler<Object?>(channel, null),
      );
      await mountExport(tester, f);
      await tap(tester, find.text('Kinderexport ausdrücklich speichern'));
      expect(f.requests, hasLength(1));
      expect(saves, 1);
      expect(
        find.textContaining('Der Kinderexport wurde gespeichert'),
        findsOneWidget,
      );
    },
    skip: kIsWeb,
  );
}
