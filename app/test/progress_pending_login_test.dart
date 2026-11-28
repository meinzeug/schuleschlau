import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/progress_screen.dart';
import 'package:schulpilot/ui.dart';

import 'progress_cards_ux88_test.dart' as fixture;

void main() {
  testWidgets('opening progress during login does not load private results', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          return fixture.reply(fixture.data(request));
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'kid'};
    final intent = state.beginAuthentication();
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => ProgressScreen(state, childId: 'kid'),
        ),
      ],
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    expect(find.text('Öffne den Lernstand erneut.'), findsOneWidget);
    expect(find.text('Zurück zur Übersicht'), findsOneWidget);
  });

  testWidgets('delayed progress cannot reappear after a login starts', (
    tester,
  ) async {
    final response = Completer<http.Response>();
    final requests = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) {
          requests.add(request);
          return response.future;
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'kid'};
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => ProgressScreen(state, childId: 'kid'),
        ),
      ],
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    expect(requests, hasLength(1));
    final intent = state.beginAuthentication();
    await tester.pump();
    response.complete(fixture.reply(fixture.data(requests.single)));
    await tester.pump();
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(find.text('Mathematik'), findsNothing);
    expect(find.text('Öffne den Lernstand erneut.'), findsOneWidget);
    expect(requests, hasLength(1));
  });
  testWidgets(
    'login closes the old page picker and ignores its captured action',
    (tester) async {
      final requests = <http.Request>[];
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            return fixture.reply(fixture.data(request, pages: 3));
          }),
        ),
      )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'kid'};
      final router = GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => ProgressScreen(state, childId: 'kid'),
          ),
        ],
      );
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      final staleCard = tester
          .widget<ActionPanel>(find.byType(ActionPanel).first)
          .onPressed!;
      await tester.ensureVisible(find.text('Seite 1 von 3'));
      await tester.tap(find.text('Seite 1 von 3'));
      await tester.pumpAndSettle();
      expect(find.text('Seite auswählen'), findsOneWidget);
      final stale = tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Seite öffnen'),
          )
          .onPressed!;
      final staleCancel = tester
          .widget<TextButton>(find.widgetWithText(TextButton, 'Abbrechen'))
          .onPressed!;
      await tester.enterText(find.byType(TextField).last, '2');
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Seite auswählen'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      stale();
      staleCancel();
      staleCard();
      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(requests, hasLength(1));
      expect(find.text('Öffne den Lernstand erneut.'), findsOneWidget);
    },
  );
}
