import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as f;

void main() {
  for (final status in ['queued', 'running', 'failed', 'completed']) {
    testWidgets('initial status is neutral until $status is confirmed', (
      tester,
    ) async {
      final pending = Completer<http.Response>();
      final calls = <String>[];
      final state = f.account((request) async {
        calls.add('${request.method} ${request.url.path}');
        return pending.future;
      });
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
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
        await tester.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pump();
      expect(find.text('Status wird geladen …'), findsOneWidget);
      expect(find.text('Deine Runde entsteht …'), findsNothing);
      expect(
        find.text('Die Vorbereitung geht auch ohne offene App weiter.'),
        findsNothing,
      );
      expect(
        find.byWidgetPredicate(
          (widget) =>
              widget is Semantics &&
              widget.properties.label == 'Status wird geladen',
        ),
        findsOneWidget,
      );
      await tester.pump(const Duration(seconds: 3));
      expect(calls, ['GET /api/jobs/job']);
      pending.complete(
        f.reply({
          'kind': 'unit',
          'status': status,
          if (status == 'completed') 'result': {'unit_id': 'ready'},
        }),
      );
      await tester.pump();
      await tester.pump();
      expect(find.text('Status wird geladen …'), findsNothing);
      expect(
        find.text(switch (status) {
          'queued' => 'Deine Runde wartet.',
          'running' => 'Deine Runde entsteht …',
          'completed' => 'Deine Runde ist bereit.',
          _ => 'Diese Runde konnte nicht vorbereitet werden.',
        }),
        findsOneWidget,
      );
      expect(calls, ['GET /api/jobs/job']);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('recovery lookup stays neutral until its own status arrives', (
    tester,
  ) async {
    const recovery = '12345678901234567890123456789012';
    final pending = Completer<http.Response>();
    final calls = <String>[];
    final state = f.account((request) async {
      calls.add('${request.method} ${request.url.path}');
      if (request.url.path.endsWith('/old')) {
        return f.reply({
          'kind': 'unit',
          'status': 'failed',
          'recovery_job_id': recovery,
        });
      }
      return pending.future;
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: 'old'),
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
    await tester.pump();
    expect(calls, ['GET /api/jobs/old', 'GET /api/jobs/$recovery']);
    expect(find.text('Status wird geladen …'), findsOneWidget);
    expect(find.text('Deine Runde entsteht …'), findsNothing);
    pending.complete(f.reply({'kind': 'unit', 'status': 'running'}));
    await tester.pump();
    await tester.pump();
    expect(find.text('Deine Runde entsteht …'), findsOneWidget);
    expect(calls, ['GET /api/jobs/old', 'GET /api/jobs/$recovery']);
  });

  testWidgets('not-found is shown only when the first read returns', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final calls = <String>[];
    final state = f.account((request) async {
      calls.add('${request.method} ${request.url.path}');
      return pending.future;
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => LearningPreparationScreen(
            state,
            childId: 'child',
            jobId: 'missing',
          ),
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
    expect(find.text('Status wird geladen …'), findsOneWidget);
    expect(find.text('Vorbereitung nicht gefunden.'), findsNothing);
    pending.complete(
      http.Response(
        '{"detail":"nicht gefunden"}',
        404,
        headers: {'content-type': 'application/json; charset=utf-8'},
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.text('Vorbereitung nicht gefunden.'), findsOneWidget);
    expect(find.text('Status wird geladen …'), findsNothing);
    expect(calls, ['GET /api/jobs/missing']);
  });
}
