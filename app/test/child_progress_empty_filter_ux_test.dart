import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/progress_screen.dart';
import 'package:schulpilot/ui.dart';

import 'progress_cards_ux88_test.dart' as fixture;

Future<(AppState, GoRouter)> open(
  WidgetTester tester,
  List<http.Request> requests, {
  double width = 320,
  double scale = 1,
}) async {
  tester.view.physicalSize = Size(width, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  final state = AppState(
    api: Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        requests.add(request);
        final period = request.url.queryParameters['period'];
        final data = fixture.data(request, items: period == '7' ? [] : null);
        data['view_filters'] = {
          'period': period ?? 'all',
          'sort': 'default',
          'search': '',
          'status': 'all',
          'round_kind': 'all',
        };
        return fixture.reply(data);
      }),
    ),
  )..user = {'id': 'kid-account', 'role': 'child', 'child_id': 'kid'};
  final router = GoRouter(
    initialLocation:
        '/progress/kid?fach=Mathematik&ergebnis=assisted&zeitraum=7',
    routes: [
      GoRoute(
        path: '/progress/:child',
        builder: (_, route) => ProgressScreen(
          state,
          childId: 'kid',
          initialSubject: route.uri.queryParameters['fach'],
          initialCategory: route.uri.queryParameters['ergebnis'],
          initialPeriod: route.uri.queryParameters['zeitraum'],
        ),
      ),
    ],
  );
  addTearDown(() async {
    await tester.pumpWidget(const SizedBox.shrink());
    router.dispose();
    state.dispose();
  });
  await tester.pumpWidget(
    MaterialApp.router(
      theme: appTheme(),
      routerConfig: router,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context)
            .copyWith(textScaler: TextScaler.linear(scale)),
        child: child!,
      ),
    ),
  );
  await tester.pumpAndSettle();
  return (state, router);
}

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'No filtered results offers an honest reset at $width px / $scale×',
      (tester) async {
        final requests = <http.Request>[];
        await open(tester, requests, width: width, scale: scale);
        expect(
          find.text('Für diese Ansicht gibt es gerade keine Ergebnisse.'),
          findsOneWidget,
        );
        final reset = find.text('Ansichtsfilter zurücksetzen');
        await tester.ensureVisible(reset);
        await tester.tap(reset);
        await tester.pumpAndSettle();
        expect(requests.every((r) => r.method == 'GET'), isTrue);
        final query = requests.last.url.queryParameters;
        expect(query['period'], isNull);
        expect(query['category'], 'assisted');
        expect(query['subject'], 'Mathematik');
        expect(find.text('Brüche'), findsOneWidget);
        expect(tester.takeException(), isNull);
      },
    );
  }
  for (final login in [true, false]) {
    testWidgets(
      'A stale reset cannot cross ${login ? 'a new sign-in' : 'account change'}',
      (tester) async {
        final requests = <http.Request>[];
        final (state, _) = await open(tester, requests);
        final action = tester
            .widget<TextButton>(
              find.widgetWithText(TextButton, 'Ansichtsfilter zurücksetzen'),
            )
            .onPressed!;
        final count = requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          action();
          state.cancelAuthentication(intent);
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        action();
        await tester.pumpAndSettle();
        expect(requests, hasLength(count));
        expect(tester.takeException(), isNull);
      },
    );
  }
}
