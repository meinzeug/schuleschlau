// Synthetic inbox and device status only; no actual notification registration.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_panel.dart';
import 'package:schulpilot/push_transport.dart';
import 'package:schulpilot/ui.dart';

http.Response reply(Object value) => http.Response(
  jsonEncode(value),
  200,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final fixtures = <({AppState state, GoRouter router})>[];

  void scenario(String name, Future<void> Function(WidgetTester) body) {
    testWidgets(name, (tester) async {
      try {
        await body(tester);
      } finally {
        await tester.pumpWidget(const SizedBox.shrink());
        for (final fixture in fixtures) {
          fixture.state.inbox.dispose();
          fixture.router.dispose();
        }
        fixtures.clear();
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      }
    });
  }

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
          PushTransport.channel,
          (_) async => <String, dynamic>{},
        );
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(PushTransport.channel, null);
  });

  Future<({AppState state, GoRouter router})> open(
    WidgetTester tester,
    List<http.Request> calls,
    List<Json> Function() items, {
    double textScale = 1,
  }) async {
    tester.view.physicalSize = const Size(320, 600);
    tester.view.devicePixelRatio = 1;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request);
          if (request.url.path.endsWith('/inbox')) {
            final rows = items();
            return reply({
              'items': rows,
              'unread': rows.where((item) => item['read'] != true).length,
            });
          }
          if (request.url.path.endsWith('/devices')) return reply([]);
          if (request.url.path.endsWith('/config')) {
            return reply({
              'available': false,
              'notice': 'Bitte deine Eltern um Freigabe.',
            });
          }
          return reply({});
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'child'};
    final router = GoRouter(
      initialLocation: '/notifications',
      routes: [
        GoRoute(
          path: '/notifications',
          builder: (_, _) => NotificationsScreen(state),
        ),
        GoRoute(
          path: '/target/:id',
          builder: (_, route) =>
              Scaffold(body: Text('Ziel ${route.pathParameters['id']}')),
        ),
      ],
    );
    fixtures.add((state: state, router: router));
    await tester.pumpWidget(
      MaterialApp.router(
        theme: appTheme(),
        routerConfig: router,
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: TextScaler.linear(textScale)),
          child: child!,
        ),
      ),
    );
    await tester.pumpAndSettle();
    return (state: state, router: router);
  }

  for (final scale in [1.0, 2.0]) {
    scenario(
      'empty child inbox has a short message and keeps device access at $scale',
      (tester) async {
        final calls = <http.Request>[];
        await open(tester, calls, () => [], textScale: scale);
        expect(find.text('Noch keine Neuigkeiten.'), findsOneWidget);
        expect(find.text('Alle Neuigkeiten'), findsNothing);
        expect(find.textContaining('Ungelesen ('), findsNothing);
        expect(find.text('Suche & Neuigkeitenfilter'), findsNothing);
        expect(find.text('Gerät einstellen'), findsOneWidget);
        await tester.ensureVisible(
          find.text('Bitte deine Eltern um Freigabe.'),
        );
        expect(find.text('Bitte deine Eltern um Freigabe.'), findsOneWidget);
        expect(calls.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }

  scenario(
    'when messages exist the child can filter and open a saved notification',
    (tester) async {
      final calls = <http.Request>[];
      final item = {
        'id': 'one',
        'title': 'Deine Runde ist bereit',
        'read': true,
        'kind': 'reminder',
        'created': 1792638000,
        'route': '/target/one',
      };
      final opened = await open(tester, calls, () => [item]);
      expect(find.text('Alle Neuigkeiten'), findsOneWidget);
      expect(find.text('Ungelesen (0)'), findsOneWidget);
      await tester.tap(find.text('Ungelesen (0)'));
      await tester.pumpAndSettle();
      expect(find.text('Bisherige Neuigkeiten anzeigen'), findsOneWidget);
      await tester.ensureVisible(find.text('Bisherige Neuigkeiten anzeigen'));
      await tester.tap(find.text('Bisherige Neuigkeiten anzeigen'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Deine Runde ist bereit'));
      await tester.tap(find.text('Deine Runde ist bereit'));
      await tester.pumpAndSettle();
      expect(opened.router.state.uri.path, '/target/one');
      expect(calls.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  scenario(
    'a selected unread filter can still be cleared if the feed empties',
    (tester) async {
      final calls = <http.Request>[];
      var items = <Json>[
        {
          'id': 'one',
          'title': 'Bereit',
          'read': true,
          'kind': 'reminder',
          'created': 1792638000,
          'route': '/target/one',
        },
      ];
      final opened = await open(tester, calls, () => items);
      await tester.tap(find.text('Ungelesen (0)'));
      await tester.pumpAndSettle();
      items = [];
      await opened.state.inbox.refresh();
      await tester.pumpAndSettle();
      expect(find.text('Alle Neuigkeiten'), findsOneWidget);
      await tester.tap(find.text('Alle Neuigkeiten'));
      await tester.pumpAndSettle();
      expect(find.text('Noch keine Neuigkeiten.'), findsOneWidget);
      expect(find.text('Alle Neuigkeiten'), findsNothing);
      expect(calls.every((request) => request.method == 'GET'), isTrue);
    },
  );
}
