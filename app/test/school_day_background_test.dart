import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:image/image.dart' as image;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/ui.dart';

http.Response response(Object data, [int status = 200]) => http.Response(
  jsonEncode(data),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Json source(int number, {bool confirmed = false, String status = 'review'}) => {
  'id': 'page$number',
  'child_id': 'child',
  'school_day_id': 'day',
  'page_number': number,
  'subject': 'Mathematik',
  'topic': 'Künstliche Bruchaufgabe $number',
  'content': 'Eigener künstlicher Testtext $number.',
  'homework': <String>[],
  'uncertainties': confirmed ? <String>[] : ['Bitte die Zahl prüfen.'],
  'confirmed': confirmed,
  'status': confirmed ? 'confirmed' : status,
  'synthetic': true,
  'fixture_id': null,
};

class PreparationServer {
  List<Json> pages;
  String stage;
  Json preparation;
  bool archived = false, realUploads = false, aiAvailable = true;
  int reads = 0, starts = 0, submissions = 0, savedForLater = 0, postponed = 0;
  int minutes = 8, uploads = 0;
  int? failUploadAt;
  final requests = <String>[];
  final keys = <String>[];
  List<Json> units = [];
  Json? todayOverride;
  Completer<http.Response>? delayedRead;
  PreparationServer({
    List<Json>? pages,
    this.stage = 'collecting',
    Json? preparation,
  }) : pages = pages ?? [source(1, status: 'uploaded')],
       preparation = preparation ?? {'status': 'idle', 'phase': null};

  Json get day => {
    'id': 'day',
    'child_id': 'child',
    'date': '2026-10-15',
    'stage': stage,
    'revision': 1,
    'read_only': archived,
    'allow_uploads': !archived,
    'max_pages': 24,
    'pages': pages,
    'confirmed_count': pages.where((p) => p['confirmed'] == true).length,
    'synthetic': !realUploads,
    'active_job': null,
    'last_error': null,
    'preparation': {
      'completed_pages': 0,
      'total_pages': pages.length,
      'job': null,
      'error': null,
      'can_retry': false,
      ...preparation,
    },
    'units': units,
    'plan': {'groups': [], 'notices': [], 'estimated_minutes': minutes},
  };

  Future<http.Response> handle(http.Request request) async {
    requests.add('${request.method} ${request.url.path}');
    if (request.method == 'GET' &&
        (request.url.path.endsWith('/school-day/today') ||
            request.url.path.endsWith('/school-days/day'))) {
      reads++;
      if (delayedRead != null) return delayedRead!.future;
      return response(
        request.url.path.endsWith('/today')
            ? {'day': todayOverride ?? day}
            : day,
      );
    }
    if (request.url.path.endsWith('/prepare')) {
      expect(request.method, 'POST');
      expect(request.body, isEmpty);
      expect(request.headers['Idempotency-Key'], isNotEmpty);
      keys.add(request.headers['Idempotency-Key']!);
      submissions++;
      stage = 'review';
      preparation = {
        'status': 'processing',
        'phase': pages.every((p) => p['confirmed'] == true)
            ? 'package'
            : 'extract',
        'job': {
          'id': 'job$submissions',
          'kind': 'preparation',
          'status': 'queued',
        },
      };
      return response({'preparation': day['preparation']}, 202);
    }
    if (request.url.path.endsWith('/save-for-later')) {
      savedForLater++;
      return response({});
    }
    if (request.method == 'PUT' && request.url.path.endsWith('/stage')) {
      stage = (jsonDecode(request.body) as Json)['stage'] as String;
      return response(day);
    }
    if (request.url.path.endsWith('/postpone')) {
      expect(request.method, 'POST');
      expect(request.body, isEmpty);
      postponed++;
      preparation = {'status': 'postponed', 'phase': 'review'};
      return response(day);
    }
    if (request.url.path.endsWith('/materials/delete-preview')) {
      return response({
        'count': 1,
        'unit_count': 1,
        'answer_count': 2,
        'selection_token': (jsonDecode(request.body)['ids'] as List).single,
      });
    }
    if (request.url.path.endsWith('/materials/bulk-delete')) {
      final body = jsonDecode(request.body);
      expect(body['delete_linked_units'], true);
      pages.removeWhere((page) => page['id'] == body['selection_token']);
      if (pages.isEmpty) stage = 'collecting';
      preparation = {'status': 'idle', 'phase': null};
      return response({'deleted_count': 1});
    }
    if (request.method == 'DELETE' &&
        request.url.path.startsWith('/api/school-days/day/pages/')) {
      final id = request.url.pathSegments.last;
      pages.removeWhere((page) => page['id'] == id);
      if (pages.isEmpty) stage = 'collecting';
      preparation = {'status': 'idle', 'phase': null};
      return response(day);
    }
    if (request.url.path.endsWith('/confirm')) {
      final body = jsonDecode(request.body) as Json;
      expect(body['uncertainties_resolved'], true);
      final page = pages.firstWhere(
        (p) => p['id'] == request.url.pathSegments[2],
      );
      page['confirmed'] = true;
      page['status'] = 'confirmed';
      page['uncertainties'] = <String>[];
      return response(page);
    }
    if (request.url.path.endsWith('/units/ready-unit/start')) {
      starts++;
      return response({});
    }
    if (request.url.path.endsWith('/status')) {
      return response({'real_data_enabled': true, 'ai_available': aiAvailable});
    }
    if (request.method == 'POST' && request.url.path.endsWith('/materials')) {
      uploads++;
      if (uploads == failUploadAt) {
        return response({'detail': 'Abgabe fehlgeschlagen'}, 503);
      }
      final page = source(uploads, status: 'uploaded');
      pages.add(page);
      return response(page, 201);
    }
    throw StateError('Unexpected synthetic test request');
  }

  AppState state() =>
      AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient(handle),
          ),
        )
        ..user = {
          'id': 'kid',
          'role': 'child',
          'child_id': 'child',
          'synthetic': true,
        };

  void requireReview() {
    stage = 'review';
    preparation = {'status': 'needs_review', 'phase': 'review'};
    for (final page in pages) {
      page['status'] = 'review';
    }
  }

  void ready() {
    stage = 'ready';
    preparation = {'status': 'ready', 'phase': 'complete'};
    units = [
      {
        'id': 'ready-unit',
        'status': 'ready',
        'subject': 'Mathematik',
        'topic': 'Künstliche Lernrunde',
      },
    ];
  }
}

