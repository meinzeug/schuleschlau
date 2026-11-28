import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/admin_media_explorer_screen.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/ui.dart';

const mediaId = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';
const secondId = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
http.Response reply(Object body, [int status = 200]) => http.Response(
  jsonEncode(body),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

class Fixture {
  final calls = <http.Request>[];
  final opened = <Uri>[];
  bool conflict = false,
      unsafeUrl = false,
      malformedSave = false,
      failSave = false,
      failNextPage = false;
  String? candidateUrl;
  Json? existingReview;
  Completer<http.Response>? lateDetail, lateSave;
  late final state =
      AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient(handle),
          ),
        )
        ..user = {
          'id': '11111111111111111111111111111111',
          'role': 'admin',
          'display_name': 'Test',
        }
        ..api.token = 'synthetic-session';
  late GoRouter router;

  Json item(String id) => {
    'id': id,
    'provider': 'youtube',
    'title': 'Künstliches Video',
    'channel': 'Beispielkanal',
    'url':
        candidateUrl ??
        (unsafeUrl
            ? 'https://www.youtube.com@evil.example/watch?v=Abcdefgh_12'
            : 'https://www.youtube.com/watch?v=Abcdefgh_12'),
    'revision': 1,
    'available': true,
    'checked_at': 1704067200,
    'checked_region': 'DE',
    'review': existingReview,
  };

  Future<http.Response> handle(http.Request request) async {
    calls.add(request);
    final path = request.url.path;
    if (request.method == 'GET' && path == '/api/admin/media-explorer') {
      final after = request.url.queryParameters['after'];
      if (after != null && failNextPage) {
        return reply({'detail': 'offline'}, 503);
      }
      return reply({
        'items': [item(after == mediaId ? secondId : mediaId)],
        'next': after == null ? mediaId : null,
      });
    }
    if (request.method == 'GET' &&
        path == '/api/admin/media-explorer/$mediaId') {
      if (lateDetail != null) return lateDetail!.future;
      return reply(item(mediaId));
    }
    if (request.method == 'POST' &&
        path == '/api/admin/media-explorer/$mediaId/decisions') {
      if (lateSave != null) return lateSave!.future;
      if (conflict) return reply({'detail': 'changed'}, 409);
      if (failSave) return reply({'detail': 'temporary outage'}, 503);
      if (malformedSave) return reply({...item(mediaId), 'review': null});
      final body = jsonDecode(request.body) as Map;
      return reply({
        ...item(mediaId),
        'review': {
          'resource_revision': body['resource_revision'],
          'review_number': (body['previous_review'] as int) + 1,
          'decision': body['decision'],
          'evidence_scope': body['evidence_scope'],
        },
      });
    }
    throw StateError('Unexpected request: ${request.method} $path');
  }

  Iterable<http.Request> get writes =>
      calls.where((request) => request.method == 'POST');

  Future<void> mount(
    WidgetTester tester, {
    double width = 390,
    double scale = 1,
    bool settle = true,
  }) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = Size(width, 844);
    router = GoRouter(
      initialLocation: '/admin/media-explorer',
      routes: [
        GoRoute(
          path: '/admin/media-explorer',
          builder: (_, _) => AdminMediaExplorerScreen(
            state,
            openExternal: (uri) async {
              opened.add(uri);
              return true;
            },
          ),
        ),
        GoRoute(
          path: '/admin',
          builder: (_, _) => const Scaffold(body: Text('Betrieb')),
        ),
        GoRoute(
          path: '/app',
          builder: (_, _) => const Scaffold(body: Text('App')),
        ),
        GoRoute(
          path: '/foreign',
          builder: (_, _) => const Scaffold(body: Text('Andere Ansicht')),
        ),
      ],
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.inbox.dispose();
      state.dispose();
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });
    await tester.pumpWidget(
      MaterialApp.router(
        routerConfig: router,
        theme: appTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
      ),
    );
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
    }
  }
}

Future<void> tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  expect(finder.hitTestable(), findsOneWidget);
  await tester.tap(finder.hitTestable());
  await tester.pumpAndSettle();
}

Future<void> choose(WidgetTester tester, int index, String value) async {
  await tap(tester, find.byType(DropdownButtonFormField<String>).at(index));
  await tap(tester, find.text(value).last);
}

Future<void> selectCandidate(WidgetTester tester) async =>
    tap(tester, find.text('Medium prüfen'));

