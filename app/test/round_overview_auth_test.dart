import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/learning_round_overview.dart';

void main() {
  final questions = <Json>[
    {'id': 'q1', 'prompt': 'Erste künstliche Frage', 'closed': true},
    {'id': 'q2', 'prompt': 'Zweite künstliche Frage', 'closed': false},
  ];
  AppState actor(List<http.Request> calls) => AppState(
    api: Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        calls.add(request);
        throw StateError('No request is expected');
      }),
    ),
  )..user = {'id': 'synthetic-child', 'role': 'child'};
  Widget screen(AppState state, {GlobalKey<NavigatorState>? navigator}) =>
      MaterialApp(
        navigatorKey: navigator,
        home: Scaffold(
          body: LearningRoundOverviewButton(
            state: state,
            unitId: 'synthetic-unit',
            questions: questions,
            currentQuestionId: 'q2',
            completed: (question) => question['closed'] == true,
          ),
        ),
      );

  testWidgets('new login closes private overview and stale buttons are inert', (
    tester,
  ) async {
    final calls = <http.Request>[];
    final state = actor(calls);
    addTearDown(state.dispose);
    final navigator = GlobalKey<NavigatorState>();
    await tester.pumpWidget(screen(state, navigator: navigator));
    await tester.tap(find.byKey(const ValueKey('round-overview-open')));
    await tester.pumpAndSettle();
    expect(find.text('Erste künstliche Frage'), findsOneWidget);
    final staleClose = tester
        .widget<IconButton>(
          find.byWidgetPredicate(
            (widget) =>
                widget is IconButton && widget.tooltip == 'Zur Aufgabe zurück',
          ),
        )
        .onPressed!;
    final staleBack = tester
        .widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Zur aktuellen Aufgabe'),
        )
        .onPressed!;
    final revision = state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Erste künstliche Frage'), findsNothing);
    unawaited(
      showDialog<void>(
        context: navigator.currentState!.context,
        builder: (_) => const AlertDialog(title: Text('Neuer Dialog')),
      ),
    );
    await tester.pumpAndSettle();
    staleClose();
    staleBack();
    await tester.pumpAndSettle();
    expect(find.text('Neuer Dialog'), findsOneWidget);
    state.cancelAuthentication(revision);
    await tester.pumpAndSettle();
    expect(find.text('Erste künstliche Frage'), findsNothing);
    expect(calls, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('overview stays closed while new login is pending', (
    tester,
  ) async {
    final calls = <http.Request>[];
    final state = actor(calls);
    addTearDown(state.dispose);
    state.beginAuthentication();
    await tester.pumpWidget(screen(state));
    final button = tester.widget<IconButton>(
      find.byKey(const ValueKey('round-overview-open')),
    );
    expect(button.onPressed, isNull);
    expect(find.text('Erste künstliche Frage'), findsNothing);
    expect(calls, isEmpty);
    expect(tester.takeException(), isNull);
  });
}
