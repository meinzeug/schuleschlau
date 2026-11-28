import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_navigation.dart';
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as common;
import 'learning_subjects_151_test.dart' as fixture;

Map<String, dynamic> material(String status, {String? job}) => {
  'id': 'material',
  'kind': 'material',
  'subject': 'Mathematik',
  'topic': 'Künstliches Thema',
  'status': 'not_started',
  'automatic_preparation': {'status': status, 'job_id': job},
};

Future<http.Response> reply(http.Request q, Map<String, dynamic> item) async {
  if (q.url.path.endsWith('/learning/subjects')) {
    return fixture.response(fixture.catalog());
  }
  if (q.url.path.endsWith('/learning')) {
    return fixture.response({
      ...fixture.listing(),
      'random_available': false,
      'items': [
        {
          ...item,
          'kind': 'topic_group',
          'topic_card': true,
          'topic_key': 'c' * 64,
          'entries': [item],
          'group_count': 1,
        },
      ],
    });
  }
  return fixture.response({'items': []});
}

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Pending is understandable and never posts at $width / $scale',
      (t) async {
        final calls = <http.Request>[];
        await fixture.open(
          t,
          calls,
          width: width,
          scale: scale,
          initial: '/learn/child/subject/${fixture.math}',
          respond: (q) => reply(q, material('pending')),
        );
        expect(
          find.textContaining('Runde wartet auf Vorbereitung'),
          findsOneWidget,
        );
        expect(find.textContaining('Runde vorbereiten'), findsNothing);
        final tile = t.widget<ListTile>(find.byType(ListTile).last);
        expect(tile.onTap, isNull);
        expect(calls.every((c) => c.method == 'GET'), isTrue);
        expect(t.takeException(), isNull);
      },
    );
  }
  for (final (status, label) in [
    ('queued', 'Runde wartet auf Vorbereitung'),
    ('running', 'Deine Runde entsteht'),
    ('blocked', 'Vorbereitung angehalten'),
    ('ready', 'Runde ist bereit'),
  ]) {
    testWidgets('$status opens existing job without POST', (t) async {
      final calls = <http.Request>[];
      await fixture.open(
        t,
        calls,
        initial: '/learn/child/subject/${fixture.math}',
        respond: (q) => reply(q, material(status, job: 'job-1')),
      );
      expect(find.textContaining(label), findsOneWidget);
      await fixture.tap(t, find.text('Künstliches Thema').last);
      expect(find.text('Vorbereitung job-1'), findsOneWidget);
      expect(calls.every((c) => c.method == 'GET'), isTrue);
    });
  }
  testWidgets('Blocked without job offers its notebook page', (t) async {
    final calls = <http.Request>[];
    await fixture.open(
      t,
      calls,
      initial: '/learn/child/subject/${fixture.math}',
      respond: (q) => reply(q, material('blocked')),
    );
    expect(find.textContaining('Vorbereitung angehalten'), findsOneWidget);
    expect(t.widget<ListTile>(find.byType(ListTile).last).onTap, isNotNull);
    expect(calls.every((c) => c.method == 'GET'), isTrue);
  });
  testWidgets('Blocked intent opens its page without preparing anything', (
    t,
  ) async {
    final calls = <http.Request>[];
    final state = common.account((request) async {
      calls.add(request);
      return common.reply({'items': []});
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (context, _) => Scaffold(
            body: TextButton(
              onPressed: () => openPlanItem(context, state, {
                'child': {'id': 'child'},
              }, material('blocked')),
              child: const Text('Ansehen'),
            ),
          ),
        ),
        GoRoute(
          path: '/material/:id',
          builder: (_, s) =>
              Scaffold(body: Text('Heftseite ${s.pathParameters['id']}')),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.tap(find.text('Ansehen'));
    await t.pumpAndSettle();
    expect(find.text('Heftseite material'), findsOneWidget);
    expect(calls, isEmpty);
  });
  testWidgets('Failed auto job links to source without creating work', (
    t,
  ) async {
    final calls = <http.Request>[];
    final state = common.account((request) async {
      calls.add(request);
      return common.reply({
        'kind': 'unit',
        'status': 'failed',
        'error': 'Künstlicher Fehler',
        'notebook_retry_material_id': 'a' * 32,
      });
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
        ),
        GoRoute(
          path: '/material/:id',
          builder: (_, s) =>
              Scaffold(body: Text('Heftseite ${s.pathParameters['id']}')),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    final link = find.text('Heftseite ansehen');
    expect(link, findsOneWidget);
    await t.ensureVisible(link);
    await t.tap(link);
    await t.pumpAndSettle();
    expect(find.text('Heftseite ${'a' * 32}'), findsOneWidget);
    expect(calls.every((c) => c.method == 'GET'), isTrue);
  });
  testWidgets('Old status action cannot open a new session', (t) async {
    final calls = <http.Request>[];
    final (state, _) = await fixture.open(
      t,
      calls,
      initial: '/learn/child/subject/${fixture.math}',
      respond: (q) => reply(q, material('running', job: 'job-1')),
    );
    final action = t.widget<ListTile>(find.byType(ListTile).last).onTap!;
    final login = state.beginAuthentication();
    action();
    await t.pumpAndSettle();
    expect(find.text('Vorbereitung job-1'), findsNothing);
    expect(calls.every((c) => c.method == 'GET'), isTrue);
    state.cancelAuthentication(login);
  });
  testWidgets('Old failed-source action cannot cross a login', (t) async {
    final calls = <http.Request>[];
    final state = common.account((request) async {
      calls.add(request);
      return common.reply({
        'kind': 'unit',
        'status': 'failed',
        'error': 'Künstlicher Fehler',
        'notebook_retry_material_id': 'a' * 32,
      });
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) =>
              LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
        ),
        GoRoute(
          path: '/material/:id',
          builder: (_, _) => const Scaffold(body: Text('Alte Heftseite')),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    final button = t.widget<TextButton>(
      find.widgetWithText(TextButton, 'Heftseite ansehen'),
    );
    final action = button.onPressed!;
    final auth = state.beginAuthentication();
    action();
    await t.pumpAndSettle();
    expect(find.text('Alte Heftseite'), findsNothing);
    expect(calls.every((c) => c.method == 'GET'), isTrue);
    state.cancelAuthentication(auth);
  });
}