Future<void> fillBasics(
  WidgetTester tester, {
  String choice = 'Freigeben',
  String kind = 'Allgemein',
}) async {
  await choose(tester, 0, choice);
  await choose(tester, 1, kind);
  await tester.enterText(find.widgetWithText(TextField, 'Mindestalter'), '10');
  tester.testTextInput.hide();
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets(
    'only actual candidates load and explicit safe link opens externally',
    (tester) async {
      final f = Fixture();
      await f.mount(tester);
      expect(find.text('Künstliches Video'), findsOneWidget);
      expect(f.writes, isEmpty);
      expect(f.opened, isEmpty);
      await selectCandidate(tester);
      await tap(tester, find.text('Quelle extern öffnen'));
      expect(
        f.opened.single.toString(),
        'https://www.youtube.com/watch?v=Abcdefgh_12',
      );
      expect(f.writes, isEmpty);
    },
  );

  testWidgets('unsafe external URL cannot be opened', (tester) async {
    final f = Fixture()..unsafeUrl = true;
    await f.mount(tester);
    await selectCandidate(tester);
    expect(
      find.text('Metadaten geprüft (UTC): 01.01.2024 · Region: DE'),
      findsOneWidget,
    );
    final button = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Quelle extern öffnen'),
    );
    expect(button.onPressed, isNull);
    expect(f.opened, isEmpty);
  });

  testWidgets('external link cannot carry extra query parameters', (
    tester,
  ) async {
    final f = Fixture()
      ..candidateUrl =
          'https://www.youtube.com/watch?v=Abcdefgh_12&next=https://evil.example';
    await f.mount(tester);
    await selectCandidate(tester);
    final button = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Quelle extern öffnen'),
    );
    expect(button.onPressed, isNull);
    expect(f.opened, isEmpty);
  });

  testWidgets(
    'content review and historical context are required for approval',
    (tester) async {
      final f = Fixture();
      await f.mount(tester);
      await selectCandidate(tester);
      await fillBasics(tester, kind: 'Historische Quelle');
      await tap(tester, find.text('Entscheidung speichern'));
      expect(find.textContaining('Inhalt selbst prüfen'), findsOneWidget);
      expect(f.writes, isEmpty);
      await tap(
        tester,
        find.text('Ich habe den Inhalt selbst angesehen und geprüft.'),
      );
      await tap(tester, find.text('Entscheidung speichern'));
      expect(find.textContaining('altersgerechte Einordnung'), findsWidgets);
      expect(f.writes, isEmpty);
      await tester.enterText(
        find.widgetWithText(TextField, 'Altersgerechte Einordnung'),
        'Historischer Kontext',
      );
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await tap(tester, find.text('Entscheidung speichern'));
      final sent = jsonDecode(f.writes.single.body) as Map;
      expect(sent['resource_revision'], 1);
      expect(sent['previous_review'], 0);
      expect(sent['content_reviewed'], true);
      expect(sent['evidence_scope'], 'content');
      expect(sent['content_kind'], 'historical_source');
      expect(sent['context'], 'Historischer Kontext');
      expect(find.text('Entscheidung gespeichert.'), findsOneWidget);
    },
  );

  testWidgets(
    'sensitive approval needs counterpoint, but blocking can use metadata only',
    (tester) async {
      final f = Fixture();
      await f.mount(tester);
      await selectCandidate(tester);
      await fillBasics(tester, kind: 'Sensibler Inhalt');
      await tap(
        tester,
        find.text('Ich habe den Inhalt selbst angesehen und geprüft.'),
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Altersgerechte Einordnung'),
        'Einordnung',
      );
      tester.testTextInput.hide();
      await tester.pumpAndSettle();
      await tap(tester, find.text('Entscheidung speichern'));
      expect(find.textContaining('Gegenperspektive'), findsWidgets);
      expect(f.writes, isEmpty);
      await choose(tester, 0, 'Sperren');
      await tap(
        tester,
        find.text('Ich habe den Inhalt selbst angesehen und geprüft.'),
      );
      await tap(tester, find.text('Entscheidung speichern'));
      final sent = jsonDecode(f.writes.single.body) as Map;
      expect(sent['decision'], 'blocked');
      expect(sent['content_reviewed'], false);
      expect(sent['evidence_scope'], 'metadata');
    },
  );

  testWidgets('sensitive approval saves the explicit review and counterpoint', (
    tester,
  ) async {
    final f = Fixture();
    await f.mount(tester);
    await selectCandidate(tester);
    await fillBasics(tester, kind: 'Sensibler Inhalt');
    await tap(
      tester,
      find.text('Ich habe den Inhalt selbst angesehen und geprüft.'),
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Altersgerechte Einordnung'),
      'Kontext',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Gegenperspektive'),
      'Unabhängige Einordnung',
    );
    tester.testTextInput.hide();
    await tester.pumpAndSettle();
    await tap(tester, find.text('Entscheidung speichern'));
    final sent = jsonDecode(f.writes.single.body) as Map;
    expect(sent['decision'], 'approved');
    expect(sent['content_reviewed'], true);
    expect(sent['context'], 'Kontext');
    expect(sent['counterpoint'], 'Unabhängige Einordnung');
  });

  testWidgets('conflict ends stale editing without an automatic second write', (
    tester,
  ) async {
    final f = Fixture()..conflict = true;
    await f.mount(tester);
    await selectCandidate(tester);
    await fillBasics(tester, choice: 'Ablehnen');
    await tap(tester, find.text('Entscheidung speichern'));
    expect(find.textContaining('Stand wurde geändert'), findsOneWidget);
    expect(find.text('Entscheidung speichern'), findsNothing);
    expect(f.writes.length, 1);
  });

  testWidgets('late candidate result is discarded when a sign-in starts', (
    tester,
  ) async {
    final f = Fixture()..lateDetail = Completer<http.Response>();
    await f.mount(tester);
    await tester.tap(find.text('Medium prüfen'));
    await tester.pump();
    final revision = f.state.beginAuthentication();
    await tester.pump();
    f.lateDetail!.complete(reply(f.item(mediaId)));
    await tester.pumpAndSettle();
    f.state.cancelAuthentication(revision);
    await tester.pumpAndSettle();
    expect(find.text('Quelle extern öffnen'), findsNothing);
    expect(find.text('Ansicht wieder öffnen'), findsOneWidget);
    f.lateDetail = null;
    await tap(tester, find.text('Ansicht wieder öffnen'));
    expect(find.text('Medium prüfen'), findsOneWidget);
    expect(f.writes, isEmpty);
  });

  testWidgets('late save cannot show a result or repeat in a new sign-in', (
    tester,
  ) async {
    final f = Fixture()..lateSave = Completer<http.Response>();
    await f.mount(tester);
    await selectCandidate(tester);
    await fillBasics(tester, choice: 'Ablehnen');
    final save = tester
        .widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Entscheidung speichern'),
        )
        .onPressed!;
    save();
    await tester.pump();
    final revision = f.state.beginAuthentication();
    await tester.pump();
    f.lateSave!.complete(
      reply({
        ...f.item(mediaId),
        'review': {'review_number': 1, 'decision': 'rejected'},
      }),
    );
    await tester.pumpAndSettle();
    f.state.cancelAuthentication(revision);
    await tester.pumpAndSettle();
    save();
    await tester.pump();
    expect(f.writes.length, 1);
    expect(find.text('Entscheidung gespeichert.'), findsNothing);
  });

  testWidgets('leaving during a save requires a fresh detail read', (
    tester,
  ) async {
    final f = Fixture()..lateSave = Completer<http.Response>();
    await f.mount(tester);
    await selectCandidate(tester);
    await fillBasics(tester, choice: 'Ablehnen');
    final save = tester
        .widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Entscheidung speichern'),
        )
        .onPressed!;
    save();
    await tester.pump();
    f.router.push('/foreign');
    await tester.pumpAndSettle();
    f.lateSave!.complete(
      reply({
        ...f.item(mediaId),
        'review': {'review_number': 1, 'decision': 'rejected'},
      }),
    );
    await tester.pump();
    f.router.pop();
    await tester.pumpAndSettle();
    expect(find.textContaining('Speicherstand ist unklar'), findsOneWidget);
    expect(find.text('Entscheidung gespeichert.'), findsNothing);
    expect(f.writes.length, 1);
  });

  testWidgets('an incomplete save response is not shown as success', (
    tester,
  ) async {
    final f = Fixture()..malformedSave = true;
    await f.mount(tester);
    await selectCandidate(tester);
    await fillBasics(tester, choice: 'Sperren');
    await tap(tester, find.text('Entscheidung speichern'));
    expect(find.textContaining('Speicherstand ist unklar'), findsOneWidget);
    expect(find.text('Entscheidung gespeichert.'), findsNothing);
    expect(f.writes.length, 1);
  });

  testWidgets(
    'a failed save is treated as uncertain without an automatic retry',
    (tester) async {
      final f = Fixture()..failSave = true;
      await f.mount(tester);
      await selectCandidate(tester);
      await fillBasics(tester, choice: 'Ablehnen');
      await tap(tester, find.text('Entscheidung speichern'));
      expect(find.textContaining('Speicherstand ist unklar'), findsOneWidget);
      expect(find.text('Entscheidung gespeichert.'), findsNothing);
      expect(f.writes.length, 1);
    },
  );

  testWidgets('a later decision uses the shown review revision', (
    tester,
  ) async {
    final f = Fixture()
      ..existingReview = {
        'resource_revision': 1,
        'review_number': 3,
        'decision': 'approved',
        'evidence_scope': 'content',
        'min_age': 10,
        'context': 'Bisheriger Kontext',
        'counterpoint': '',
      };
    await f.mount(tester);
    await selectCandidate(tester);
    expect(find.text('Bisher: Freigabe vermerkt'), findsOneWidget);
    expect(find.text('Einordnung: Bisheriger Kontext'), findsOneWidget);
    await fillBasics(tester, choice: 'Sperren');
    await tap(tester, find.text('Entscheidung speichern'));
    expect((jsonDecode(f.writes.single.body) as Map)['previous_review'], 3);
  });

  testWidgets(
    'a review of an older source revision is not shown as current approval',
    (tester) async {
      final f = Fixture()
        ..existingReview = {
          'resource_revision': 0,
          'review_number': 3,
          'decision': 'approved',
          'evidence_scope': 'content',
          'min_age': 10,
          'context': '',
          'counterpoint': '',
        };
      await f.mount(tester);
      expect(find.text('Prüfstand: Frühere Prüfung veraltet'), findsOneWidget);
      await selectCandidate(tester);
      expect(find.text('Bisher: Frühere Prüfung veraltet'), findsOneWidget);
      expect(find.text('Bisher: Freigabe vermerkt'), findsNothing);
    },
  );

  testWidgets('a new sign-in closes a pending decision menu', (tester) async {
    final f = Fixture();
    await f.mount(tester);
    await selectCandidate(tester);
    await tap(tester, find.byType(DropdownButtonFormField<String>).first);
    expect(find.text('Freigeben'), findsWidgets);
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Freigeben'), findsNothing);
    expect(find.text('Entscheidung speichern'), findsNothing);
    expect(f.writes, isEmpty);
  });

  testWidgets('an old menu callback cannot alter a covered editor', (
    tester,
  ) async {
    final f = Fixture();
    await f.mount(tester);
    await selectCandidate(tester);
    final callback = tester
        .widget<DropdownButtonFormField<String>>(
          find.byType(DropdownButtonFormField<String>).first,
        )
        .onChanged!;
    f.router.push('/foreign');
    await tester.pumpAndSettle();
    callback('approved');
    await tester.pump();
    f.router.pop();
    await tester.pumpAndSettle();
    await choose(tester, 1, 'Allgemein');
    await tester.enterText(
      find.widgetWithText(TextField, 'Mindestalter'),
      '10',
    );
    tester.testTextInput.hide();
    await tester.pumpAndSettle();
    await tap(tester, find.text('Entscheidung speichern'));
    expect(find.textContaining('Bitte Entscheidung'), findsOneWidget);
    expect(f.writes, isEmpty);
  });

  testWidgets('parents cannot read admin media candidates', (tester) async {
    final f = Fixture();
    f.state.user = {'id': 'parent', 'role': 'parent'};
    await f.mount(tester);
    expect(f.calls, isEmpty);
    expect(find.text('Medium prüfen'), findsNothing);
  });

  testWidgets(
    'a failed page load keeps the current cursor and can be retried',
    (tester) async {
      final f = Fixture()..failNextPage = true;
      await f.mount(tester);
      await tap(tester, find.text('Weitere Kandidaten'));
      expect(find.textContaining('gerade nicht erreichbar'), findsOneWidget);
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Zurück'),
            )
            .onPressed,
        isNull,
      );
      f.failNextPage = false;
      await tap(tester, find.text('Weitere Kandidaten'));
      expect(f.calls.last.url.queryParameters['after'], mediaId);
      await tap(tester, find.text('Zurück'));
      expect(f.calls.last.url.queryParameters['after'], isNull);
    },
  );

  testWidgets('bounded next and previous pages are explicitly loaded', (
    tester,
  ) async {
    final f = Fixture();
    await f.mount(tester);
    await tap(tester, find.text('Weitere Kandidaten'));
    expect(f.calls.last.url.queryParameters['after'], mediaId);
    await tap(tester, find.text('Zurück'));
    expect(f.calls.last.url.queryParameters['after'], isNull);
    expect(f.writes, isEmpty);
  });

  for (final size in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets('editor remains usable at ${size.$1} and ${size.$2}× text', (
      tester,
    ) async {
      final f = Fixture();
      await f.mount(tester, width: size.$1, scale: size.$2);
      await selectCandidate(tester);
      await fillBasics(tester, choice: 'Sperren');
      await tap(tester, find.text('Entscheidung speichern'));
      expect(f.writes.length, 1);
      expect(tester.takeException(), isNull);
    });
  }
}