GoRouter router(AppState state, {bool archived = false}) => GoRouter(
  initialLocation: '/after-school/child${archived ? '?day=day' : ''}',
  routes: [
    GoRoute(
      path: '/after-school/:id',
      builder: (_, route) => SchoolDayScreen(
        state,
        key: ValueKey('child:${route.uri.queryParameters['day'] ?? 'today'}'),
        childId: 'child',
        dayId: route.uri.queryParameters['day'],
      ),
    ),
    GoRoute(
      path: '/app',
      builder: (_, _) => const Scaffold(body: Text('Startseite')),
    ),
    GoRoute(
      path: '/away',
      builder: (_, _) => const Scaffold(body: Text('Andere Seite')),
    ),
    GoRoute(
      path: '/unit/:id',
      builder: (_, _) => const Scaffold(body: Text('Freiwillig gestartet')),
    ),
    GoRoute(
      path: '/library/:id',
      builder: (_, _) => const Scaffold(body: Text('Meine Hefte')),
    ),
  ],
);

Future<void> settleUi(WidgetTester tester) async {
  // A running server preparation intentionally has an indeterminate spinner;
  // pumpAndSettle would wait for that animation forever.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump();
}

Future<void> tapText(WidgetTester tester, String label) async {
  final control = find.text(label);
  await tester.ensureVisible(control);
  await tester.tap(control);
  await settleUi(tester);
}

Future<void> showPhotoDetails(WidgetTester tester) async {
  await tapText(tester, 'Fotos ansehen');
}

Future<void> reload(WidgetTester tester) async {
  final header = find.byKey(const ValueKey('page-tools-button'));
  await tester.ensureVisible(header);
  await settleUi(tester);
  expect(header.hitTestable(), findsOneWidget);
  await tester.tap(header);
  await settleUi(tester);
  final choice = find.byKey(
    const ValueKey('page-tools-choice:school-day-tools'),
  );
  await tester.ensureVisible(choice);
  await settleUi(tester);
  expect(choice.hitTestable(), findsOneWidget);
  await tester.tap(choice);
  await settleUi(tester);
  await settleUi(tester);
  await tapText(tester, 'Neu laden');
}

