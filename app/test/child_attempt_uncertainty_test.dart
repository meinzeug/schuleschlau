import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/coaching_panel.dart';
import 'package:schulpilot/math_content.dart';
import 'package:schulpilot/saved_attempt_tools.dart';

import 'unit_learning_time_test.dart' as fixture;
import 'child_local_tools_ux88_test.dart' as f;

Json attempt({
  bool assisted = false,
  bool uncertain = false,
  Object? created = 1700000000,
}) => {
  'id': 'synthetic-attempt',
  'answer': 'Katze',
  'outcome': 'correct',
  'assisted': assisted,
  'created': created,
  'evaluation': {'independence_uncertain': uncertain},
  'assessment_history': <Json>[],
};
Json question(List<Json> attempts) => {
  'id': 'first',
  'prompt': 'Was bedeutet cat?',
  'attempts': attempts,
};

void main() {
  test('saved result categories retain help and do not upgrade uncertain independence', () {
    expect(
      storedQuestionCategory(question([attempt(uncertain: true)])),
      'uncertain',
    );
    expect(
      storedQuestionCategory(
        question([attempt(assisted: true, uncertain: true)]),
      ),
      'assisted',
    );
    expect(
      storedQuestionCategory(
        question([attempt(assisted: true, created: null)]),
      ),
      'assisted',
    );
    expect(
      storedQuestionCategory(question([attempt(created: null)])),
      'uncertain',
    );
    expect(storedQuestionCategory(question([attempt()])), 'independent');
    expect(
      storedQuestionCategory(
        question([attempt(created: '2026-10-23T09:00:00Z')]),
      ),
      'independent',
    );
    expect(
      storedQuestionCategory(question([attempt(), attempt()])),
      'assisted',
    );
    expect(
      storedQuestionCategory(question([attempt(), attempt(uncertain: true)])),
      'assisted',
    );
    expect(
      storedQuestionCategory(question([attempt(created: null), attempt()])),
      'uncertain',
    );
  });
  for (final mode in ['marker', 'unknown-time', 'help', 'independent']) {
    testWidgets('vocabulary result uses actual independent evidence: $mode', (
      tester,
    ) async {
      final data = fixture.unit(status: 'completed');
      data['round_kind'] = 'vocabulary';
      data['vocabulary_result'] = {'skills': <String>[]};
      data['questions'][0]['attempts'] = [
        attempt(
          assisted: mode == 'help',
          uncertain: mode == 'marker' || mode == 'help',
          created: mode == 'unknown-time' ? null : 1700000000,
        ),
      ];
      await fixture.openUnit(
        tester,
        (_) async => http.Response(
          jsonEncode(data),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      );
      final count = mode == 'independent' ? 1 : 0;
      expect(
        find.byWidgetPredicate(
          (w) =>
              w is MathText &&
              (w.data?.contains(
                    '$count beim ersten Versuch ohne Hilfe richtig',
                  ) ??
                  false),
        ),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets(
    'child result card keeps actual support visible when the marker is set',
    (tester) async {
      final item = question([attempt(assisted: true, uncertain: true)]);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: RoundQuestionCards(questions: [item]),
            ),
          ),
        ),
      );
      expect(
        find.textContaining('Mit Hilfe oder erneut richtig'),
        findsOneWidget,
      );
      expect(find.textContaining('Richtig · allein gelöst?'), findsNothing);
    },
  );
  testWidgets('unknown retry order retains help without inventing sequence', (
    tester,
  ) async {
    final first = attempt(assisted: true, created: null);
    final second = {...attempt(), 'id': 'retry'};
    await f.show(
      tester,
      RoundAnswerExplorer(
        questions: [
          question([first, second]),
        ],
      ),
    );
    await f.tap(tester, find.text('1 noch unklar'));
    expect(
      find.text('Die Reihenfolge der Versuche ist nicht sicher bekannt.'),
      findsOneWidget,
    );
    await f.tap(tester, find.text('Alle 2 gespeicherten Versuche'));
    expect(find.text('Gespeicherter Versuch'), findsNWidgets(2));
    expect(find.textContaining('Unterstützung erfasst'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'stored answer tools do not imply chronology when a time is unknown',
    (tester) async {
      final data = question([
        attempt(assisted: true, created: null),
        attempt(),
      ]);
      await f.show(
        tester,
        SavedAttemptTools(questions: [data], sourceKey: 'test'),
      );
      await f.tap(tester, find.text('Versuche nach Zeit und Eingabe ansehen'));
      expect(find.textContaining('Gespeicherte Antwort 1'), findsOneWidget);
      expect(find.textContaining('Zeitpunkt nicht verfügbar'), findsOneWidget);
      await f.tap(tester, find.text('Zwei Versuche dieser Frage vergleichen'));
      expect(
        find.text('Die Reihenfolge der Versuche ist nicht sicher bekannt.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
