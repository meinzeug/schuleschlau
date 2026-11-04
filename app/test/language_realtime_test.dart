import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/language_workshop.dart';

http.Response reply(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Map<String, Object?> project(String status) => {
  'id': 'project',
  'mode': 'exam',
  'target_locale': 'en-GB',
  'status': status,
  'goal': 'Künstliches Sprachziel',
  'draft': '',
  'job_id': 'artificial-job',
  'unit_id': status == 'ready' ? 'unit' : null,
  'can_retry': false,
  'error': null,
  'result': null,
};

class Harness {
  final List<http.Request> requests = [];
  late final AppState state;
  late final GoRouter router;
  Future<http.Response> Function(http.Request)? handler;

  Harness() {
    state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) {
                requests.add(request);
                return handler!(request);
              }),
            )..token = 'synthetic-session',
          )
          ..user = {
            'id': 'child-user',
            'role': 'child',
            'child_id': 'child',
            'display_name': 'Testkind',
            'families': [],
          };
    router = GoRouter(
      initialLocation: '/language',
      routes: [
        GoRoute(
          path: '/language',
          builder: (_, _) =>
              LanguageWorkshop(state, childId: 'child', projectId: 'project'),
        ),
      ],
    );
  }

  Future<void> show(WidgetTester tester, double width) async {
    tester.view.physicalSize = Size(width, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(router.dispose);
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
  }
}

void main() {
  for (final width in [320.0, 390.0]) {
    testWidgets(
      'resume revalidates pending project at $width without a write',
      (tester) async {
        final h = Harness();
        final stale = Completer<http.Response>();
        var calls = 0;
        h.handler = (_) async {
          calls++;
          if (calls == 2) return stale.future;
          return reply(project(calls == 1 ? 'queued' : 'ready'));
        };
        await h.show(tester, width);
        expect(find.text('Wird vorbereitet'), findsOneWidget);
        await tester.pump(const Duration(seconds: 3));
        expect(calls, 2);
        tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
        await tester.pump();
        tester.binding.handleAppLifecycleStateChanged(
          AppLifecycleState.resumed,
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 100));
        expect(find.text('Bereit zum Üben'), findsOneWidget);
        stale.complete(reply(project('queued')));
        await tester.pump();
        expect(find.text('Bereit zum Üben'), findsOneWidget);
        expect(h.requests.every((r) => r.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
      },
    );
  }

  testWidgets('a backgrounded screen waits for resume before its first read', (
    tester,
  ) async {
    final h = Harness();
    h.handler = (_) async => reply(project('ready'));
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await h.show(tester, 390);
    expect(h.requests, isEmpty);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Bereit zum Üben'), findsOneWidget);
    expect(h.requests.every((r) => r.method == 'GET'), isTrue);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('a transient outage recovers on foreground without a write', (
    tester,
  ) async {
    final h = Harness();
    var calls = 0;
    h.handler = (_) async {
      calls++;
      if (calls == 1) return reply(project('queued'));
      if (calls == 2) return reply({'detail': 'Kurz offline'}, 503);
      return reply(project('ready'));
    };
    await h.show(tester, 390);
    await tester.pump(const Duration(seconds: 3));
    await tester.pump();
    expect(find.text('Kurz offline'), findsOneWidget);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.text('Bereit zum Üben'), findsOneWidget);
    expect(h.requests.every((r) => r.method == 'GET'), isTrue);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('session replacement discards a delayed private project', (
    tester,
  ) async {
    final h = Harness();
    final stale = Completer<http.Response>();
    h.handler = (_) => stale.future;
    await h.show(tester, 390);
    h.state.api.token = 'different-session';
    h.state.refreshState();
    await tester.pump();
    stale.complete(reply(project('ready')));
    await tester.pump();
    expect(find.text('Künstliches Sprachziel'), findsNothing);
    expect(h.requests.every((r) => r.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  for (final code in [403, 404, 429]) {
    testWidgets('HTTP $code stops background reads until explicit retry', (
      tester,
    ) async {
      final h = Harness();
      var calls = 0;
      h.handler = (_) async {
        calls++;
        if (calls == 1) return reply(project('queued'));
        if (calls == 2) {
          return reply({'detail': 'Künstlicher Lesefehler'}, code);
        }
        return reply(project('ready'));
      };
      await h.show(tester, 390);
      await tester.pump(const Duration(seconds: 3));
      await tester.pump();
      expect(find.text('Künstlicher Lesefehler'), findsOneWidget);
      if (code != 429) {
        expect(find.text('Künstliches Sprachziel'), findsNothing);
      }
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      await tester.pump(const Duration(seconds: 5));
      expect(calls, 2);
      await tester.tap(find.text('Erneut laden'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));
      expect(calls, 3);
      expect(find.text('Bereit zum Üben'), findsOneWidget);
      expect(h.requests.every((r) => r.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }
}
