import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/api.dart';

import 'learning_room_test.dart' as room;

void main() {
  testWidgets('a shown hint explains support and survives reopening', (
    tester,
  ) async {
    final server = room.SavedRound();
    final question = (server.value['questions'] as List).first as Json;
    Future<http.Response> handle(http.Request request) async {
      if (request.url.path.endsWith('/hint')) {
        server.calls.add('${request.method} ${request.url.path}');
        server.hints++;
        final text = server.hints == 1
            ? 'Denke an das Wort.'
            : 'Cat heißt Katze.';
        final shown = (question['shown_hints'] as List? ?? <Json>[]);
        question['shown_hints'] = [
          ...shown,
          {'number': server.hints, 'text': text},
        ];
        question['hints_used'] = server.hints;
        return room.jsonReply({
          'hint': text,
          'hints_used': server.hints,
          'exhausted': false,
        });
      }
      return server.handle(request);
    }

    final first = await room.openRound(tester, server, handle: handle);
    expect(find.text('Deine Antwort zählt mit Tipp.'), findsNothing);
    await room.tapText(tester, 'Hilfe');
    expect(find.text('Deine Antwort zählt mit Tipp.'), findsOneWidget);
    await room.tapText(tester, 'Noch ein Tipp');
    expect(find.text('Cat heißt Katze.'), findsOneWidget);
    expect(server.hints, 2);
    expect(server.answers, 0);
    await first.close();

    await room.openRound(tester, server, handle: handle);
    expect(find.text('Cat heißt Katze.'), findsOneWidget);
    expect(find.text('Deine Antwort zählt mit Tipp.'), findsOneWidget);
    expect(server.hints, 2);
    expect(server.answers, 0);
  });

  testWidgets('saved correct feedback names the hint after reopening', (
    tester,
  ) async {
    final server = room.SavedRound()
      ..pending(answer: 'Katze', outcome: 'correct', status: 'active');
    final q = (server.value['questions'] as List).first as Json;
    q['attempts'] = [
      {
        'id': 'saved-attempt',
        'answer': 'Katze',
        'outcome': 'correct',
        'assisted': true,
        'evaluation': {
          'support_reasons': ['hint'],
        },
      },
    ];
    server.value['pending_feedback']['assisted'] = true;
    final first = await room.openRound(tester, server);
    expect(find.text('Mit Tipp gelöst. Gut gemacht!'), findsOneWidget);
    expect(find.text('Richtig!'), findsOneWidget);
    await first.close();

    await room.openRound(tester, server);
    expect(find.text('Mit Tipp gelöst. Gut gemacht!'), findsOneWidget);
    expect(find.text('Richtig!'), findsOneWidget);
    expect(server.answers, 0);
    expect(server.hints, 0);
    expect(server.calls.where((call) => call.contains('/answer')), isEmpty);
  });

  testWidgets('correct answer after a hint shows supported feedback', (
    tester,
  ) async {
    final server = room.SavedRound();
    Future<http.Response> handle(http.Request request) async {
      final response = await server.handle(request);
      if (!request.url.path.endsWith('/answer')) return response;
      final q = (server.value['questions'] as List).first as Json;
      final attempt = (q['attempts'] as List).last as Json;
      attempt['id'] = 'attempt-1';
      attempt['evaluation'] = {
        'support_reasons': ['hint'],
      };
      return room.jsonReply({
        'unit': server.value,
        ...server.value['pending_feedback'] as Map,
      });
    }

    await room.openRound(tester, server, handle: handle);
    await room.tapText(tester, 'Hilfe');
    await room.tapText(tester, 'Katze');
    await room.tapText(tester, 'Antwort prüfen');
    expect(find.text('Richtig!'), findsOneWidget);
    expect(find.text('Mit Tipp gelöst. Gut gemacht!'), findsOneWidget);
    expect(server.hints, 1);
    expect(server.answers, 1);
  });
}
