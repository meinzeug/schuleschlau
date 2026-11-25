import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/processing_trace_panel.dart';
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

const jobId = '11111111111111111111111111111111';
http.Response reply(Object value, [int status = 200]) => http.Response(
  jsonEncode(value),
  status,
  headers: {'content-type': 'application/json'},
);

void main() {
  for (final entry in <String, String>{
    'feedback': 'Lernrückblick',
    'decision': 'Nächster Lernschritt',
    'visual': 'Grafik',
    'visual_review': 'Grafikprüfung',
    'exam_review': 'Klassenarbeit',
    'vocabulary': 'Wortschatzimport',
    'language': 'Sprachübung',
    'tutor': 'Lernhilfe',
    'parent_review': 'Elternüberblick',
    'unexpected': 'Verarbeitung',
  }.entries) {
    testWidgets('trace shows bounded phase label ${entry.key}', (tester) async {
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (_) async => reply({
              'job_id': jobId,
              'phase': entry.key,
              'status': 'failed',
              'sources': [],
              'units': [],
            }),
          ),
        ),
      )..user = {'id': 'parent', 'role': 'parent'};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ProcessingTracePanel(state: state, jobId: jobId),
          ),
        ),
      );
      await tester.tap(find.text('Verarbeitung ansehen'));
      await tester.pumpAndSettle();
      expect(find.text('Schritt: ${entry.value}'), findsOneWidget);
    });
  }

  testWidgets('parent preparation page exposes trace only after a tap', (
    tester,
  ) async {
    final calls = <String>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add('${request.method} ${request.url.path}');
          if (request.url.path.endsWith('/trace')) {
            return reply({
              'job_id': jobId,
              'phase': 'generation',
              'status': 'failed',
              'error_code': 'invalid_output',
              'failure_detail': 'question_fraction_ambiguous',
              'sources': [],
              'units': [],
            });
          }
          return reply({
            'id': jobId,
            'kind': 'unit',
            'status': 'failed',
            'error': 'Vorbereitung fehlgeschlagen.',
          });
        }),
      ),
    )..user = {'id': 'parent', 'role': 'parent', 'display_name': 'Eltern'};
    addTearDown(state.dispose);
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: jobId),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    expect(calls.where((path) => path.endsWith('/trace')), isEmpty);
    await tester.ensureVisible(find.text('Verarbeitung ansehen'));
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pumpAndSettle();
    expect(calls.where((path) => path.endsWith('/trace')), hasLength(1));
    expect(find.text('Fehlerklasse: invalid_output'), findsOneWidget);
    expect(
      find.text('Eine Bruchaufgabe war nicht eindeutig gestellt.'),
      findsOneWidget,
    );
    expect(calls.every((path) => path.startsWith('GET ')), isTrue);
  });

  testWidgets('parent opens a read-only trace deliberately', (tester) async {
    final calls = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request);
          return reply({
            'job_id': jobId,
            'phase': 'generation',
            'status': 'completed',
            'model': {'model': 'fixture/model', 'config_revision': 3},
            'sources': [
              {'id': 'synthetic', 'revision': 1, 'current_revision': 2},
            ],
            'units': [
              {
                'references': [
                  {'id': 'fixture', 'version': 1},
                ],
              },
            ],
          });
        }),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProcessingTracePanel(state: state, jobId: jobId),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(calls, isEmpty);
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pumpAndSettle();
    expect(calls.single.method, 'GET');
    expect(calls.single.url.path, '/api/jobs/$jobId/trace');
    expect(find.text('Schritt: Lernrunde'), findsOneWidget);
    expect(find.text('Modell: fixture/model'), findsOneWidget);
    expect(find.text('Konfigurationsstand: 3'), findsOneWidget);
    expect(find.text('Quellen: 1'), findsOneWidget);
    expect(find.text('Grafikvorlagen: 1'), findsOneWidget);
    expect(find.text('fixture · Version 1'), findsOneWidget);
    expect(find.text('Quellenfassung: 1 · aktuell 2'), findsOneWidget);
  });

  testWidgets('failed trace shows a safe retry and never retries by itself', (
    tester,
  ) async {
    var calls = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          calls++;
          return calls == 1
              ? reply({'detail': 'artificial-private-provider-body'}, 503)
              : reply({
                  'job_id': jobId,
                  'phase': 'recognition',
                  'status': 'completed',
                  'sources': [],
                  'units': [],
                });
        }),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProcessingTracePanel(state: state, jobId: jobId),
        ),
      ),
    );
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pumpAndSettle();
    expect(find.text('Details erneut laden'), findsOneWidget);
    expect(
      find.textContaining('artificial-private-provider-body'),
      findsNothing,
    );
    await tester.pump(const Duration(seconds: 10));
    expect(calls, 1);
    await tester.tap(find.text('Details erneut laden'));
    await tester.pumpAndSettle();
    expect(calls, 2);
    expect(find.text('Schritt: Erkennung'), findsOneWidget);
  });

  testWidgets('closing and reopening discards an older trace', (tester) async {
    final pending = Completer<http.Response>();
    var calls = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          calls++;
          if (calls == 1) return pending.future;
          return reply({
            'job_id': jobId,
            'phase': 'countercheck',
            'status': 'completed',
            'sources': [],
            'units': [],
          });
        }),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProcessingTracePanel(state: state, jobId: jobId),
        ),
      ),
    );
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pump();
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pumpAndSettle();
    pending.complete(
      reply({
        'job_id': jobId,
        'phase': 'generation',
        'status': 'completed',
        'sources': [],
        'units': [],
      }),
    );
    await tester.pumpAndSettle();
    expect(calls, 2);
    expect(find.text('Schritt: Gegenprüfung'), findsOneWidget);
    expect(find.text('Schritt: Lernrunde'), findsNothing);
  });

  testWidgets('old trace is discarded when a new login begins', (tester) async {
    final pending = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) => pending.future),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProcessingTracePanel(state: state, jobId: jobId),
        ),
      ),
    );
    await tester.tap(find.text('Verarbeitung ansehen'));
    await tester.pump();
    state.beginAuthentication();
    pending.complete(
      reply({
        'job_id': jobId,
        'phase': 'generation',
        'status': 'completed',
        'model': {'model': 'old-account-model', 'config_revision': 3},
      }),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('old-account-model'), findsNothing);
  });

  for (final width in [320.0, 390.0]) {
    testWidgets('parent trace stays usable with large text at $width pixels', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (_) async => reply({
              'job_id': jobId,
              'phase': 'generation',
              'status': 'failed',
              'error_code': 'invalid_output',
              'model': {
                'model': 'fixture/very-long-test-model-name-without-spaces-and-repeated-parts',
                'config_revision': 3,
              },
              'sources': [],
              'units': [],
            }),
          ),
        ),
      )..user = {'id': 'parent', 'role': 'parent'};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(
              size: Size(width, 800),
              textScaler: const TextScaler.linear(2),
            ),
            child: Scaffold(
              body: SingleChildScrollView(
                child: ProcessingTracePanel(state: state, jobId: jobId),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Verarbeitung ansehen'));
      await tester.pumpAndSettle();
      expect(find.text('Fehlerklasse: invalid_output'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('children never see the technical panel or trigger a read', (
    tester,
  ) async {
    var calls = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          calls++;
          return reply({});
        }),
      ),
    )..user = {'id': 'child', 'role': 'child'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ProcessingTracePanel(state: state, jobId: jobId),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Verarbeitung ansehen'), findsNothing);
    expect(calls, 0);
  });
}
