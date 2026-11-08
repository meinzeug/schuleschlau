// A separately installed, offline-only visual fixture for physical-device QA.
// It uses no user account or remote service and is not a release entrypoint.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/schulbuddy.dart';
import 'package:schulpilot/ui.dart';

void main() {
  const child = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
  final state = AppState(
    api: Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        return http.Response(
          jsonEncode({
            'context_key': 'today',
            'label': 'Künstlicher Test',
            'available': true,
            'notice': 'Künstlicher Test ohne echte Fragen oder Netzwerk.',
            'starters': ['Wie fange ich an?'],
            'history': [],
          }),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    ),
  )..user = {'id': 'synthetic-actor', 'role': 'child', 'child_id': child};
  final nav = GlobalKey<NavigatorState>();
  final router = GoRouter(
    navigatorKey: nav,
    initialLocation: '/app',
    routes: [
      GoRoute(
        path: '/app',
        builder: (context, _) => Scaffold(
          appBar: AppBar(title: const Text('Künstlicher Gerätetest')),
          body: Center(
            child: TextButton(
              onPressed: () => SchulbuddyScope.maybeOf(context)?.open(),
              child: const Text('Schulbuddy öffnen'),
            ),
          ),
        ),
      ),
    ],
  );
  runApp(
    MaterialApp.router(
      theme: appTheme(),
      routerConfig: router,
      builder: (context, body) => ListenableBuilder(
        listenable: router.routeInformationProvider,
        builder: (_, _) => SchulbuddyHost(
          state: state,
          navigatorKey: nav,
          location: router.routeInformationProvider.value.uri.toString(),
          child: body!,
        ),
      ),
    ),
  );
}
