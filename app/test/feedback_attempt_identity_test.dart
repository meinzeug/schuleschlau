import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'learning_room_test.dart' as fixtures;

void main() {
  testWidgets('Feedback shows details for its own saved attempt', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Erste künstliche Antwort');
    final question = (server.value['questions'] as List).first as Map;
    question['attempts'] = [
      {
        'id': 'saved-attempt',
        'answer': 'Erste künstliche Antwort',
        'outcome': 'incorrect',
        'assisted': false,
        'evaluation': {'reason': 'Begründung zum ersten Versuch.'},
      },
      {
        'id': 'different-attempt',
        'answer': 'Zweite künstliche Antwort',
        'outcome': 'incorrect',
        'assisted': true,
        'evaluation': {'reason': 'Begründung zum anderen Versuch.'},
      },
    ];
    await fixtures.openRound(tester, server);

    expect(find.text('Begründung zum ersten Versuch.'), findsOneWidget);
    expect(find.text('Begründung zum anderen Versuch.'), findsNothing);
  });

  testWidgets('Missing feedback attempt never borrows another assessment', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Meine gespeicherte Antwort', outcome: 'uncertain');
    server.value['supports_recheck'] = true;
    server.value['supports_recheck_attempt_id'] = true;
    final question = (server.value['questions'] as List).first as Map;
    question['attempts'] = [
      {
        'id': 'different-attempt',
        'answer': 'Andere Antwort',
        'outcome': 'uncertain',
        'assisted': true,
        'evaluation': {'reason': 'Begründung eines anderen Versuchs.'},
      },
    ];
    await fixtures.openRound(tester, server);

    expect(find.text('Meine gespeicherte Antwort'), findsOneWidget);
    expect(find.text('Begründung eines anderen Versuchs.'), findsNothing);
    expect(find.text('Antwort erneut prüfen'), findsNothing);
  });

  testWidgets('Older feedback does not offer rechecking the later answer', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Frühere Antwort', outcome: 'uncertain');
    server.value['supports_recheck'] = true;
    server.value['supports_recheck_attempt_id'] = true;
    final question = (server.value['questions'] as List).first as Map;
    question['attempts'] = [
      {
        'id': 'saved-attempt',
        'answer': 'Frühere Antwort',
        'outcome': 'uncertain',
        'assisted': false,
        'evaluation': {'reason': 'Ältere Bewertung.'},
      },
      {
        'id': 'different-attempt',
        'answer': 'Spätere Antwort',
        'outcome': 'uncertain',
        'assisted': true,
        'evaluation': {'reason': 'Andere Bewertung.'},
      },
    ];
    await fixtures.openRound(tester, server);

    expect(find.text('Ältere Bewertung.'), findsOneWidget);
    expect(find.text('Andere Bewertung.'), findsNothing);
    expect(find.text('Antwort erneut prüfen'), findsNothing);
  });

  testWidgets('An old API offers help instead of an unbound recheck', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Meine Antwort', outcome: 'uncertain');
    server.value['supports_recheck'] = true;
    final question = (server.value['questions'] as List).first as Map;
    question['attempts'] = [
      {
        'id': 'saved-attempt',
        'answer': 'Meine Antwort',
        'outcome': 'uncertain',
        'assisted': false,
      },
    ];
    await fixtures.openRound(tester, server);
    expect(find.text('Antwort erneut prüfen'), findsNothing);
    expect(find.textContaining('nicht sicher erneut prüfen'), findsOneWidget);
    expect(find.text('Mit der Lernhilfe klären'), findsOneWidget);
  });

  testWidgets(
    'Old feedback cannot open a tutor after an authentication intent',
    (tester) async {
      final server = fixtures.SavedRound();
      server.pending(answer: 'Meine Antwort', outcome: 'uncertain');
      server.value['supports_recheck'] = true;
      final question = (server.value['questions'] as List).first as Map;
      question['attempts'] = [
        {
          'id': 'saved-attempt',
          'answer': 'Meine Antwort',
          'outcome': 'uncertain',
          'assisted': false,
        },
      ];
      final harness = await fixtures.openRound(tester, server);
      final action = tester
          .widget<TextButton>(
            find.widgetWithText(TextButton, 'Mit der Lernhilfe klären'),
          )
          .onPressed!;
      final before = server.calls.length;
      final intent = harness.state.beginAuthentication();
      action();
      await tester.pump();
      harness.state.cancelAuthentication(intent);
      action();
      await tester.pump();
      expect(server.calls.length, before);
      expect(find.byType(BottomSheet), findsNothing);
      await harness.close();
    },
  );

  testWidgets('Current unclear feedback opens its editable tutor question', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Meine Antwort', outcome: 'uncertain');
    server.value['supports_recheck'] = true;
    final question = (server.value['questions'] as List).first as Map;
    question['attempts'] = [
      {
        'id': 'saved-attempt',
        'answer': 'Meine Antwort',
        'outcome': 'uncertain',
        'assisted': false,
      },
    ];
    var reads = 0;
    final harness = await fixtures.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.method == 'GET' &&
            request.url.path.endsWith('/tutor/questions')) {
          reads++;
          return http.Response(
            jsonEncode({'questions': [], 'next_cursor': null}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }
        return server.handle(request);
      },
    );
    final button = find.widgetWithText(TextButton, 'Mit der Lernhilfe klären');
    await tester.ensureVisible(button);
    await tester.tap(button);
    await tester.pumpAndSettle();
    expect(reads, 1);
    expect(find.byType(BottomSheet), findsOneWidget);
    expect(
      tester.widget<TextField>(find.byType(TextField).last).controller!.text,
      contains('Meine Antwort'),
    );
    await harness.close();
  });

  testWidgets(
    'A changed attempt keeps feedback when the server rejects recheck',
    (tester) async {
      final server = fixtures.SavedRound();
      server.pending(answer: 'Meine Antwort', outcome: 'uncertain');
      server.value['supports_recheck'] = true;
      server.value['supports_recheck_attempt_id'] = true;
      final question = (server.value['questions'] as List).first as Map;
      question['attempts'] = [
        {
          'id': 'saved-attempt',
          'answer': 'Meine Antwort',
          'outcome': 'uncertain',
          'assisted': false,
        },
      ];
      var calls = 0;
      await fixtures.openRound(
        tester,
        server,
        handle: (request) async {
          if (request.url.path.endsWith('/recheck')) {
            calls++;
            expect(request.body, '{"attempt_id":"saved-attempt"}');
            return fixtures.jsonReply({
              'detail': 'Die Antwort hat sich geändert.',
            }, 409);
          }
          return server.handle(request);
        },
      );
      await fixtures.tapText(tester, 'Antwort erneut prüfen');
      expect(calls, 1);
      expect(find.text('Meine Antwort'), findsOneWidget);
      expect(
        find.textContaining('Die Antwort hat sich geändert.'),
        findsOneWidget,
      );
      expect(server.acknowledgements, 0);
    },
  );
}
