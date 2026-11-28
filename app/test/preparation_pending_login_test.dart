import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as f;

void main() {
  testWidgets('opening a preparation during login requires deliberate reload', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(320, 600);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final requests = <http.Request>[];
    final state = f.account((r) async {
      requests.add(r);
      return f.reply({
        'kind': 'unit',
        'status': 'completed',
        'result': {'unit_id': 'ready'},
      });
    });
    final intent = state.beginAuthentication();
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
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pump(const Duration(seconds: 4));
    expect(requests, isEmpty);
    await tester.tap(find.text('Status neu laden'));
    await tester.pumpAndSettle();
    expect(requests.map((r) => r.method), ['GET']);
    expect(find.text('Deine Runde ist bereit.'), findsOneWidget);
  });

  testWidgets('old ready action cannot start a unit during login', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account((r) async {
      requests.add(r);
      return f.reply({
        'kind': 'unit',
        'status': 'completed',
        'result': {'unit_id': 'ready'},
      });
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
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    final action = tester.widget<ActionButton>(
      find.widgetWithText(ActionButton, 'Los geht’s'),
    );
    final intent = state.beginAuthentication();
    await action.onPressed();
    await tester.pump();
    expect(requests.where((r) => r.method != 'GET'), isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
  });

  testWidgets('delayed old status cannot replace a deliberate fresh reload', (
    tester,
  ) async {
    final old = Completer<http.Response>();
    var reads = 0;
    final state = f.account((r) {
      reads++;
      if (reads == 1) return old.future;
      return Future.value(
        f.reply({
          'kind': 'unit',
          'status': 'completed',
          'result': {'unit_id': 'fresh'},
        }),
      );
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
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    expect(reads, 1);
    final intent = state.beginAuthentication();
    state.cancelAuthentication(intent);
    await tester.pump();
    await tester.tap(find.text('Status neu laden'));
    await tester.pump();
    expect(reads, 1);
    old.complete(
      f.reply({
        'kind': 'unit',
        'status': 'failed',
        'error': 'Veralteter Fehler',
      }),
    );
    await tester.pumpAndSettle();
    expect(reads, 2);
    expect(find.text('Veralteter Fehler'), findsNothing);
    expect(find.text('Deine Runde ist bereit.'), findsOneWidget);
  });
}
