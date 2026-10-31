import 'package:flutter_test/flutter_test.dart';

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
