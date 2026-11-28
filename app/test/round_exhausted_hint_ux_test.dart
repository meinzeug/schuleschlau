import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'learning_room_test.dart' as room;

Future<http.Response> hintResponse(
  room.SavedRound server,
  http.Request request,
) {
  if (request.url.path.endsWith('/hint')) {
    server.calls.add('${request.method} ${request.url.path}');
    server.hints++;
    return Future.value(
      room.jsonReply({
        'hint': 'Denke an das Wort.',
        'hints_used': 1,
        'exhausted': true,
      }),
    );
  }
  return server.handle(request);
}

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets('Exhausted help stays concise at $width px and $scale×', (
      tester,
    ) async {
      final server = room.SavedRound();
      await room.openRound(
        tester,
        server,
        textScale: scale,
        handle: (request) => hintResponse(server, request),
      );
      tester.view.physicalSize = Size(width, 844);
      await tester.pumpAndSettle();
      await room.tapText(tester, 'Hilfe');
      expect(find.text('Denke an das Wort.'), findsOneWidget);
      expect(find.text('Deine Antwort zählt mit Tipp.'), findsOneWidget);
      expect(
        find.text('Alle Tipps gesehen. Unter „Mehr Hilfe“ geht es weiter.'),
        findsOneWidget,
      );
      expect(find.text('Noch ein Tipp'), findsNothing);
      expect(find.text('Mehr Hilfe'), findsOneWidget);
      await tester.ensureVisible(find.text('Mehr Hilfe'));
      await tester.tap(find.text('Mehr Hilfe'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));
      expect(find.text('Erklärung ansehen'), findsOneWidget);
      await tester.ensureVisible(find.text('Zurück zur Aufgabe'));
      await tester.tap(find.text('Zurück zur Aufgabe'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 500));
      await room.tapText(tester, 'Zur eigenen Eingabe');
      expect(server.hints, 1);
      expect(server.answers, 0);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets(
    'Three saved hints remain readable after reopening without a request',
    (tester) async {
      final server = room.SavedRound();
      final question = (server.value['questions'] as List).first as Map;
      question['shown_hints'] = [
        {'number': 1, 'text': 'Erster Tipp'},
        {'number': 2, 'text': 'Zweiter Tipp'},
        {'number': 3, 'text': 'Dritter Tipp'},
      ];
      question['hints_used'] = 3;
      final harness = await room.openRound(tester, server);
      expect(find.text('Dritter Tipp'), findsOneWidget);
      expect(find.text('Noch ein Tipp'), findsNothing);
      expect(find.text('Deine Antwort zählt mit Tipp.'), findsOneWidget);
      final chooser = find.byType(DropdownButtonFormField<int>);
      await tester.ensureVisible(chooser);
      await tester.tap(chooser);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Tipp 1').last);
      await tester.pumpAndSettle();
      expect(find.text('Erster Tipp'), findsOneWidget);
      expect(server.hints, 0);
      expect(server.answers, 0);
      await harness.close();
    },
  );

  for (final login in [true, false]) {
    testWidgets(
      'An old help action is inert after ${login ? 'sign-in' : 'account replacement'}',
      (tester) async {
        final server = room.SavedRound();
        final harness = await room.openRound(
          tester,
          server,
          handle: (request) => hintResponse(server, request),
        );
        await room.tapText(tester, 'Hilfe');
        final action = tester
            .widget<TextButton>(find.widgetWithText(TextButton, 'Mehr Hilfe'))
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
        await tester.pumpAndSettle();
        expect(server.calls, hasLength(before));
        expect(server.answers, 0);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
