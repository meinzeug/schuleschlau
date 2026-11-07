import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/auth_screens.dart';
import 'package:schulpilot/ui.dart';

http.Response reply(Object data) => http.Response(
  jsonEncode(data),
  200,
  headers: {'content-type': 'application/json; charset=utf-8'},
);
Finder field(String label) => find.byWidgetPredicate(
  (widget) => widget is TextField && widget.decoration?.labelText == label,
);

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets(
    'successful login keeps its pending home read current after login route closes',
    (t) async {
      final pending = Completer<http.Response>();
      var probes = 0;
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (r.url.path == '/api/auth/login') {
              return reply({
                'user': {
                  'id': 'synthetic-child',
                  'role': 'child',
                  'child_id': 'c',
                },
              });
            }
            if (r.url.path == '/api/children/c/overview') {
              probes++;
              return pending.future;
            }
            return reply({'available': false});
          }),
        ),
      );
      Future<Object>? overview;
      (Object?, String?, int?)? readIdentity;
      state.addListener(() {
        if (state.user != null && overview == null) {
          readIdentity = state.api.requestIdentity();
          overview = state.api
              .get('/children/c/overview')
              .then<Object>((v) => v, onError: (Object e) => e);
        }
      });
      final router = GoRouter(
        initialLocation: '/login',
        routes: [
          GoRoute(
            path: '/login',
            builder: (_, s) => AuthScreen(state, mode: 'login', linkUri: s.uri),
          ),
          GoRoute(
            path: '/app',
            builder: (_, _) => const Scaffold(body: Text('Startseite')),
          ),
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      await t.enterText(field('E-Mail oder Benutzername'), 'test-child');
      await t.enterText(field('Passwort'), 'secure-child-pass-123');
      await t.tap(find.widgetWithText(FilledButton, 'Anmelden'));
      await t.pumpAndSettle();
      expect(find.text('Startseite'), findsOneWidget);
      expect(probes, 1);
      // Auth intent belongs to the accepted account, not the disposed form.
      expect(state.api.ownsRequest(readIdentity!), isTrue);
      pending.complete(reply({'ok': true}));
      await t.pumpAndSettle();
      expect(await overview, {'ok': true});
      expect(t.takeException(), isNull);
    },
  );
  testWidgets('leaving a pending login invalidates its eventual response', (
    t,
  ) async {
    final pending = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.url.path == '/api/auth/login') return pending.future;
          return reply({'available': false});
        }),
      ),
    );
    final router = GoRouter(
      initialLocation: '/login',
      routes: [
        GoRoute(
          path: '/login',
          builder: (_, s) => AuthScreen(state, mode: 'login', linkUri: s.uri),
        ),
        GoRoute(
          path: '/away',
          builder: (_, _) => const Scaffold(body: Text('Anderswo')),
        ),
        GoRoute(
          path: '/app',
          builder: (_, _) => const Scaffold(body: Text('Startseite')),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    await t.enterText(field('E-Mail oder Benutzername'), 'test-child');
    await t.enterText(field('Passwort'), 'secure-child-pass-123');
    await t.tap(find.widgetWithText(FilledButton, 'Anmelden'));
    await t.pump();
    final identity = state.api.requestIdentity();
    router.go('/away');
    await t.pumpAndSettle();
    expect(state.api.ownsRequest(identity), isFalse);
    pending.complete(
      reply({
        'user': {'id': 'synthetic-child', 'role': 'child', 'child_id': 'c'},
      }),
    );
    await t.pumpAndSettle();
    expect(find.text('Anderswo'), findsOneWidget);
    expect(state.user, isNull);
    expect(t.takeException(), isNull);
  });
  testWidgets(
    'a newer authentication intent prevents the old login navigation',
    (t) async {
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (r.url.path == '/api/auth/login') {
              return reply({
                'user': {
                  'id': 'synthetic-child',
                  'role': 'child',
                  'child_id': 'c',
                },
              });
            }
            return reply({'available': false});
          }),
        ),
      );
      int? newer;
      state.addListener(() {
        if (state.user != null && newer == null) {
          newer = state.beginAuthentication();
        }
      });
      final router = GoRouter(
        initialLocation: '/login',
        routes: [
          GoRoute(
            path: '/login',
            builder: (_, s) => AuthScreen(state, mode: 'login', linkUri: s.uri),
          ),
          GoRoute(
            path: '/app',
            builder: (_, _) => const Scaffold(body: Text('Startseite')),
          ),
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      await t.enterText(field('E-Mail oder Benutzername'), 'test-child');
      await t.enterText(field('Passwort'), 'secure-child-pass-123');
      await t.tap(find.widgetWithText(FilledButton, 'Anmelden'));
      await t.pumpAndSettle();
      expect(newer, isNotNull);
      expect(state.api.requestIdentity().$3, newer);
      expect(router.state.uri.path, '/login');
      expect(find.text('Startseite'), findsNothing);
      expect(t.takeException(), isNull);
    },
  );
}
