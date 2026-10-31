// Local responses only: a missing or temporarily inaccessible job is not a new request.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as common;
import 'learning_preparation_child_errors_132_test.dart' as fixture;

void main() {
  for (final response in [
    (404, 'Dieser Auftrag ist nicht mehr vorhanden.'),
    (409, 'Die Lernquelle wurde geändert. Bitte prüfe sie erneut.'),
    (
      429,
      'Neue KI-Verarbeitung ist durch das Aufruf- oder Kostenlimit begrenzt.',
    ),
  ]) {
    testWidgets('a ${response.$1} status read still offers saved rounds', (
      tester,
    ) async {
      final screen = fixture.PreparationFixture(
        response.$2,
        status: response.$1,
      );
      await screen.mount(tester);
      expect(find.text(response.$2), findsOneWidget);
      if (response.$1 == 404) {
        expect(find.text('Vorbereitung nicht gefunden.'), findsOneWidget);
        expect(find.text('Status neu laden'), findsNothing);
        expect(
          find.widgetWithText(FilledButton, 'Gespeicherte Runden ansehen'),
          findsOneWidget,
        );
        expect(find.text('Zur Startseite'), findsOneWidget);
      } else {
        expect(find.text('Status neu laden'), findsOneWidget);
      }
      await screen.assertSavedExitWithoutRetry(tester);
    });
  }

  testWidgets('a queued round uses one short status and keeps the home exit', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = common.account((request) async {
      requests.add(request);
      return common.reply({'kind': 'unit', 'status': 'queued'});
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
        ),
      ],
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    await tester.pump();
    expect(find.text('Deine Runde wartet.'), findsOneWidget);
    expect(
      find.text('Die Vorbereitung geht auch ohne offene App weiter.'),
      findsOneWidget,
    );
    expect(find.text('Zur Startseite'), findsOneWidget);
    expect(find.text('Status neu laden'), findsNothing);
    expect(find.text('Gespeicherte Runden ansehen'), findsNothing);
    expect(requests, hasLength(1));
    expect(requests.single.method, 'GET');
  });

  testWidgets(
    'a network failure keeps the saved-rounds exit without creating work',
    (tester) async {
      final requests = <http.Request>[];
      final state = common.account((request) async {
        requests.add(request);
        throw http.ClientException('synthetic connection failure');
      });
      final router = GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => LearningPreparationScreen(
              state,
              childId: 'child',
              jobId: 'job',
            ),
          ),
          GoRoute(
            path: '/learn/child',
            builder: (_, _) =>
                const Scaffold(body: Text('Gespeicherte künstliche Runden')),
          ),
        ],
      );
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox.shrink());
        router.dispose();
        state.dispose();
      });
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      expect(find.text('Status neu laden'), findsOneWidget);
      await tester.ensureVisible(find.text('Gespeicherte Runden ansehen'));
      await tester.tap(find.text('Gespeicherte Runden ansehen'));
      await tester.pumpAndSettle();
      expect(find.text('Gespeicherte künstliche Runden'), findsOneWidget);
      expect(requests, hasLength(1));
      expect(requests.single.method, 'GET');
      expect(tester.takeException(), isNull);
    },
  );
}
