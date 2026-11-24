import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/child_account.dart';
import 'package:schulpilot/ui.dart';

http.Response reply(Object value, [int status = 200]) =>
    http.Response(jsonEncode(value), status);
final devices = [
  {'id': 'here', 'device': 'Eigenes Testhandy', 'current': true},
  {'id': 'one', 'device': 'Testtablet', 'current': false},
  {'id': 'two', 'device': 'Testlaptop', 'current': false},
];

class DeviceFixture {
  final requests = <http.Request>[];
  final firstList = Completer<http.Response>();
  final pendingDelete = Completer<http.Response>();
  bool delayFirst = false, delayDelete = false;
  var lists = 0;
  late final AppState state;
  late final GoRouter router;

  DeviceFixture({this.delayFirst = false, this.delayDelete = false}) {
    state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                requests.add(r);
                if (r.url.path == '/api/auth/sessions' && r.method == 'GET') {
                  lists++;
                  if (delayFirst && lists == 1) return firstList.future;
                  return reply(devices);
                }
                if (r.method == 'DELETE' &&
                    r.url.path.startsWith('/api/auth/sessions/')) {
                  if (delayDelete) return pendingDelete.future;
                  return reply({});
                }
                return reply({});
              }),
            ),
          )
          ..user = {
            'id': 'test-child-user',
            'role': 'child',
            'child_id': 'test-child',
          };
    state.api.token = 'synthetic-session';
    router = GoRouter(
      initialLocation: '/account',
      routes: [
        GoRoute(path: '/account', builder: (_, _) => ChildAccount(state)),
        GoRoute(
          path: '/login',
          builder: (_, _) => const Scaffold(body: Text('Login')),
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
    if (!delayFirst) await tester.pumpAndSettle();
  }

  List<http.Request> get deletions =>
      requests.where((r) => r.method == 'DELETE').toList();
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder.first);
  await tester.pumpAndSettle();
  await tester.tap(finder.first);
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final error in [false, true]) {
    testWidgets(
      'old device ${error ? 'error' : 'list'} is discarded and can be explicitly reloaded',
      (tester) async {
        final f = DeviceFixture(delayFirst: true);
        await f.mount(tester);
        final intent = f.state.beginAuthentication();
        f.firstList.complete(
          error
              ? reply({'detail': 'Altes privates Detail'}, 400)
              : reply(devices),
        );
        await tester.pumpAndSettle();
        expect(find.text('Testtablet'), findsNothing);
        expect(find.text('Altes privates Detail'), findsNothing);
        expect(find.text('Bitte lade die Geräte erneut.'), findsOneWidget);
        f.state.cancelAuthentication(intent);
        await tapVisible(tester, find.text('Erneut laden'));
        expect(find.text('Testtablet'), findsOneWidget);
        expect(f.deletions, isEmpty);
      },
    );
  }
  testWidgets('old device list is discarded after a token change', (
    tester,
  ) async {
    final f = DeviceFixture(delayFirst: true);
    await f.mount(tester);
    f.state.api.token = 'different-session';
    f.firstList.complete(reply(devices));
    await tester.pumpAndSettle();
    expect(find.text('Testtablet'), findsNothing);
    expect(find.text('Bitte lade die Geräte erneut.'), findsOneWidget);
    expect(f.deletions, isEmpty);
  });
  testWidgets('stale device card cannot open a logout confirmation', (
    tester,
  ) async {
    final f = DeviceFixture();
    await f.mount(tester);
    f.state.beginAuthentication();
    await tapVisible(tester, find.text('Gerät abmelden'));
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.deletions, isEmpty);
  });
  testWidgets('logout confirmation cannot send after new login begins', (
    tester,
  ) async {
    final f = DeviceFixture();
    await f.mount(tester);
    await tapVisible(tester, find.text('Gerät abmelden'));
    expect(find.text('Dieses Gerät abmelden?'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.deletions, isEmpty);
  });
  testWidgets(
    'bulk confirmation closes without deleting after a new login begins',
    (tester) async {
      final f = DeviceFixture();
      await f.mount(tester);
      await tapVisible(tester, find.text('Andere Geräte gemeinsam abmelden'));
      expect(find.text('Andere Geräte abmelden?'), findsOneWidget);
      f.state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      expect(f.deletions, isEmpty);
    },
  );
  testWidgets('stale device details cannot be opened after a token change', (
    tester,
  ) async {
    final f = DeviceFixture();
    await f.mount(tester);
    f.state.api.token = 'different-session';
    await tapVisible(tester, find.text('Testtablet'));
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.deletions, isEmpty);
  });
  testWidgets('open device details close without interaction on new login', (
    tester,
  ) async {
    final f = DeviceFixture();
    await f.mount(tester);
    await tapVisible(tester, find.text('Testtablet'));
    expect(find.textContaining('Angemeldet seit:'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(f.deletions, isEmpty);
  });
  testWidgets('current-device logout does not clear a newer login intent', (
    tester,
  ) async {
    final f = DeviceFixture(delayDelete: true);
    await f.mount(tester);
    final owner = f.state.user;
    await tester.ensureVisible(find.text('Hier abmelden'));
    await tester.tap(find.text('Hier abmelden'));
    await tester.pump();
    expect(f.deletions, hasLength(1));
    f.state.beginAuthentication();
    f.pendingDelete.complete(reply({}));
    await tester.pumpAndSettle();
    expect(identical(f.state.user, owner), isTrue);
    expect(f.state.api.token, 'synthetic-session');
    expect(find.text('Login'), findsNothing);
  });
  testWidgets('bulk logout stops before another request after login starts', (
    tester,
  ) async {
    final f = DeviceFixture(delayDelete: true);
    await f.mount(tester);
    await tapVisible(tester, find.text('Andere Geräte gemeinsam abmelden'));
    await tester.tap(
      find.descendant(
        of: find.byType(AlertDialog),
        matching: find.text('Andere Geräte abmelden'),
      ),
    );
    await tester.pump();
    expect(f.deletions, hasLength(1));
    f.state.beginAuthentication();
    f.pendingDelete.complete(reply({}));
    await tester.pumpAndSettle();
    expect(f.deletions, hasLength(1));
    expect(find.textContaining('Geräte sind abgemeldet'), findsNothing);
  });
}
