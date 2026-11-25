import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/local_processing_failures_panel.dart';

const childId = '11111111111111111111111111111111';
const unitId = '22222222222222222222222222222222';

http.Response reply(Object value) => http.Response(
  jsonEncode(value),
  200,
  headers: {'content-type': 'application/json'},
);

void main() {
  testWidgets('parent deliberately loads bounded technical errors using GET', (
    tester,
  ) async {
    final calls = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request);
          return reply({
            'errors': [
              {'code': 'photo_invalid', 'created': 1700000000, 'unit_id': null},
              {
                'code': 'question_missing',
                'created': 1700000000,
                'unit_id': unitId,
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
          body: LocalProcessingFailuresPanel(state: state, childId: childId),
        ),
      ),
    );
    expect(calls, isEmpty);
    await tester.tap(find.text('Verarbeitungsfehler'));
    await tester.pumpAndSettle();
    expect(calls, hasLength(1));
    expect(calls.single.method, 'GET');
    expect(calls.single.url.path, '/api/children/$childId/processing-errors');
    expect(find.text('Foto konnte nicht gelesen werden'), findsOneWidget);
    expect(find.text('Aufgabe war nicht mehr verfügbar'), findsOneWidget);
    expect(find.byTooltip('Runde öffnen'), findsOneWidget);
  });

  testWidgets('child cannot see or load parent diagnostics', (tester) async {
    var calls = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          calls++;
          return reply({'errors': []});
        }),
      ),
    )..user = {'id': 'child', 'role': 'child'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LocalProcessingFailuresPanel(state: state, childId: childId),
        ),
      ),
    );
    expect(find.text('Verarbeitungsfehler'), findsNothing);
    expect(calls, 0);
  });

  testWidgets('late response is discarded after panel closes', (tester) async {
    final result = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) => result.future),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LocalProcessingFailuresPanel(state: state, childId: childId),
        ),
      ),
    );
    await tester.tap(find.text('Verarbeitungsfehler'));
    await tester.pump();
    await tester.tap(find.text('Verarbeitungsfehler'));
    result.complete(
      reply({
        'errors': [
          {'code': 'photo_invalid'},
        ],
      }),
    );
    await tester.pumpAndSettle();
    expect(find.text('Foto konnte nicht gelesen werden'), findsNothing);
  });

  testWidgets('late response is discarded on account switch', (tester) async {
    final result = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) => result.future),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: LocalProcessingFailuresPanel(state: state, childId: childId),
        ),
      ),
    );
    await tester.tap(find.text('Verarbeitungsfehler'));
    await tester.pump();
    state.beginAuthentication();
    result.complete(
      reply({
        'errors': [
          {'code': 'photo_invalid'},
        ],
      }),
    );
    await tester.pumpAndSettle();
    expect(find.text('Foto konnte nicht gelesen werden'), findsNothing);
  });

  for (final width in [320.0, 390.0]) {
    testWidgets('diagnostics remain readable at $width with large text', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 760);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (_) async => reply({
              'errors': [
                {
                  'code': 'photo_unavailable',
                  'created': 1700000000,
                  'unit_id': null,
                },
              ],
            }),
          ),
        ),
      )..user = {'id': 'parent', 'role': 'parent'};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(
              size: Size(width, 760),
              textScaler: const TextScaler.linear(1.4),
            ),
            child: Scaffold(
              body: SingleChildScrollView(
                child: LocalProcessingFailuresPanel(
                  state: state,
                  childId: childId,
                ),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Verarbeitungsfehler'));
      await tester.pumpAndSettle();
      expect(find.text('Fotodienst war nicht erreichbar'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}
