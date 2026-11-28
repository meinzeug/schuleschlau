import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/ui.dart';
import 'package:schulpilot/unit_screen.dart';

void main() {
  testWidgets('a possible evidence change does not block starting a round', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    var started = false;
    final requests = <http.Request>[];
    Map<String, dynamic> unit() => {
      'id': 'unit',
      'child_id': 'child',
      'subject': 'Mathematik',
      'topic': 'Künstliche Zahlen',
      'status': started ? 'active' : 'not_started',
      'synthetic': false,
      'provider': 'fixture',
      'model': 'fixture',
      'introduction_seen': true,
      'explanation': 'Künstliche Erklärung',
      'practice_evidence_may_have_changed': true,
      'questions': [
        {
          'id': 'q',
          'type': 'short',
          'prompt': 'Wie viel?',
          'attempts': [],
          'hints_used': 0,
          'input_kind': 'number',
        },
      ],
    };
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.url.path.endsWith('/start')) started = true;
          return http.Response(
            jsonEncode(unit()),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      ),
    )..user = {'id': 'own', 'role': 'child', 'child_id': 'child'};
    final router = GoRouter(
      initialLocation: '/unit/unit',
      routes: [
        GoRoute(
          path: '/unit/:id',
          builder: (_, _) => UnitScreen(state, unitId: 'unit'),
        ),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('prepared-round-evidence-notice')),
      findsOneWidget,
    );
    expect(requests.where((r) => r.method == 'POST'), isEmpty);
    final start = find.byKey(const ValueKey('learning-primary-action'));
    await tester.ensureVisible(start);
    await tester.tap(start);
    await tester.pumpAndSettle();
    expect(started, isTrue);
    expect(
      find.byKey(const ValueKey('prepared-round-evidence-notice')),
      findsNothing,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'a newly observed change is shown after starting without blocking',
    (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      var started = false;
      final requests = <http.Request>[];
      Map<String, dynamic> unit() => {
        'id': 'unit',
        'child_id': 'child',
        'subject': 'Mathematik',
        'topic': 'Künstliche Zahlen',
        'status': started ? 'active' : 'not_started',
        'synthetic': false,
        'provider': 'fixture',
        'model': 'fixture',
        'introduction_seen': true,
        'explanation': 'Künstliche Erklärung',
        'practice_evidence_may_have_changed': started,
        'questions': [
          {
            'id': 'q',
            'type': 'short',
            'prompt': 'Wie viel?',
            'attempts': [],
            'hints_used': 0,
            'input_kind': 'number',
          },
        ],
      };
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            if (request.url.path.endsWith('/start')) started = true;
            return http.Response(
              jsonEncode(unit()),
              200,
              headers: {'content-type': 'application/json'},
            );
          }),
        ),
      )..user = {'id': 'own', 'role': 'child', 'child_id': 'child'};
      final router = GoRouter(
        initialLocation: '/unit/unit',
        routes: [
          GoRoute(
            path: '/unit/:id',
            builder: (_, _) => UnitScreen(state, unitId: 'unit'),
          ),
        ],
      );
      addTearDown(router.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('prepared-round-evidence-notice')),
        findsNothing,
      );
      expect(requests.where((r) => r.method == 'POST'), isEmpty);
      final start = find.byKey(const ValueKey('learning-primary-action'));
      await tester.ensureVisible(start);
      await tester.tap(start);
      await tester.pumpAndSettle();
      expect(started, isTrue);
      expect(
        find.text(
          'Dein Lernstand könnte sich geändert haben. Du kannst trotzdem weiterlernen.',
        ),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('prepared-round-evidence-notice')),
        findsNothing,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
