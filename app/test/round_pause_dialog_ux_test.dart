import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'adaptive_learning_test.dart' as adaptive;
import 'learning_room_test.dart' as room;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Unsaved input warning fits at $width / $scale× with keyboard',
      (tester) async {
        final server = room.SavedRound(
          questions: [room.question('cat', type: 'short')],
        );
        server.value['learning_session'] = adaptive.session();
        await room.openRound(
          tester,
          server,
          height: 568,
          textScale: scale,
          handle: (http.Request request) async {
            if (request.method == 'PUT') {
              return room.jsonReply({'detail': 'Künstlich offline'}, 503);
            }
            return server.handle(request);
          },
        );
        tester.view.physicalSize = Size(width, 568);
        await tester.pump();
        await tester.enterText(find.byType(TextField).first, 'Mein Entwurf');
        await tester.pump(const Duration(milliseconds: 900));
        tester.view.viewInsets = const FakeViewPadding(bottom: 220);
        addTearDown(tester.view.resetViewInsets);
        await tester.tap(find.byTooltip('Lernrunde verlassen'));
        await tester.pumpAndSettle();
        expect(
          find.text(
            'Deine letzte Eingabe ist noch nicht sicher auf dem Server und kann verloren gehen. Geprüfte Antworten bleiben erhalten.',
          ),
          findsOneWidget,
        );
        final stay = find.text('Hier bleiben');
        expect(stay.hitTestable(), findsOneWidget);
        expect(find.text('Pause machen').hitTestable(), findsOneWidget);
        await tester.tap(stay);
        await tester.pumpAndSettle();
        expect(find.text('Mein Entwurf'), findsOneWidget);
        expect(server.answers, 0);
        expect(server.calls.where((call) => call.endsWith('/pause')), isEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }

  for (final login in [true, false]) {
    testWidgets(
      'Stale pause confirmation cannot act after ${login ? 'sign-in' : 'account change'}',
      (tester) async {
        final server = room.SavedRound(
          questions: [room.question('cat', type: 'short')],
        );
        server.value['learning_session'] = adaptive.session(
          answer: 'Gespeicherter Entwurf',
        );
        final harness = await room.openRound(
          tester,
          server,
          handle: (request) async {
            if (request.method == 'PUT') {
              return room.jsonReply(server.value['learning_session']);
            }
            return server.handle(request);
          },
        );
        await tester.tap(find.byTooltip('Lernrunde verlassen'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 500));
        expect(
          find.text(
            'Deine Eingabe ist gespeichert. Du kannst später hier weiterlernen.',
          ),
          findsOneWidget,
        );
        final action = tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Pause machen'),
            )
            .onPressed!;
        final before = server.calls.length;
        if (login) {
          final intent = harness.state.beginAuthentication();
          action();
          harness.state.cancelAuthentication(intent);
        } else {
          harness.state.user = {
            'id': 'other',
            'role': 'child',
            'child_id': 'other',
          };
        }
        action();
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 500));
        expect(server.calls.where((call) => call.endsWith('/pause')), isEmpty);
        expect(server.calls, hasLength(before));
        expect(server.answers, 0);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'A deliberate pause keeps saved input without an answer or invented time',
    (tester) async {
      final server = room.SavedRound(
        questions: [room.question('cat', type: 'short')],
      );
      server.value['learning_session'] = adaptive.session(
        answer: 'Gespeicherter Entwurf',
      );
      final heartbeats = <Map<String, dynamic>>[];
      await room.openRound(
        tester,
        server,
        handle: (request) async {
          if (request.url.path.endsWith('/heartbeat')) {
            heartbeats.add(Map<String, dynamic>.from(jsonDecode(request.body)));
          }
          if (request.method == 'PUT') {
            return room.jsonReply(server.value['learning_session']);
          }
          return server.handle(request);
        },
      );
      await tester.tap(find.byTooltip('Lernrunde verlassen'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Pause machen'));
      await tester.pumpAndSettle();
      expect(find.text('Startseite'), findsOneWidget);
      expect(
        server.calls.where((call) => call.endsWith('/pause')),
        hasLength(1),
      );
      expect(server.answers, 0);
      expect(
        server.value['learning_session']['working_memory']['draft']['answer'],
        'Gespeicherter Entwurf',
      );
      expect(
        heartbeats.every(
          (beat) => beat.keys.toSet().difference({'baseline'}).isEmpty,
        ),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
