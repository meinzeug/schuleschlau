import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'learning_room_test.dart' as fixtures;

void main() {
  testWidgets('Older backend does not offer unsupported recovery', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    await fixtures.openRound(tester, server);
    expect(find.text('Rückmeldungen ansehen'), findsNothing);
  });

  testWidgets('Unread feedback is explicit, individual, and usable at 320 px', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.pending(answer: 'Meine Antwort');
    server.value['supports_feedback_recovery'] = true;
    server.value['feedback_recovery_available'] = true;
    final items = [
      {
        'attempt_id': 'first',
        'prompt': 'Erste Aufgabe',
        'answer': 'Antwort eins',
        'outcome': 'incorrect',
        'assisted': false,
      },
      {
        'attempt_id': 'second',
        'prompt': 'Zweite Aufgabe',
        'answer': 'Antwort zwei',
        'outcome': 'correct',
        'assisted': true,
      },
    ];
    final acknowledgements = <String>[];
    await fixtures.openRound(
      tester,
      server,
      textScale: 1.2,
      handle: (request) async {
        if (request.method == 'GET' &&
            request.url.path.endsWith('/feedback/recovery')) {
          return fixtures.jsonReply({'items': items, 'next_after': null});
        }
        if (request.method == 'POST' &&
            request.url.path.endsWith('/feedback/recovery/acknowledge')) {
          final id = (jsonDecode(request.body) as Map)['attempt_id'] as String;
          acknowledgements.add(id);
          items.removeWhere((item) => item['attempt_id'] == id);
          return fixtures.jsonReply({'acknowledged': true});
        }
        return server.handle(request);
      },
    );
    await fixtures.tapText(tester, 'Rückmeldungen ansehen');
    expect(
      find.text(
        'Die Reihenfolge ist nicht bekannt. Schau jede Rückmeldung einzeln an.',
      ),
      findsOneWidget,
    );
    expect(find.text('Deine Antwort: Antwort eins'), findsOneWidget);
    expect(acknowledgements, isEmpty);
    await tester.ensureVisible(find.text('Gelesen').first);
    await tester.tap(find.text('Gelesen').first);
    await tester.pumpAndSettle();
    expect(acknowledgements, ['first']);
    expect(find.text('Deine Antwort: Antwort eins'), findsNothing);
    expect(find.text('Deine Antwort: Antwort zwei'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Opening and closing leaves all markers unread', (tester) async {
    final server = fixtures.SavedRound();
    server.value['feedback_recovery_available'] = true;
    var writes = 0;
    await fixtures.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/feedback/recovery')) {
          return fixtures.jsonReply({
            'items': [
              {
                'attempt_id': 'first',
                'prompt': 'Frage',
                'answer': 'Antwort',
                'outcome': 'uncertain',
                'assisted': false,
              },
            ],
            'next_after': null,
          });
        }
        if (request.url.path.endsWith('/feedback/recovery/acknowledge')) {
          writes++;
        }
        return server.handle(request);
      },
    );
    await fixtures.tapText(tester, 'Rückmeldungen ansehen');
    await tester.tap(find.byTooltip('Schließen'));
    await tester.pumpAndSettle();
    expect(writes, 0);
  });

  testWidgets('Unsaved input remains after reviewing older feedback', (
    tester,
  ) async {
    final server = fixtures.SavedRound(
      questions: [fixtures.question('cat', type: 'short')],
    );
    server.value['feedback_recovery_available'] = true;
    await fixtures.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/feedback/recovery')) {
          return fixtures.jsonReply({
            'items': [
              {
                'attempt_id': 'first',
                'prompt': 'Frage',
                'answer': 'Antwort',
                'outcome': 'uncertain',
                'assisted': false,
              },
            ],
            'next_after': null,
          });
        }
        if (request.url.path.endsWith('/feedback/recovery/acknowledge')) {
          return fixtures.jsonReply({'acknowledged': true});
        }
        return server.handle(request);
      },
    );
    await tester.enterText(find.byType(TextField).first, 'Mein Entwurf');
    await fixtures.tapText(tester, 'Rückmeldungen ansehen');
    await fixtures.tapText(tester, 'Gelesen');
    await tester.tap(find.byTooltip('Schließen'));
    await tester.pumpAndSettle();
    expect(find.text('Mein Entwurf'), findsOneWidget);
    expect(server.answers, 0);
  });

  testWidgets('Further pages are deliberate and can return to the first', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.value['feedback_recovery_available'] = true;
    await fixtures.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.url.path.endsWith('/feedback/recovery')) {
          final next = request.url.queryParameters['after'] != null;
          return fixtures.jsonReply({
            'items': [
              {
                'attempt_id': next ? 'second' : 'first',
                'prompt': next ? 'Frage zwei' : 'Frage eins',
                'answer': 'Antwort',
                'outcome': 'incorrect',
                'assisted': false,
              },
            ],
            'next_after': next ? null : 'first',
          });
        }
        return server.handle(request);
      },
    );
    await fixtures.tapText(tester, 'Rückmeldungen ansehen');
    expect(find.text('Frage eins'), findsOneWidget);
    await fixtures.tapText(tester, 'Weitere anzeigen');
    expect(find.text('Frage zwei'), findsOneWidget);
    await fixtures.tapText(tester, 'Zur ersten Seite');
    expect(find.text('Frage eins'), findsOneWidget);
  });
}
