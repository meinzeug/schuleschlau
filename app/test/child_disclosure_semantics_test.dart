import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/answer_writing_tools.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/child_today_widgets.dart';
import 'package:schulpilot/child_section_ui.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets('child filter reports whether its options are expanded', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: const Scaffold(
            body: ChildFilterTools(
              summary: 'Alle',
              filtered: false,
              child: Text('Filteroption'),
            ),
          ),
        ),
      );
      final control = find.byKey(const ValueKey('child-mobile-filter-toggle'));
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.tap(control);
      await tester.pumpAndSettle();
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(find.text('Filteroption'), findsOneWidget);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('an active child filter remains named and expandable', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: const Scaffold(
            body: ChildFilterTools(
              summary: 'Mathematik',
              filtered: true,
              child: Text('Filteroption'),
            ),
          ),
        ),
      );
      final control = find.byKey(const ValueKey('child-mobile-filter-toggle'));
      final data = tester.getSemantics(control).getSemanticsData();
      expect(data.label, contains('Filter aktiv'));
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.tap(control);
      await tester.pumpAndSettle();
      expect(find.text('Filteroption'), findsOneWidget);
      expect(tester.takeException(), isNull);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('round details report their expansion on the action', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: ChildTodayHero(
              eyebrow: 'Heute',
              title: 'Deine Runde',
              subtitle: 'Ein Beispiel',
              action: const SizedBox(),
              details: const Text('Deine Details'),
            ),
          ),
        ),
      );
      final control = find.byKey(const ValueKey('today-round-details'));
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.tap(control);
      await tester.pumpAndSettle();
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(find.text('Deine Details'), findsOneWidget);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('writing tools report expansion without changing the answer', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final calls = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request);
          throw StateError('The writing tools must stay local.');
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child'};
    final input = TextEditingController(text: 'Meine Antwort');
    try {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: AnswerWritingTools(
              state: state,
              controller: input,
              sourceKey: 'synthetic-source',
              enabled: true,
              isCurrent: () => true,
              maxLength: 500,
            ),
          ),
        ),
      );
      final control = find.byKey(const ValueKey('writing-tools-toggle'));
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.tap(control);
      await tester.pumpAndSettle();
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(input.text, 'Meine Antwort');
      expect(calls, isEmpty);
    } finally {
      await tester.pumpWidget(const SizedBox());
      input.dispose();
      state.dispose();
      semantics.dispose();
    }
  });
}
