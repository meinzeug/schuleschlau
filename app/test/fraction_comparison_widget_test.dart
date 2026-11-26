import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/fraction_comparison_widget.dart';
import 'package:schulpilot/learning_graphic_scope.dart';

import 'learning_scene_player_test.dart' as support;

Map<String, dynamic> step() => {
  'reference': {'id': 'math.fraction.comparison', 'version': 1},
  'disclosure': 'solution',
  'presentation': {
    'version': 1,
    'evidence_kind': 'knowledge',
    'blocks': [
      for (final pair in [
        [1, 3],
        [3, 4],
        [4, 12],
        [9, 12],
      ])
        {
          'kind': 'fraction',
          'disclosure': 'solution',
          'labels': <String>[],
          'connections': <String>[],
          'marks': <String>[],
          'numbers': pair,
          'variant': '',
          'unit': '',
        },
    ],
  },
};

void main() {
  for (final width in [320.0, 390.0, 1280.0]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets('Comparison is legible and interactive at $width/$scale', (
        tester,
      ) async {
        support.size(tester, Size(width, 844));
        var phase = 'initial';
        await tester.pumpWidget(
          support.host(
            StatefulBuilder(
              builder: (context, setState) => LearningGraphicScope(
                index: 0,
                phase: phase,
                onChanged: (_, value) => setState(() => phase = value),
                child: FractionComparisonWidget(step: step()),
              ),
            ),
            size: Size(width, 844),
            scale: scale,
            reduced: true,
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text('1 / 3'), findsOneWidget);
        expect(find.text('3 / 4'), findsOneWidget);
        await support.tapVisible(tester, find.text('Gleicher Nenner'));
        expect(find.text('4 / 12'), findsOneWidget);
        expect(find.text('9 / 12'), findsOneWidget);
        expect(phase, 'comparison-common');
        await support.tapVisible(tester, find.text('Brüche'));
        expect(find.text('1 / 3'), findsOneWidget);
        expect(phase, 'comparison-original');
        expect(tester.takeException(), isNull);
      });
    }
  }

  test(
    'Only a complete, arithmetically correct disclosed comparison is accepted',
    () {
      final value = step();
      expect(FractionComparisonWidget.supports(value), isTrue);
      for (final change in ['hidden', 'wrong', 'other', 'negative', 'extra']) {
        final bad = jsonDecode(jsonEncode(value)) as Map<String, dynamic>;
        final blocks = bad['presentation']['blocks'] as List;
        switch (change) {
          case 'hidden':
            bad['disclosure'] = 'given';
          case 'wrong':
            blocks[2]['numbers'] = [5, 12];
          case 'other':
            bad['reference']['id'] = 'math.fraction.part_whole';
          case 'negative':
            blocks[0]['numbers'] = [-1, 3];
          case 'extra':
            blocks[0]['labels'] = ['unverified'];
        }
        expect(FractionComparisonWidget.supports(bad), isFalse, reason: change);
      }
    },
  );

  testWidgets(
    'Account changes hide the comparison and exploration sends no requests',
    (tester) async {
      final requests = <http.Request>[];
      final state = support.actor(requests);
      await tester.pumpWidget(
        support.host(FractionComparisonWidget(step: step(), state: state)),
      );
      await tester.pumpAndSettle();
      await support.tapVisible(tester, find.text('Gleicher Nenner'));
      expect(requests, isEmpty);
      state.user = {'id': 'another-child', 'role': 'child'};
      state.refreshState();
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('fraction-comparison')), findsNothing);
      expect(requests, isEmpty);
    },
  );
  testWidgets('A saved common-denominator view is restored without a write', (
    tester,
  ) async {
    final changes = <String>[];
    await tester.pumpWidget(
      support.host(
        LearningGraphicScope(
          index: 0,
          phase: 'comparison-common',
          onChanged: (_, value) => changes.add(value),
          child: FractionComparisonWidget(step: step()),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('4 / 12'), findsOneWidget);
    expect(find.text('9 / 12'), findsOneWidget);
    expect(changes, isEmpty);
  });
}
