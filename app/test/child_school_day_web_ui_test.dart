// Synthetic complete-page checks, runnable in the Flutter VM and Chrome.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/ui.dart';

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final size in [const Size(320, 600), const Size(390, 844)]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets('Child school day is clear and usable at $size/$scale', (
        tester,
      ) async {
        tester.view.physicalSize = size;
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final requests = <http.Request>[];
        final state =
            AppState(
                api: Api(
                  base: 'https://example.invalid/api',
                  client: MockClient((request) async {
                    requests.add(request);
                    final Object response;
                    if (request.url.path.endsWith('/study-path')) {
                      response = {
                        'available': true,
                        'blocks': [
                          {
                            'id': 'done',
                            'title': 'Brüche vergleichen',
                            'phase': 'understand',
                            'label': 'Erste Runde',
                            'status': 'completed',
                            'question_count': 2,
                            'unit_id': 'old',
                          },
                          {
                            'id': 'next',
                            'title': 'Brüche erweitern',
                            'phase': 'understand',
                            'label': 'Erste Runde',
                            'status': 'ready',
                            'question_count': 2,
                            'unit_id': 'next-unit',
                          },
                        ],
                        'total_questions': 4,
                        'completed_questions': 2,
                        'ready_questions': 2,
                        'next_block_id': 'next',
                        'can_continue': true,
                      };
                    } else if (request.url.path.endsWith('/school-days/day')) {
                      response = {
                        'id': 'day',
                        'child_id': 'child',
                        'date': '2026-11-26',
                        'stage': 'ready',
                        'revision': 1,
                        'allow_uploads': true,
                        'pages': [
                          {
                            'id': 'page',
                            'child_id': 'child',
                            'page_number': 1,
                            'subject': 'Mathematik',
                            'topic': 'Brüche',
                            'confirmed': true,
                            'status': 'confirmed',
                            'synthetic': true,
                          },
                        ],
                        'confirmed_count': 1,
                        'synthetic': false,
                        'units': <Object>[],
                        'plan': {
                          'groups': <Object>[],
                          'notices': <Object>[],
                          'estimated_minutes': 8,
                        },
                        'preparation': {'status': 'completed'},
                      };
                    } else {
                      return http.Response('Unexpected synthetic route', 404);
                    }
                    return http.Response(
                      jsonEncode(response),
                      200,
                      headers: {'content-type': 'application/json'},
                    );
                  }),
                ),
              )
              ..user = {
                'id': 'fake-user',
                'role': 'child',
                'child_id': 'child',
                'synthetic': true,
              };
        final router = GoRouter(
          routes: [
            GoRoute(
              path: '/',
              builder: (_, _) =>
                  SchoolDayScreen(state, childId: 'child', dayId: 'day'),
            ),
            GoRoute(
              path: '/unit/:id',
              builder: (_, route) => Scaffold(
                body: Text('Beispielrunde ${route.pathParameters['id']}'),
              ),
            ),
          ],
        );
        addTearDown(() async {
          await tester.pumpWidget(const SizedBox());
          router.dispose();
          state.inbox.dispose();
          state.familyCalls.dispose();
          state.dispose();
        });
        await tester.pumpWidget(
          MaterialApp.router(
            theme: appTheme(brightness: Brightness.dark),
            routerConfig: router,
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(context)
                  .copyWith(textScaler: TextScaler.linear(scale)),
              child: child!,
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text('Brüche erweitern'), findsOneWidget);
        expect(find.text('3 Fertig'), findsNothing);
        expect(find.text('Fragen zu meinen Heftseiten'), findsNothing);
        expect(find.text('Heftseiten und bisherige Runden'), findsNothing);
        await tester.ensureVisible(find.text('Meine Heftseiten'));
        await tester.tap(find.text('Meine Heftseiten'));
        await tester.pumpAndSettle();
        expect(find.text('Fragen zu meinen Heftseiten'), findsOneWidget);
        expect(find.text('Heftseiten und bisherige Runden'), findsOneWidget);
        await tester.tap(find.text('Meine Heftseiten'));
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.text('Weiterlernen'));
        await tester.tap(find.text('Weiterlernen'));
        await tester.pumpAndSettle();
        expect(find.text('Beispielrunde next-unit'), findsOneWidget);
        expect(requests, isNotEmpty);
        expect(requests.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      });
    }
  }
}