void mobile(WidgetTester tester, [double width = 390]) {
  tester.view.physicalSize = Size(width, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  testWidgets('four saved photos keep the hand-off action visible on a phone', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [for (var i = 1; i <= 4; i++) source(i)],
    );
    final navigation = router(server.state());
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    final submit = find.text('Fotos abgeben');
    expect(submit, findsOneWidget);
    final bounds = tester.getRect(submit);
    expect(bounds.top, greaterThan(0));
    expect(
      bounds.bottom,
      lessThan(
        tester.view.physicalSize.height / tester.view.devicePixelRatio - 80,
      ),
    );
    await tester.tap(submit);
    await settleUi(tester);
    expect(server.submissions, 1);
    expect(tester.takeException(), isNull);
  });

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('Photos hand off once and survive leaving before OCR finishes', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer();
    final state = server.state();
    final navigation = router(state);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    expect(server.submissions, 0);
    await tapText(tester, 'Fotos abgeben');
    expect(server.submissions, 1);
    expect(find.text('Wir lesen deine Heftseiten'), findsOneWidget);
    expect(
      server.requests.any(
        (r) => r.contains('/extract') || r.contains('/jobs/'),
      ),
      false,
    );
    await tapText(tester, 'Zur Startseite');
    expect(find.text('Startseite'), findsOneWidget);
    final readsAway = server.reads;
    server.requireReview();
    await tester.pump(const Duration(seconds: 12));
    expect(server.reads, readsAway);
    navigation.go('/after-school/child');
    await settleUi(tester);
    await showPhotoDetails(tester);
    expect(find.text('Seite 1'), findsOneWidget);
    expect(server.submissions, 1);
    expect(server.pages.single['confirmed'], false);
    expect(tester.takeException(), isNull);
  });

  for (final width in [320.0, 390.0, 1280.0]) {
    testWidgets('Review deletion can be cancelled and advances on $width px', (
      tester,
    ) async {
      mobile(tester, width);
      final server = PreparationServer(
        pages: [source(1), source(2)],
        stage: 'review',
        preparation: {'status': 'needs_review', 'phase': 'review'},
      );
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(find.byType(CheckboxListTile), findsNothing);
      await showPhotoDetails(tester);
      await tapText(tester, 'Seite löschen');
      expect(find.text('Heftseite löschen?'), findsOneWidget);
      expect(find.textContaining('verknüpfte Lernrunde'), findsOneWidget);
      await tapText(tester, 'Abbrechen');
      expect(server.pages, hasLength(2));
      expect(server.requests.where((r) => r.startsWith('DELETE ')), isEmpty);

      await tapText(tester, 'Seite löschen');
      expect(
        find.widgetWithText(FilledButton, 'Heftseite löschen'),
        findsOneWidget,
      );
      await tapText(tester, 'Heftseite löschen');
      expect(server.pages.single['id'], 'page2');
      expect(find.text('Seite 2'), findsOneWidget);
      expect(server.pages.single['confirmed'], false);

      await tapText(tester, 'Seite löschen');
      await tapText(tester, 'Heftseite löschen');
      expect(server.pages, isEmpty);
      expect(find.text('Zeig mir deine Heftseiten'), findsOneWidget);
      expect(
        server.requests.where((r) => r.contains('/materials/bulk-delete')),
        hasLength(2),
      );
      expect(server.requests.where((r) => r.contains('/confirm')), isEmpty);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Deleting the last archived review page returns home', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [source(1)],
      stage: 'review',
      preparation: {'status': 'needs_review', 'phase': 'review'},
    )..archived = true;
    final navigation = router(server.state(), archived: true);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    await showPhotoDetails(tester);
    await tapText(tester, 'Seite löschen');
    expect(
      find.widgetWithText(FilledButton, 'Heftseite löschen'),
      findsOneWidget,
    );
    await tapText(tester, 'Heftseite löschen');
    expect(server.pages, isEmpty);
    expect(find.text('Startseite'), findsOneWidget);
    expect(server.submissions, 0);
    expect(server.requests.where((r) => r.contains('/confirm')), isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Empty archived day opens notebooks without changing the day', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [],
      stage: 'review',
      preparation: {'status': 'needs_review', 'phase': 'review'},
    )..archived = true;
    final navigation = router(server.state(), archived: true);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    expect(find.text('Hier sind noch keine Heftseiten.'), findsOneWidget);
    await tapText(tester, 'Meine Heftseiten ansehen');
    expect(find.text('Meine Hefte'), findsOneWidget);
    expect(server.requests.every((r) => r.startsWith('GET ')), isTrue);
    expect(server.stage, 'review');
    expect(tester.takeException(), isNull);
  });

  for (final width in [320.0, 1280.0]) {
    testWidgets('Offene Seiten überlässt das Kind den Eltern auf $width px', (
      tester,
    ) async {
      mobile(tester, width);
      final server = PreparationServer(
        pages: [source(1)],
        stage: 'review',
        preparation: {'status': 'needs_review', 'phase': 'review'},
      );
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(server.pages.single['confirmed'], false);
      expect(find.byType(CheckboxListTile), findsNothing);
      expect(find.text('Stimmt, weiter'), findsNothing);
      expect(
        find.text(
          'Deine Fotos sind gespeichert. Wenn etwas unklar ist, können deine Eltern nachsehen.',
        ),
        findsOneWidget,
      );
      await showPhotoDetails(tester);
      expect(find.text('Seite 1'), findsOneWidget);
      expect(
        find.text(
          'Diese Seite prüfen deine Eltern. Dein Foto ist gespeichert.',
        ),
        findsOneWidget,
      );
      expect(server.pages.single['confirmed'], false);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets(
    'A child leaves pending photo review without confirming or restarting it',
    (tester) async {
      mobile(tester);
      final server = PreparationServer(
        pages: [source(1)],
        stage: 'review',
        preparation: {'status': 'needs_review', 'phase': 'review'},
      );
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(
        find.widgetWithText(ActionButton, 'Zur Startseite'),
        findsOneWidget,
      );
      expect(find.text('Seite 1'), findsNothing);
      await tapText(tester, 'Zur Startseite');
      expect(find.text('Startseite'), findsOneWidget);
      expect(server.pages.single['confirmed'], false);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
      expect(server.submissions, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Another photo remains reachable after the last source confirmation',
    (tester) async {
      mobile(tester);
      final server = PreparationServer(
        pages: [source(1)],
        stage: 'review',
        preparation: {'status': 'needs_review', 'phase': 'review'},
      )..realUploads = true;
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(find.text('Stimmt, weiter'), findsNothing);
      await tapText(tester, 'Noch eine Seite hinzufügen');
      expect(find.text('Fotos auswählen'), findsOneWidget);
      expect(
        tester
            .getSize(find.widgetWithText(ActionButton, 'Fotos auswählen'))
            .height,
        greaterThanOrEqualTo(48),
      );
      expect(server.pages.single['confirmed'], false);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Photo entry returns to a ready day without changing its stage', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [source(1, confirmed: true)],
      stage: 'ready',
      preparation: {'status': 'completed', 'phase': null},
    )..realUploads = true;
    final state = server.state();
    final navigation = GoRouter(
      initialLocation: '/after-school/child',
      routes: [
        GoRoute(
          path: '/after-school/:id',
          builder: (_, _) =>
              SchoolDayScreen(state, childId: 'child', startWithPhotos: true),
        ),
      ],
    );
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    expect(find.text('Mit diesen Seiten weiter'), findsOneWidget);
    await tapText(tester, 'Mit diesen Seiten weiter');
    expect(find.text('Zeig mir deine Heftseiten'), findsNothing);
    expect(find.text('Foto hinzufügen'), findsOneWidget);
    expect(find.text('Heftseiten und bisherige Runden'), findsNothing);
    expect(find.text('Fragen zu meinen Heftseiten'), findsNothing);
    await tapText(tester, 'Meine Heftseiten');
    expect(find.text('Heftseiten und bisherige Runden'), findsOneWidget);
    expect(find.text('Fragen zu meinen Heftseiten'), findsOneWidget);
    expect(find.text('Heftseite 1 · Mathematik'), findsOneWidget);
    expect(server.stage, 'ready');
    expect(server.requests.where((r) => r.startsWith('PUT ')), isEmpty);
    expect(server.submissions, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('A stale notebook tutor action cannot reopen across sign-in', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [source(1, confirmed: true)],
      stage: 'ready',
      preparation: {'status': 'completed', 'phase': null},
    )..realUploads = true;
    final state = server.state();
    final navigation = router(state);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    await tapText(tester, 'Meine Heftseiten');
    final oldAction = tester
        .widget<TextButton>(
          find.widgetWithText(TextButton, 'Fragen zu meinen Heftseiten'),
        )
        .onPressed!;
    final before = server.requests.length;
    final intent = state.beginAuthentication();
    oldAction();
    await tester.pumpAndSettle();
    expect(server.requests.length, before);
    state.cancelAuthentication(intent);
    oldAction();
    await tester.pumpAndSettle();
    expect(server.requests.length, before);
    expect(find.byType(BottomSheet), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('A long notebook list keeps search before the pages', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [for (var n = 1; n <= 4; n++) source(n, confirmed: true)],
      stage: 'ready',
      preparation: {'status': 'completed', 'phase': null},
    )..realUploads = true;
    final navigation = router(server.state());
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    await tapText(tester, 'Meine Heftseiten');
    expect(
      tester.getTopLeft(find.text('Suchen und filtern')).dy,
      lessThan(tester.getTopLeft(find.text('Heftseite 1 · Mathematik')).dy),
    );
    expect(server.requests.every((r) => r.startsWith('GET ')), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('A short notebook list opens its page after one disclosure', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [source(1, confirmed: true)],
      stage: 'ready',
      preparation: {'status': 'completed', 'phase': null},
    )..realUploads = true;
    final state = server.state();
    final navigation = GoRouter(
      initialLocation: '/after-school/child',
      routes: [
        GoRoute(
          path: '/after-school/:id',
          builder: (_, _) => SchoolDayScreen(state, childId: 'child'),
        ),
        GoRoute(
          path: '/material/:id',
          builder: (_, route) => Scaffold(
            body: Text('Gespeicherte Seite ${route.pathParameters['id']}'),
          ),
        ),
      ],
    );
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    await tapText(tester, 'Meine Heftseiten');
    await tapText(tester, 'Heftseite 1 · Mathematik');
    expect(find.text('Gespeicherte Seite page1'), findsOneWidget);
    expect(server.requests.every((r) => r.startsWith('GET ')), isTrue);
    expect(server.submissions, 0);
    expect(server.starts, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Persisted preparation stops reads in background and resumes without a POST',
    (tester) async {
      mobile(tester);
      final server = PreparationServer(
        stage: 'review',
        preparation: {'status': 'processing', 'phase': 'extract'},
      );
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      for (final lifecycle in [
        AppLifecycleState.inactive,
        AppLifecycleState.hidden,
        AppLifecycleState.paused,
      ]) {
        tester.binding.handleAppLifecycleStateChanged(lifecycle);
      }
      await tester.pump();
      final backgroundReads = server.reads;
      server.requireReview();
      await tester.pump(const Duration(seconds: 12));
      expect(server.reads, backgroundReads);
      for (final lifecycle in [
        AppLifecycleState.hidden,
        AppLifecycleState.inactive,
        AppLifecycleState.resumed,
      ]) {
        tester.binding.handleAppLifecycleStateChanged(lifecycle);
      }
      await settleUi(tester);
      await showPhotoDetails(tester);
      expect(find.text('Seite 1'), findsOneWidget);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('resume during a school-day read fetches the current status', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer()
      ..delayedRead = Completer<http.Response>();
    final delayed = server.delayedRead!;
    final oldDay = response({'day': server.day});
    final state = server.state();
    final navigation = router(state);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await tester.pump();
    await tester.pump();
    expect(server.reads, 1);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    await tester.pump();
    server.requireReview();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    server.delayedRead = null;
    delayed.complete(oldDay);
    await settleUi(tester);
    expect(server.reads, 2);
    await showPhotoDetails(tester);
    expect(find.text('Seite 1'), findsOneWidget);
    expect(
      server.requests.where((request) => !request.startsWith('GET ')),
      isEmpty,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'resumed school-day read cannot continue in a different session',
    (tester) async {
      mobile(tester);
      final server = PreparationServer()
        ..delayedRead = Completer<http.Response>();
      final delayed = server.delayedRead!;
      final state = server.state()..api.token = 'session-a';
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await tester.pump();
      await tester.pump();
      expect(server.reads, 1);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      state.api.token = 'session-b';
      state.refreshState();
      await tester.pump();
      server.delayedRead = null;
      delayed.complete(response({'day': server.day}));
      await settleUi(tester);
      expect(server.reads, 1);
      expect(find.text('Künstliche Bruchaufgabe 1'), findsNothing);
      expect(
        server.requests.where((request) => !request.startsWith('GET ')),
        isEmpty,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'Failed preparation only retries explicitly within the server bound',
    (tester) async {
      mobile(tester);
      final server = PreparationServer();
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      await tapText(tester, 'Fotos abgeben');
      server.preparation = {
        'status': 'failed',
        'phase': 'extract',
        'can_retry': true,
        'error': 'Künstlicher Anbieterfehler',
      };
      await tester.pump(const Duration(seconds: 3));
      await settleUi(tester);
      await reload(tester);
      expect(server.submissions, 1);
      expect(find.text('Was ist passiert?'), findsNothing);
      await tapText(tester, 'Lesen fortsetzen');
      expect(server.submissions, 2);
      expect(server.keys.toSet(), hasLength(2));
      server.preparation = {
        'status': 'failed',
        'phase': 'extract',
        'can_retry': false,
        'error': 'Künstliche Wiederholungsgrenze',
      };
      await tester.pump(const Duration(seconds: 3));
      await settleUi(tester);
      expect(find.text('Lesen fortsetzen'), findsNothing);
      await reload(tester);
      expect(server.submissions, 2);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Photo preflight offers saved rounds without parent detour or wasted retry',
    (tester) async {
      mobile(tester);
      final server = PreparationServer(
        preparation: {
          'status': 'failed',
          'phase': 'extract',
          'can_retry': false,
          'error_code': 'cost_preflight',
          'error': 'Private operator diagnostic must not become child copy',
        },
      );
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(
        find.widgetWithText(ActionPanel, 'Gespeicherte Runden ansehen'),
        findsOneWidget,
      );
      expect(find.text('Hefte öffnen'), findsOneWidget);
      expect(find.text('Was ist passiert?'), findsNothing);
      expect(
        find.text(
          'Das Vorbereiten hat nicht geklappt. Deine Fotos und bisherigen Runden bleiben gespeichert.',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('Deine Fotos'), findsWidgets);
      expect(find.textContaining('Bitte deine Eltern um Hilfe.'), findsNothing);
      expect(find.text('Erneut vorbereiten'), findsNothing);
      expect(find.text('Lesen fortsetzen'), findsNothing);
      expect(find.textContaining('Private operator diagnostic'), findsNothing);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('A covered preparation route stops polling until it returns', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      stage: 'review',
      preparation: {'status': 'processing', 'phase': 'extract'},
    );
    final navigation = router(server.state());
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    unawaited(navigation.push('/away'));
    await settleUi(tester);
    final hiddenReads = server.reads;
    server.requireReview();
    await tester.pump(const Duration(seconds: 12));
    expect(server.reads, hiddenReads);
    navigation.pop();
    await settleUi(tester);
    await showPhotoDetails(tester);
    expect(find.text('Seite 1'), findsOneWidget);
    expect(server.submissions, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'No remaining learning time keeps sources for later without AI or a start',
    (tester) async {
      mobile(tester);
      final server =
          PreparationServer(
              pages: [source(1, confirmed: true)],
              stage: 'review',
            )
            ..realUploads = true
            ..minutes = 0;
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(find.text('Im Hintergrund vorbereiten'), findsNothing);
      await tapText(tester, 'Für später einplanen');
      expect(server.savedForLater, 1);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(server.pages.single['confirmed'], true);
      expect(find.text('Startseite'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Yesterday stays saved and is reviewed by parents', (
    tester,
  ) async {
    mobile(tester);
    final server = PreparationServer(
      pages: [source(1)],
      stage: 'review',
      preparation: {'status': 'needs_review', 'phase': 'review'},
    )..archived = true;
    final navigation = router(server.state(), archived: true);
    addTearDown(navigation.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: navigation),
    );
    await settleUi(tester);
    await showPhotoDetails(tester);
    expect(find.text('Seite 1'), findsOneWidget);
    expect(find.text('Noch eine Seite hinzufügen'), findsNothing);
    expect(find.byType(CheckboxListTile), findsNothing);
    expect(find.text('Stimmt, weiter'), findsNothing);
    expect(
      find.text('Diese Seite prüfen deine Eltern. Dein Foto ist gespeichert.'),
      findsOneWidget,
    );
    expect(server.submissions, 0);
    expect(server.starts, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Photo selection is available during temporary AI unavailability',
    (tester) async {
      mobile(tester);
      const picker = MethodChannel('plugins.flutter.io/image_picker');
      var pickerCalls = 0;
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(picker, (
        call,
      ) async {
        expect(call.method, 'pickMultiImage');
        pickerCalls++;
        return <String>[];
      });
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          picker,
          null,
        ),
      );
      final server = PreparationServer(pages: [])
        ..realUploads = true
        ..aiAvailable = false;
      final navigation = router(server.state());
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      await tapText(tester, 'Fotos auswählen');
      expect(find.byType(AlertDialog), findsNothing);
      expect(pickerCalls, 1);
      expect(server.submissions, 0);
      expect(find.textContaining('gerade nicht erreichbar'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'An unreadable archived page is kept while restarting with today photos',
    (tester) async {
      mobile(tester);
      final server =
          PreparationServer(
              pages: [source(1, status: 'unreadable')],
              stage: 'review',
              preparation: {'status': 'needs_photo', 'phase': 'review'},
            )
            ..archived = true
            ..units = [
              {
                'id': 'old-unit',
                'status': 'completed',
                'subject': 'Mathematik',
                'topic': 'Alte künstliche Runde',
              },
            ];
      final oldSources = jsonEncode(server.pages);
      final oldUnits = jsonEncode(server.units);
      final navigation = router(server.state(), archived: true);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(find.text('Ersetzen'), findsNothing);
      await tapText(tester, 'Für später ablegen');
      expect(server.postponed, 1);
      expect(find.text('Für später abgelegt'), findsOneWidget);
      expect(find.text('Dein Lernpaket ist bereit'), findsNothing);
      expect(jsonEncode(server.pages), oldSources);
      expect(jsonEncode(server.units), oldUnits);
      server.todayOverride = {
        ...server.day,
        'id': 'today-day',
        'stage': 'collecting',
        'read_only': false,
        'allow_uploads': true,
        'pages': <Json>[],
        'confirmed_count': 0,
        'units': <Json>[],
        'preparation': {'status': 'idle', 'phase': null},
      };
      await tapText(tester, 'Heute neu fotografieren');
      expect(
        navigation.routeInformationProvider.value.uri.queryParameters['day'],
        isNull,
      );
      expect(find.text('Zeig mir deine Heftseiten'), findsOneWidget);
      expect(server.submissions, 0);
      expect(server.starts, 0);
      expect(jsonEncode(server.pages), oldSources);
      expect(jsonEncode(server.units), oldUnits);
      expect(server.requests.any((r) => r.startsWith('DELETE ')), false);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'A late response from a logged out child never restores its sources',
    (tester) async {
      mobile(tester);
      final server = PreparationServer()
        ..delayedRead = Completer<http.Response>();
      final state = server.state();
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await tester.pump();
      state.user = {
        'id': 'other-kid',
        'role': 'child',
        'child_id': 'other-child',
      };
      state.refreshState();
      server.delayedRead!.complete(response({'day': server.day}));
      await settleUi(tester);
      expect(find.text('Fotos abgeben'), findsNothing);
      expect(find.text('Künstliche Bruchaufgabe 1'), findsNothing);
      expect(server.submissions, 0);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'Photo selection stays local until explicit submission; optional editor preserves drafts',
    (tester) async {
      mobile(tester);
      final dir = await tester.runAsync(
        () => Directory.systemTemp.createTemp('schulpilot-gallery-bulk-'),
      );
      addTearDown(() => dir!.delete(recursive: true));
      final paths = <String>[];
      await tester.runAsync(() async {
        for (var i = 0; i < 3; i++) {
          final photo = image.Image(width: 30, height: 40);
          photo.setPixelRgb(i + 1, 1, 20, 40, 60);
          final file = File('${dir!.path}/page-$i.png');
          await file.writeAsBytes(image.encodePng(photo));
          paths.add(file.path);
        }
      });
      const picker = MethodChannel('plugins.flutter.io/image_picker');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        picker,
        (call) async => paths,
      );
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          picker,
          null,
        ),
      );
      final server = PreparationServer(pages: [])..realUploads = true;
      final state = server.state();
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      await tapText(tester, 'Fotos auswählen');
      for (
        var wait = 0;
        wait < 300 && (await state.pendingUploads.read('kid')).length < 3;
        wait++
      ) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      expect(await state.pendingUploads.read('kid'), hasLength(3));
      expect(find.text('Foto übernehmen'), findsNothing);
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.text('Noch eine Seite fotografieren'), findsOneWidget);
      expect(find.text('Erste Seite fotografieren'), findsNothing);
      expect(
        tester.getTopLeft(find.byTooltip('Foto 1 ansehen')).dy,
        lessThan(tester.getTopLeft(find.text('Fotos abgeben')).dy),
      );
      expect(
        tester.getBottomRight(find.text('Fotos abgeben')).dy,
        lessThan(844),
      );
      expect(server.uploads, 0);
      expect(server.submissions, 0);
      final thumbnail = find.descendant(
        of: find.byTooltip('Foto 1 ansehen'),
        matching: find.byType(Image),
      );
      expect(tester.getSize(thumbnail), const Size(40, 40));
      final previewBounds = tester.getRect(find.byTooltip('Foto 1 ansehen'));
      final editBounds = tester.getRect(find.byTooltip('Foto 1 bearbeiten'));
      expect(previewBounds.right, lessThanOrEqualTo(editBounds.left));
      await tester.ensureVisible(find.byTooltip('Foto 1 bearbeiten'));
      await tester.tap(find.byTooltip('Foto 1 bearbeiten'));
      await settleUi(tester);
      expect(find.text('Foto übernehmen'), findsOneWidget);
      await tester.tap(find.text('Abbrechen').last);
      await settleUi(tester);
      expect(await state.pendingUploads.read('kid'), hasLength(3));
      await tapText(tester, 'Fotos abgeben');
      for (var wait = 0; wait < 300 && server.submissions < 1; wait++) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      expect(server.uploads, 3);
      expect(server.submissions, 1);
      final receipts = await state.pendingUploads.receipts('kid');
      expect(receipts.where((r) => r['stage'] == 'saved'), hasLength(3));
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'Direct gallery submission handles photos exceeding the local batch limit',
    (tester) async {
      mobile(tester);
      final dir = await tester.runAsync(
        () => Directory.systemTemp.createTemp('schulpilot-direct-gallery-'),
      );
      addTearDown(() => dir!.delete(recursive: true));
      final paths = <String>[];
      await tester.runAsync(() async {
        final random = Random(1234);
        final photo = image.Image(width: 1000, height: 1000);
        for (var y = 0; y < photo.height; y++) {
          for (var x = 0; x < photo.width; x++) {
            photo.setPixelRgb(
              x,
              y,
              random.nextInt(256),
              random.nextInt(256),
              random.nextInt(256),
            );
          }
        }
        final bytes = image.encodeJpg(photo, quality: 95);
        expect(bytes.length * 4, greaterThan(3 * 1024 * 1024));
        for (var i = 0; i < 4; i++) {
          final file = File('${dir!.path}/page-$i.jpg');
          await file.writeAsBytes(bytes);
          paths.add(file.path);
        }
      });
      const picker = MethodChannel('plugins.flutter.io/image_picker');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        picker,
        (call) async => paths,
      );
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          picker,
          null,
        ),
      );
      final server = PreparationServer(pages: [])..realUploads = true;
      final state = server.state();
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      expect(find.text('Fotos auswählen und abgeben'), findsNothing);
      await tapText(tester, 'Fotos direkt abgeben');
      await tapText(tester, 'Fotos auswählen und abgeben');
      for (var wait = 0; wait < 600 && server.submissions == 0; wait++) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      expect(server.uploads, 4);
      expect(server.submissions, 1);
      expect(await state.pendingUploads.read('kid'), isEmpty);
      expect(
        (await state.pendingUploads.receipts('kid'))
            .where((r) => r['stage'] == 'saved'),
        hasLength(4),
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'Direct gallery failure preserves the pending photo and stops processing',
    (tester) async {
      mobile(tester);
      final dir = await tester.runAsync(
        () => Directory.systemTemp.createTemp('schulpilot-direct-failure-'),
      );
      addTearDown(() => dir!.delete(recursive: true));
      final paths = <String>[];
      await tester.runAsync(() async {
        for (var i = 0; i < 3; i++) {
          final file = File('${dir!.path}/page-$i.png');
          await file.writeAsBytes(
            image.encodePng(image.Image(width: 30, height: 40)),
          );
          paths.add(file.path);
        }
      });
      const picker = MethodChannel('plugins.flutter.io/image_picker');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        picker,
        (call) async => paths,
      );
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          picker,
          null,
        ),
      );
      final server = PreparationServer(pages: [])
        ..realUploads = true
        ..failUploadAt = 2;
      final state = server.state();
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      await tapText(tester, 'Fotos direkt abgeben');
      await tapText(tester, 'Fotos auswählen und abgeben');
      for (var wait = 0; wait < 300 && server.uploads < 2; wait++) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      await settleUi(tester);
      expect(server.uploads, 2);
      expect(server.pages, hasLength(1));
      expect(server.submissions, 0);
      expect(await state.pendingUploads.read('kid'), hasLength(1));
      final receipts = await state.pendingUploads.receipts('kid');
      expect(receipts.where((r) => r['stage'] == 'saved'), hasLength(1));
      expect(receipts.where((r) => r['stage'] == 'queued'), hasLength(1));
      expect(receipts.where((r) => r['stage'] == 'not_accepted'), hasLength(1));
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'Ten selected files retain eight local drafts and two clear rejections',
    (tester) async {
      mobile(tester);
      final dir = await tester.runAsync(
        () => Directory.systemTemp.createTemp('schulpilot-gallery-'),
      );
      addTearDown(() => dir!.delete(recursive: true));
      final paths = <String>[];
      await tester.runAsync(() async {
        for (var i = 0; i < 10; i++) {
          final photo = image.Image(width: 30, height: 40);
          photo.setPixelRgb(i + 1, 1, 20, 40, 60);
          final file = File('${dir!.path}/page-$i.png');
          await file.writeAsBytes(image.encodePng(photo));
          paths.add(file.path);
        }
      });
      const picker = MethodChannel('plugins.flutter.io/image_picker');
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        picker,
        (call) async => paths,
      );
      addTearDown(
        () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
          picker,
          null,
        ),
      );
      final server = PreparationServer(pages: [])..realUploads = true;
      final state = server.state();
      final navigation = router(state);
      addTearDown(navigation.dispose);
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: navigation),
      );
      await settleUi(tester);
      await tapText(tester, 'Fotos auswählen');
      for (
        var wait = 0;
        wait < 300 && (await state.pendingUploads.receipts('kid')).length < 10;
        wait++
      ) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      for (
        var wait = 0;
        wait < 300 && (await state.pendingUploads.read('kid')).length < 8;
        wait++
      ) {
        await tester.runAsync(
          () => Future<void>.delayed(const Duration(milliseconds: 30)),
        );
        await settleUi(tester);
      }
      expect(await state.pendingUploads.read('kid'), hasLength(8));
      final receipts = await state.pendingUploads.receipts('kid');
      expect(receipts, hasLength(10));
      expect(receipts.where((r) => r['stage'] == 'queued'), hasLength(8));
      expect(receipts.where((r) => r['stage'] == 'not_accepted'), hasLength(2));
      expect(server.uploads, 0);
      expect(server.submissions, 0);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  for (final mode in ['recovered', 'gallery', 'direct']) {
    testWidgets(
      '$mode photo cannot cross an account change during collection handoff',
      (tester) async {
        final recovered = mode == 'recovered';
        mobile(tester);
        final server = PreparationServer(pages: [], stage: 'review')
          ..realUploads = true;
        final handoff = Completer<http.Response>();
        var collectingRequested = false;
        final state = AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) {
              if (request.method == 'PUT' &&
                  request.url.path.endsWith('/stage')) {
                collectingRequested = true;
                return handoff.future;
              }
              return server.handle(request);
            }),
          ),
        )..user = {'id': 'kid', 'role': 'child', 'child_id': 'child'};
        final bytes = image.encodePng(image.Image(width: 30, height: 40));
        if (recovered) {
          state.recoveredPhoto = bytes;
        } else {
          final dir = await tester.runAsync(
            () =>
                Directory.systemTemp.createTemp('schulpilot-account-gallery-'),
          );
          addTearDown(() => dir!.delete(recursive: true));
          final file = File('${dir!.path}/artificial.png');
          await tester.runAsync(() => file.writeAsBytes(bytes));
          const picker = MethodChannel('plugins.flutter.io/image_picker');
          tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
            picker,
            (_) async => [file.path],
          );
          addTearDown(
            () => tester.binding.defaultBinaryMessenger
                .setMockMethodCallHandler(picker, null),
          );
        }
        final navigation = GoRouter(
          initialLocation: '/after-school/child',
          routes: [
            GoRoute(
              path: '/after-school/:id',
              builder: (_, _) => SchoolDayScreen(
                state,
                childId: 'child',
                startWithPhotos: true,
              ),
            ),
          ],
        );
        addTearDown(navigation.dispose);
        await tester.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: navigation),
        );
        await settleUi(tester);
        if (recovered) {
          await tapText(tester, 'Letztes Foto wiederfinden');
        } else {
          if (mode == 'direct') {
            await tapText(tester, 'Fotos direkt abgeben');
          }
          await tapText(
            tester,
            mode == 'direct'
                ? 'Fotos auswählen und abgeben'
                : 'Fotos auswählen',
          );
        }
        for (var wait = 0; wait < 100 && !collectingRequested; wait++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 30)),
          );
          await settleUi(tester);
        }
        expect(collectingRequested, isTrue);

        // accept() changes the identity before awaiting native session storage
        // and notifying listeners. The owner check must cover that interval.
        state.user = {
          'id': 'other-kid',
          'role': 'child',
          'child_id': 'other-child',
        };
        handoff.complete(response({...server.day, 'stage': 'collecting'}));
        await settleUi(tester);
        expect(await state.pendingUploads.read('other-kid'), isEmpty);
        expect(server.uploads, 0);
        expect(server.submissions, 0);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
      },
    );
  }
}
