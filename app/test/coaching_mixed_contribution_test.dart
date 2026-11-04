import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/coaching_panel.dart';
import 'package:schulpilot/math_content.dart';

import 'coach_practice_failure_ux_test.dart' as saved;
import 'coaching_cards_142_test.dart' as cards;

void main() {
  testWidgets('A contribution goal does not advertise missing recall days', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: LearningProgressPanel({
              'subject': 'Ethik',
              'topic': 'Perspektiven',
              'learning_goals': [
                {
                  'label': 'Eigene Gedanken',
                  'assessment_applicable': false,
                  'successful_check_days': 0,
                },
              ],
            }),
          ),
        ),
      ),
    );
    await saved.click(tester, 'Was bleibt über mehrere Tage hängen?');
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is MathText &&
            widget.data == 'Eigener Beitrag · ohne Leistungsbewertung',
      ),
      findsOneWidget,
    );
    expect(find.text('0 spätere Prüftage'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Open contributions remain ungraded in both review views', (
    tester,
  ) async {
    for (final role in ['child', 'parent']) {
      final value = cards.unit();
      (value['coaching']['report']['question_reviews'] as List).add({
        'question_id': 'contribution',
        'outcome': 'uncertain',
        'assessment_kind': 'reflection',
        'feedback': 'Dein eigener Beitrag ist gespeichert und wird nicht als richtig oder falsch bewertet.',
      });
      final before = jsonEncode(value);
      final h = saved.Harness(data: value);
      if (role == 'parent') {
        h.state.user = {'id': 'synthetic-parent', 'role': 'parent'};
      }
      await h.open(tester, width: 390);
      expect(find.text('1 eigener Beitrag'), findsOneWidget);
      await saved.click(
        tester,
        role == 'child' ? 'Mein Rückblick' : 'Vollständigen Rückblick ansehen',
      );
      await saved.click(tester, 'Rückmeldung zu jeder Aufgabe');
      expect(
        find.byWidgetPredicate(
          (w) => w is MathText && w.data == 'Dein eigener Beitrag ist gespeichert und wird nicht als richtig oder falsch bewertet.',
        ),
        findsOneWidget,
      );
      expect(jsonEncode(value), before);
      expect(h.calls, isEmpty);
      expect(tester.takeException(), isNull);
      await h.close(tester);
    }
  });
}
