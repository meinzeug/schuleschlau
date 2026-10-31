import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/feedback_recovery_sheet.dart';

import 'learning_room_test.dart' as fixtures;

void main() {
  testWidgets('Starts recovery before loading and retries a failed start', (
    tester,
  ) async {
    var beginCalls = 0;
    var listCalls = 0;
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        if (request.url.path.endsWith('/feedback/recovery/begin')) {
          beginCalls++;
          if (beginCalls == 1) {
            return fixtures.jsonReply({
              'detail': 'Bitte erneut versuchen',
            }, 503);
          }
          return fixtures.jsonReply({'started': true});
        }
        listCalls++;
        return fixtures.jsonReply({'items': [], 'next_after': null});
      }),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: FeedbackRecoverySheet(
            api: api,
            unitId: 'unit',
            isCurrent: () => true,
            onChanged: () {},
            onRequestStarted: (_) {},
            onClose: () {},
            supportsBegin: true,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(beginCalls, 1);
    expect(listCalls, 0);
    expect(find.text('Erneut versuchen'), findsOneWidget);
    await tester.tap(find.text('Erneut versuchen'));
    await tester.pumpAndSettle();
    expect(beginCalls, 2);
    expect(listCalls, 1);
    expect(find.text('Keine ungelesenen Rückmeldungen.'), findsOneWidget);
  });

  testWidgets(
    '320 × 568 and 200% text keeps long entries and actions reachable',
    (tester) async {
      tester.view.physicalSize = const Size(320, 568);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var acknowledgements = 0;
      final longText = List.filled(503, 'a').join();
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'POST') {
            acknowledgements++;
            return fixtures.jsonReply({'acknowledged': true});
          }
          return fixtures.jsonReply({
            'items': [
              {
                'attempt_id': 'first',
                'prompt': longText,
                'answer': longText,
                'outcome': 'incorrect',
                'assisted': false,
              },
            ],
            'next_after': null,
          });
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context)
                .copyWith(textScaler: const TextScaler.linear(2)),
            child: child!,
          ),
          home: Scaffold(
            body: FeedbackRecoverySheet(
              api: api,
              unitId: 'unit',
              isCurrent: () => true,
              onChanged: () {},
              onRequestStarted: (_) {},
              onClose: () {},
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      for (
        var i = 0;
        i < 100 && find.text('Gelesen').hitTestable().evaluate().isEmpty;
        i++
      ) {
        await tester.drag(find.byType(ListView), const Offset(0, -350));
        await tester.pump();
      }
      expect(find.text('Gelesen').hitTestable(), findsOneWidget);
      await tester.tap(find.text('Gelesen'));
      await tester.pumpAndSettle();
      expect(acknowledgements, 1);
      expect(tester.takeException(), isNull);
    },
  );

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

  testWidgets(
    'Closing while acknowledgement is in flight reloads after it commits',
    (tester) async {
      final server = fixtures.SavedRound();
      server.pending(answer: 'Vorherige Antwort');
      server.value['feedback_recovery_available'] = true;
      final response = Completer<http.Response>();
      var unitReads = 0;
      await fixtures.openRound(
        tester,
        server,
        handle: (request) async {
          if (request.method == 'GET' &&
              request.url.path == '/api/units/unit') {
            unitReads++;
          }
          if (request.method == 'GET' &&
              request.url.path.endsWith('/feedback/recovery')) {
            return fixtures.jsonReply({
              'items': [
                {
                  'attempt_id': 'first',
                  'prompt': 'Frage',
                  'answer': 'Vorherige Antwort',
                  'outcome': 'incorrect',
                  'assisted': false,
                },
              ],
              'next_after': null,
            });
          }
          if (request.url.path.endsWith('/feedback/recovery/acknowledge')) {
            return response.future;
          }
          return server.handle(request);
        },
      );
      await fixtures.tapText(tester, 'Rückmeldungen ansehen');
      final readsBefore = unitReads;
      await tester.tap(find.text('Gelesen'));
      await tester.pump();
      await tester.tap(find.byTooltip('Schließen'));
      await tester.pump(const Duration(milliseconds: 300));
      expect(unitReads, readsBefore);
      server.value['pending_feedback'] = null;
      server.value['feedback_recovery_available'] = false;
      response.complete(fixtures.jsonReply({'acknowledged': true}));
      await tester.pumpAndSettle();
      expect(unitReads, greaterThan(readsBefore));
      expect(find.text('Rückmeldungen ansehen'), findsNothing);
    },
  );

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

  testWidgets(
    'After a timeout a saved draft survives and recovery can be reopened',
    (tester) async {
      final server = fixtures.SavedRound(
        questions: [fixtures.question('cat', type: 'short')],
      );
      server.value['feedback_recovery_available'] = true;
      var lateCommit = false;
      var listReads = 0;
      await fixtures.openRound(
        tester,
        server,
        handle: (request) async {
          if (request.method == 'GET' &&
              request.url.path.endsWith('/feedback/recovery')) {
            listReads++;
            return fixtures.jsonReply({
              'items': lateCommit
                  ? []
                  : [
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
            return fixtures.jsonReply({'detail': 'Zeitüberschreitung'}, 504);
          }
          return server.handle(request);
        },
      );
      await tester.enterText(find.byType(TextField).first, 'Mein Entwurf');
      await fixtures.tapText(tester, 'Rückmeldungen ansehen');
      await fixtures.tapText(tester, 'Gelesen');
      expect(find.textContaining('Zeitüberschreitung'), findsOneWidget);
      await tester.tap(find.byTooltip('Schließen'));
      await tester.pumpAndSettle();
      expect(find.text('Mein Entwurf'), findsOneWidget);
      lateCommit = true;
      await fixtures.tapText(tester, 'Rückmeldungen ansehen');
      expect(listReads, 2);
      expect(find.text('Keine ungelesenen Rückmeldungen.'), findsOneWidget);
      await tester.tap(find.byTooltip('Schließen'));
      await tester.pumpAndSettle();
      expect(find.text('Mein Entwurf'), findsOneWidget);
      expect(server.answers, 0);
    },
  );

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

  testWidgets('An empty later page does not say earlier entries are read', (
    tester,
  ) async {
    final server = fixtures.SavedRound();
    server.value['feedback_recovery_available'] = true;
    await fixtures.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.method == 'GET' &&
            request.url.path.endsWith('/feedback/recovery')) {
          final later = request.url.queryParameters['after'] != null;
          return fixtures.jsonReply({
            'items': [
              {
                'attempt_id': later ? 'second' : 'first',
                'prompt': later ? 'Frage zwei' : 'Frage eins',
                'answer': 'Antwort',
                'outcome': 'incorrect',
                'assisted': false,
              },
            ],
            'next_after': later ? null : 'first',
          });
        }
        if (request.url.path.endsWith('/feedback/recovery/acknowledge')) {
          return fixtures.jsonReply({'acknowledged': true});
        }
        return server.handle(request);
      },
    );
    await fixtures.tapText(tester, 'Rückmeldungen ansehen');
    await fixtures.tapText(tester, 'Weitere anzeigen');
    await fixtures.tapText(tester, 'Gelesen');
    expect(find.text('Keine ungelesenen Rückmeldungen.'), findsNothing);
    expect(
      find.text('Auf dieser Seite sind keine weiteren Rückmeldungen.'),
      findsOneWidget,
    );
    await fixtures.tapText(tester, 'Zur ersten Seite');
    expect(find.text('Frage eins'), findsOneWidget);
  });
}
