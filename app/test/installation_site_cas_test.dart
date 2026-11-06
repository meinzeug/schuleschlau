import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/installation_screen.dart';
import 'package:schulpilot/settings_screen.dart';
import 'package:schulpilot/ui.dart';

import 'admin_batch1_ux_test.dart' as fixture;
import 'admin_workspace_test.dart' as workspace;

class _SiteServer {
  int revision = 1;
  String name = 'Synthetic';
  final bodies = <Json>[];
  bool exposeRevision = true;
  int emergencyStops = 0;

  Json snapshot() {
    final value = fixture.installation();
    (value['site'] as Map)['operator_name'] = name;
    if (exposeRevision) {
      value['site_revision'] = revision;
    } else {
      value.remove('site_revision');
    }
    return value;
  }

  Future<http.Response> handle(http.Request request) async {
    if (request.url.path == '/api/admin/installation' &&
        request.method == 'GET') {
      return fixture.reply(snapshot());
    }
    if (request.url.path == '/api/admin/installation/site' &&
        request.method == 'PUT') {
      final body = Json.from(jsonDecode(request.body) as Map);
      bodies.add(body);
      if (body['expected_revision'] != revision) {
        return fixture.reply({
          'detail': 'Die Betriebseinstellungen wurden geändert. Bitte den Entwurf erneut prüfen.',
        }, 409);
      }
      name = body['operator_name'] as String? ?? name;
      revision++;
      return fixture.reply(snapshot());
    }
    if (request.url.path == '/api/admin/emergency-stop' &&
        request.method == 'POST') {
      emergencyStops++;
      return fixture.reply({'ok': true});
    }
    if (request.method == 'GET') {
      return fixture.reply(switch (request.url.path) {
        '/api/admin/provider' => workspace.provider(),
        '/api/admin/provider/check' => {'status': 'Synthetic'},
        '/api/admin/operations' => {
          'jobs': {'queued': 0, 'running': 0},
        },
        '/api/admin/families' => workspace.familyResponse(request, []),
        '/api/admin/audit' => <Json>[],
        _ => <String, dynamic>{},
      });
    }
    fail('Unexpected request: ${request.method} ${request.url.path}');
  }
}

void main() {
  testWidgets(
    'Site conflict preserves the draft until an explicit comparison',
    (tester) async {
      final server = _SiteServer();
      final state = fixture.operator(server.handle);
      final router = await fixture.mountInstallation(tester, state);
      await tester.enterText(fixture.field('Betreiber'), 'Synthetic draft');
      server.revision = 2;
      server.name = 'Synthetic other admin';
      await fixture.press(tester, find.text('Einstellungen speichern'));
      expect(server.bodies.single['expected_revision'], 1);
      expect(
        tester.widget<TextField>(fixture.field('Betreiber')).controller!.text,
        'Synthetic draft',
      );
      expect(server.name, 'Synthetic other admin');
      await fixture.press(tester, find.text('Aktuellen Stand prüfen'));
      expect(find.textContaining('Synthetic other admin'), findsOneWidget);
      expect(find.textContaining('Synthetic draft'), findsWidgets);
      await tester.tap(find.text('Abbrechen'));
      await tester.pumpAndSettle();
      expect(server.bodies, hasLength(1));
      await fixture.press(tester, find.text('Aktuellen Stand prüfen'));
      await tester.tap(find.text('Stand für Entwurf übernehmen'));
      await tester.pumpAndSettle();
      expect(server.bodies, hasLength(1));
      await fixture.press(tester, find.text('Einstellungen speichern'));
      expect(server.bodies.last['expected_revision'], 2);
      expect(server.name, 'Synthetic draft');
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.inbox.dispose();
      state.dispose();
    },
  );

  testWidgets('Old server without site revision cannot silently save', (
    tester,
  ) async {
    final server = _SiteServer()..exposeRevision = false;
    final state = fixture.operator(server.handle);
    final router = await fixture.mountInstallation(tester, state);
    await tester.enterText(fixture.field('Betreiber'), 'Synthetic draft');
    await fixture.press(tester, find.text('Einstellungen speichern'));
    expect(server.bodies, isEmpty);
    expect(find.textContaining('nicht versionsgesichert'), findsOneWidget);
    expect(
      tester.widget<TextField>(fixture.field('Betreiber')).controller!.text,
      'Synthetic draft',
    );
    await tester.pumpWidget(const SizedBox());
    router.dispose();
    state.inbox.dispose();
    state.dispose();
  });

  testWidgets('Emergency stop remains reachable after a site conflict', (
    tester,
  ) async {
    final server = _SiteServer();
    final state = fixture.operator(server.handle);
    final router = GoRouter(
      initialLocation: '/admin/settings',
      routes: [
        GoRoute(
          path: '/admin/settings',
          builder: (_, _) => InstallationScreen(state, initial: false),
        ),
        GoRoute(path: '/admin', builder: (_, _) => AdminScreen(state)),
      ],
    );
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    await tester.enterText(fixture.field('Betreiber'), 'Synthetic draft');
    server.revision = 2;
    await fixture.press(tester, find.text('Einstellungen speichern'));
    expect(server.bodies.single['expected_revision'], 1);
    expect(find.text('Aktuellen Stand prüfen'), findsOneWidget);
    router.go('/admin');
    await tester.pumpAndSettle();
    await fixture.press(tester, find.text('KI-Aufrufe sofort stoppen'));
    expect(server.emergencyStops, 1);
    expect(
      find.text('Notfallstopp gespeichert. Neue KI-Aufrufe sind gesperrt.'),
      findsOneWidget,
    );
    await tester.pumpWidget(const SizedBox());
    router.dispose();
    state.inbox.dispose();
    state.dispose();
  });
}
