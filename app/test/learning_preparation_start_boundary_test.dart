import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as fixture;

http.Response failure(int status, String text) => http.Response(
  jsonEncode({'detail': text}),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

void main() {
  testWidgets(
    'a pending start cannot be submitted twice and conflict is clear',
    (t) async {
      final pending = Completer<http.Response>();
      var starts = 0;
      final state = fixture.account((r) async {
        if (r.method == 'GET') {
          return fixture.reply({
            'kind': 'unit',
            'status': 'completed',
            'result': {'unit_id': 'ready'},
          });
        }
        starts++;
        return pending.future;
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
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      await t.tap(find.text('Los geht’s'));
      await t.pump();
      expect(find.text('Bitte warten …'), findsOneWidget);
      expect(
        t
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Bitte warten …'),
            )
            .onPressed,
        isNull,
      );
      expect(starts, 1);
      pending.complete(failure(409, 'Dieser Lernauftrag beginnt später.'));
      await t.pumpAndSettle();
      expect(find.text('Dieser Lernauftrag beginnt später.'), findsOneWidget);
      expect(find.text('Los geht’s'), findsOneWidget);
      expect(starts, 1);
      expect(t.takeException(), isNull);
    },
  );
  for (final width in [320.0, 390.0]) {
    testWidgets('explicit start failure stays recoverable at $width', (
      t,
    ) async {
      t.view.physicalSize = Size(width, 844);
      t.view.devicePixelRatio = 1;
      final calls = <String>[];
      var starts = 0;
      final state = fixture.account((r) async {
        calls.add('${r.method} ${r.url.path}');
        if (r.method == 'GET') {
          return fixture.reply({
            'kind': 'unit',
            'status': 'completed',
            'result': {'unit_id': 'ready'},
          });
        }
        if (++starts == 1) return failure(503, 'interner Fehler');
        return fixture.reply({});
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
            path: '/unit/:id',
            builder: (_, r) =>
                Scaffold(body: Text('Runde ${r.pathParameters['id']}')),
          ),
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
        t.view.resetPhysicalSize();
        t.view.resetDevicePixelRatio();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      await t.tap(find.text('Los geht’s'));
      await t.pumpAndSettle();
      expect(
        find.text('Das Öffnen hat nicht geklappt. Versuche es noch einmal.'),
        findsOneWidget,
      );
      expect(find.text('interner Fehler'), findsNothing);
      expect(find.text('Los geht’s'), findsOneWidget);
      expect(calls, ['GET /api/jobs/job', 'POST /api/units/ready/start']);
      await t.tap(find.text('Los geht’s'));
      await t.pumpAndSettle();
      expect(find.text('Runde ready'), findsOneWidget);
      expect(calls, [
        'GET /api/jobs/job',
        'POST /api/units/ready/start',
        'POST /api/units/ready/start',
      ]);
      expect(t.takeException(), isNull);
    });
  }
  for (final status in [403, 404]) {
    testWidgets('start $status removes stale ready action', (t) async {
      final state = fixture.account(
        (r) async => r.method == 'GET'
            ? fixture.reply({
                'kind': 'unit',
                'status': 'completed',
                'result': {'unit_id': 'ready'},
              })
            : failure(status, 'Zugriff beendet'),
      );
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
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      await t.tap(find.text('Los geht’s'));
      await t.pumpAndSettle();
      expect(find.text('Los geht’s'), findsNothing);
      expect(find.text('Deine Runde ist bereit.'), findsNothing);
      expect(
        find.text('Diese Runde ist nicht mehr verfügbar.'),
        findsOneWidget,
      );
      expect(find.text('Vorbereitung nicht gefunden.'), findsNothing);
      expect(find.text('Gespeicherte Runden ansehen'), findsOneWidget);
      expect(t.takeException(), isNull);
    });
  }
  testWidgets('a late start failure does not leak into a covered route', (
    t,
  ) async {
    final delayed = Completer<http.Response>();
    final state = fixture.account(
      (r) async => r.method == 'GET'
          ? fixture.reply({
              'kind': 'unit',
              'status': 'completed',
              'result': {'unit_id': 'ready'},
            })
          : delayed.future,
    );
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
        ),
        GoRoute(
          path: '/other',
          builder: (_, _) => const Scaffold(body: Text('Andere Seite')),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    await t.tap(find.text('Los geht’s'));
    await t.pump();
    router.push('/other');
    await t.pumpAndSettle();
    delayed.complete(failure(409, 'Verdeckter privater Konflikt'));
    await t.pumpAndSettle();
    expect(find.text('Andere Seite'), findsOneWidget);
    expect(find.text('Verdeckter privater Konflikt'), findsNothing);
    router.pop();
    await t.pumpAndSettle();
    expect(find.text('Los geht’s'), findsOneWidget);
    expect(find.text('Verdeckter privater Konflikt'), findsNothing);
    expect(t.takeException(), isNull);
  });
  testWidgets('late failed start cannot reveal details to replaced session', (
    t,
  ) async {
    final delayed = Completer<http.Response>();
    final state = fixture.account(
      (r) async => r.method == 'GET'
          ? fixture.reply({
              'kind': 'unit',
              'status': 'completed',
              'result': {'unit_id': 'ready'},
            })
          : delayed.future,
    );
    state.api.token = 'old-session';
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
      await t.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    await t.tap(find.text('Los geht’s'));
    await t.pump();
    state.api.token = 'new-session';
    // ignore: invalid_use_of_protected_member, invalid_use_of_visible_for_testing_member
    state.notifyListeners();
    await t.pump();
    delayed.complete(failure(409, 'Privater alter Konflikt'));
    await t.pumpAndSettle();
    expect(find.text('Privater alter Konflikt'), findsNothing);
    expect(
      find.text('Das Öffnen hat nicht geklappt. Versuche es noch einmal.'),
      findsNothing,
    );
    expect(t.takeException(), isNull);
  });
}
