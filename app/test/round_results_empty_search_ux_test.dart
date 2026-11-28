import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/coaching_panel.dart';
import 'package:schulpilot/learning_tool_scope.dart';

import 'child_local_tools_ux88_test.dart' as fixture;

List<Map<String, dynamic>> questions() => [
  {
    'id': 'one',
    'prompt': 'Erste Aufgabe',
    'attempts': [
      {'answer': '5', 'outcome': 'incorrect', 'assisted': false},
    ],
  },
  {
    'id': 'two',
    'prompt': 'Zweite Aufgabe',
    'attempts': [
      {'answer': '6', 'outcome': 'correct', 'assisted': true},
    ],
  },
];

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Empty result search retains the local sort at $width / $scale×',
      (tester) async {
        final data = questions();
        final original = jsonEncode(data);
        final state = fixture.account(
          (_) async => throw StateError('no network'),
        );
        await fixture.show(
          tester,
          LearningToolScope(
            state: state,
            sourceKey: 'synthetic-results',
            builder: (_) => RoundAnswerExplorer(questions: data, state: state),
          ),
          size: Size(width, 844),
          scale: scale,
        );
        await fixture.tap(tester, find.text('Alle Antworten (2)'));
        await fixture.tap(
          tester,
          find.text('Versuche nach Zeit und Eingabe ansehen'),
        );
        await fixture.tap(
          tester,
          find.text('Neueste datierte Versuche zuerst'),
        );
        final control = find.widgetWithText(
          SwitchListTile,
          'Neueste datierte Versuche zuerst',
        );
        expect(tester.widget<SwitchListTile>(control).value, isTrue);
        final input = fixture.input('In diesen gespeicherten Aufgaben suchen');
        await tester.enterText(input, 'kein Treffer');
        await tester.pumpAndSettle();
        expect(
          find.textContaining('Keine gespeicherte Aufgabe passt'),
          findsOneWidget,
        );
        expect(
          find.text('Versuche nach Zeit und Eingabe ansehen'),
          findsNothing,
        );
        expect(
          find.text(
            'Letzte gespeicherte Antwort je Aufgabe · ohne Versuchsfilter',
          ),
          findsNothing,
        );
        await fixture.tap(tester, find.byTooltip('Aufgabensuche leeren'));
        expect(tester.widget<TextField>(input).controller!.text, isEmpty);
        expect(find.text('Erste Aufgabe'), findsWidgets);
        if (control.evaluate().isEmpty) {
          await fixture.tap(
            tester,
            find.text('Versuche nach Zeit und Eingabe ansehen'),
          );
        }
        expect(tester.widget<SwitchListTile>(control).value, isTrue);
        expect(jsonEncode(data), original);
        expect(tester.takeException(), isNull);
      },
    );
  }

  for (final login in [true, false]) {
    testWidgets(
      'Old search reset is inert after ${login ? 'sign-in' : 'account replacement'}',
      (tester) async {
        final state = fixture.account(
          (_) async => throw StateError('no network'),
        );
        await fixture.show(
          tester,
          LearningToolScope(
            state: state,
            sourceKey: 'synthetic-results',
            builder: (_) =>
                RoundAnswerExplorer(questions: questions(), state: state),
          ),
        );
        await fixture.tap(tester, find.text('Alle Antworten (2)'));
        final input = fixture.input('In diesen gespeicherten Aufgaben suchen');
        await tester.enterText(input, 'geheim');
        await tester.pumpAndSettle();
        final controller = tester.widget<TextField>(input).controller!;
        final reset = tester
            .widget<IconButton>(
              find.byWidgetPredicate(
                (widget) =>
                    widget is IconButton &&
                    widget.tooltip == 'Aufgabensuche leeren',
              ),
            )
            .onPressed!;
        if (login) {
          final intent = state.beginAuthentication();
          reset();
          state.cancelAuthentication(intent);
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        reset();
        expect(controller.text, 'geheim');
        state.refreshState();
        await tester.pumpAndSettle();
        if (!login) expect(find.text('Erste Aufgabe'), findsNothing);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
