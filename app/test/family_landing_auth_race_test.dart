import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/dashboard.dart';
import 'package:schulpilot/exam_landing.dart';
import 'package:schulpilot/ui.dart';

http.Response familyResponse(String name) => http.Response(
  jsonEncode({
    'children': [
      {'id': 'test-child', 'display_name': name},
    ],
  }),
  200,
  headers: {'content-type': 'application/json'},
);

class ExamFixture {
  final pending = <Completer<http.Response>>[];
  final requests = <http.Request>[];
  late final AppState state;
  late final GoRouter router;

  ExamFixture({bool dashboard = false}) {
    state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) {
                requests.add(request);
                if (request.url.path == '/api/families/test-family') {
                  final reply = Completer<http.Response>();
                  pending.add(reply);
                  return reply.future;
                }
                return Future.value(http.Response('{}', 200));
              }),
            ),
          )
          ..user = {
            'id': 'test-parent',
            'role': 'parent',
            'families': [
              {'id': 'test-family', 'permission': 'owner'},
            ],
          }
          ..familyId = 'test-family';
    state.api.token = 'synthetic-session';
    router = GoRouter(
      initialLocation: '/choose',
      routes: [
        GoRoute(
          path: '/choose',
          builder: (_, _) =>
              dashboard ? DashboardScreen(state) : ExamLandingScreen(state),
        ),
        GoRoute(
          path: '/exams/:child',
          builder: (_, route) =>
              Scaffold(body: Text('Ziel ${route.pathParameters['child']}')),
        ),
        GoRoute(
          path: '/child/:child',
          builder: (_, route) =>
              Scaffold(body: Text('Kind ${route.pathParameters['child']}')),
        ),
      ],
    );
  }

  Future<void> mount(WidgetTester tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
  }
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final fails in [false, true]) {
    testWidgets(
      'late ${fails ? 'failure' : 'family response'} is discarded after login starts and explicit retry works',
      (tester) async {
        final f = ExamFixture();
        await f.mount(tester);
        expect(f.pending, hasLength(1));
        final intent = f.state.beginAuthentication();
        f.pending.first.complete(
          fails
              ? http.Response(
                  jsonEncode({'detail': 'Veraltetes privates Detail'}),
                  400,
                )
              : familyResponse('Alter privater Name'),
        );
        await tester.pumpAndSettle();
        expect(find.text('Alter privater Name'), findsNothing);
        expect(find.text('Veraltetes privates Detail'), findsNothing);
        expect(
          find.text('Bitte lade die Familienauswahl erneut.'),
          findsOneWidget,
        );
        f.state.cancelAuthentication(intent);
        await tester.tap(find.text('Erneut laden'));
        await tester.pump();
        expect(f.pending, hasLength(2));
        f.pending.last.complete(familyResponse('Neues Testkind'));
        await tester.pumpAndSettle();
        expect(find.text('Neues Testkind'), findsOneWidget);
        expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
      },
    );
    testWidgets(
      'dashboard discards a late ${fails ? 'failure' : 'response'} after login starts and allows a fresh read',
      (tester) async {
        final f = ExamFixture(dashboard: true);
        await f.mount(tester);
        final intent = f.state.beginAuthentication();
        f.pending.first.complete(
          fails
              ? http.Response(
                  jsonEncode({'detail': 'Veraltetes privates Detail'}),
                  400,
                )
              : familyResponse('Alter privater Name'),
        );
        await tester.pumpAndSettle();
        expect(find.text('Alter privater Name'), findsNothing);
        expect(find.text('Veraltetes privates Detail'), findsNothing);
        expect(
          find.text('Bitte lade die Familienübersicht erneut.'),
          findsOneWidget,
        );
        f.state.cancelAuthentication(intent);
        await tester.tap(find.text('Erneut laden'));
        await tester.pump();
        expect(f.pending, hasLength(2));
        f.pending.last.complete(familyResponse('Neues Testkind'));
        await tester.pumpAndSettle();
        expect(find.text('Neues Testkind'), findsOneWidget);
        expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
      },
    );
  }

  testWidgets(
    'an already shown child card cannot navigate after login intent changes',
    (tester) async {
      final f = ExamFixture();
      await f.mount(tester);
      f.pending.first.complete(familyResponse('Testkind'));
      await tester.pumpAndSettle();
      expect(find.text('Testkind'), findsOneWidget);
      f.state.beginAuthentication();
      await tester.tap(find.text('Testkind'));
      await tester.pumpAndSettle();
      expect(f.router.routeInformationProvider.value.uri.path, '/choose');
      expect(find.text('Ziel test-child'), findsNothing);
      expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    },
  );

  testWidgets('current child card opens the selected exams', (tester) async {
    final f = ExamFixture();
    await f.mount(tester);
    f.pending.first.complete(familyResponse('Testkind'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Testkind'));
    await tester.pumpAndSettle();
    expect(find.text('Ziel test-child'), findsOneWidget);
  });

  for (final dashboard in [false, true]) {
    for (final changed in ['account', 'family', 'token']) {
      testWidgets(
        '${dashboard ? 'dashboard' : 'exam chooser'} rejects a response after $changed changes',
        (tester) async {
          final f = ExamFixture(dashboard: dashboard);
          await f.mount(tester);
          switch (changed) {
            case 'account':
              f.state.user = {'id': 'other-parent', 'role': 'parent'};
            case 'family':
              f.state.familyId = 'other-family';
            case 'token':
              f.state.api.token = 'other-session';
          }
          f.pending.first.complete(familyResponse('Veraltetes Testkind'));
          await tester.pumpAndSettle();
          expect(find.text('Veraltetes Testkind'), findsNothing);
          expect(
            find.text(
              dashboard
                  ? 'Bitte lade die Familienübersicht erneut.'
                  : 'Bitte lade die Familienauswahl erneut.',
            ),
            findsOneWidget,
          );
        },
      );
    }
  }

  testWidgets('dashboard ignores stale child actions when a login starts', (
    tester,
  ) async {
    final f = ExamFixture(dashboard: true);
    await f.mount(tester);
    f.pending.first.complete(familyResponse('Testkind'));
    await tester.pumpAndSettle();
    expect(find.text('Testkind'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.tap(find.text('Lernüberblick öffnen'));
    await tester.pumpAndSettle();
    expect(f.router.routeInformationProvider.value.uri.path, '/choose');
    expect(find.text('Kind test-child'), findsNothing);
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
  });

  testWidgets('current dashboard child card opens its learning overview', (
    tester,
  ) async {
    final f = ExamFixture(dashboard: true);
    await f.mount(tester);
    f.pending.first.complete(familyResponse('Testkind'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Lernüberblick öffnen'));
    await tester.pumpAndSettle();
    expect(find.text('Kind test-child'), findsOneWidget);
  });

  testWidgets('stale dashboard cannot open the new child form', (tester) async {
    final f = ExamFixture(dashboard: true);
    await f.mount(tester);
    f.pending.first.complete(http.Response('{"children":[]}', 200));
    await tester.pumpAndSettle();
    expect(find.text('Ersten Kinderzugang einrichten'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.tap(find.text('Ersten Kinderzugang einrichten'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
  });

  testWidgets('an open family picker cannot switch family after login starts', (
    tester,
  ) async {
    final f = ExamFixture(dashboard: true);
    f.state.user!['families'] = [
      {'id': 'test-family', 'name': 'Erste Testfamilie', 'permission': 'owner'},
      {
        'id': 'other-family',
        'name': 'Zweite Testfamilie',
        'permission': 'owner',
      },
    ];
    await f.mount(tester);
    f.pending.first.complete(familyResponse('Testkind'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Erste Testfamilie').first);
    await tester.pumpAndSettle();
    f.state.beginAuthentication();
    await tester.tap(find.text('Zweite Testfamilie').last);
    await tester.pumpAndSettle();
    expect(f.state.familyId, 'test-family');
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
  });
}
