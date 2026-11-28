import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/math_content.dart';
import 'package:schulpilot/ui.dart';
import 'package:schulpilot/unit_screen.dart';

import 'unit_learning_time_test.dart' as fixture;

void main() {
  testWidgets(
    'legacy parent labels a preserved uncertain answer independent with null date',
    (tester) async {
      final data = fixture.unit(status: 'active');
      data['questions'][0]['hints'] = <String>[];
      data['questions'][0]['explanation'] = 'Künstliche Erklärung';
      data['questions'][0]['attempts'] = [
        {
          'id': 'synthetic',
          'answer': 'Katze',
          'outcome': 'correct',
          'assisted': false,
          'created': null,
          'evaluation': {'independence_uncertain': true},
          'assessment_history': [],
        },
      ];
      final requests = <http.Request>[];
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            requests.add(r);
            return http.Response(
              jsonEncode(data),
              200,
              headers: {'content-type': 'application/json; charset=utf-8'},
            );
          }),
        ),
      )..user = {'id': 'synthetic-parent', 'role': 'parent'};
      final router = GoRouter(
        initialLocation: '/unit/unit',
        routes: [
          GoRoute(
            path: '/unit/:id',
            builder: (_, _) => UnitScreen(state, unitId: 'unit'),
          ),
        ],
      );
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      expect(requests, isNotEmpty);
      expect(
        requests.first.headers['X-Schulpilot-Capabilities'],
        isNot(contains('attempt-time-unknown-v1')),
      );
      expect(
        find.byWidgetPredicate(
          (w) =>
              w is MathText &&
              (w.data?.contains('Antwort: Katze') ?? false) &&
              (w.data?.contains('selbstständig') ?? false),
        ),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      router.dispose();
    },
  );
  for (final role in ['child', 'parent']) {
    testWidgets('legacy $role displays a deliberate 409 round error', (
      tester,
    ) async {
      final requests = <http.Request>[];
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((r) async {
                  requests.add(r);
                  return http.Response(
                    jsonEncode({
                      'detail': 'Diese Runde ist gerade nicht verfügbar. Du kannst eine andere öffnen.',
                    }),
                    409,
                    headers: {
                      'content-type': 'application/json; charset=utf-8',
                    },
                  );
                }),
              ),
            )
            ..user = {
              'id': 'synthetic-user',
              'role': role,
              if (role == 'child') 'child_id': 'child',
            };
      final router = GoRouter(
        initialLocation: '/unit/unit',
        routes: [
          GoRoute(
            path: '/unit/:id',
            builder: (_, _) => UnitScreen(state, unitId: 'unit'),
          ),
        ],
      );
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Diese Runde ist gerade nicht verfügbar.'),
        findsOneWidget,
      );
      expect(find.text('Erneut versuchen'), findsOneWidget);
      expect(requests.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      router.dispose();
    });
  }
}
