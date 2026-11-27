import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image/image.dart' as image;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/pending_uploads.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as local;
import 'school_day_background_test.dart' as fixture;

Uint8List syntheticPhoto() =>
    Uint8List.fromList(image.encodePng(image.Image(width: 3, height: 3)));

class PausedReceiptStorage extends FlutterSecureStorage {
  bool pauseSaved = false;
  final entered = Completer<void>(), resume = Completer<void>();
  @override
  Future<void> write({
    required String key,
    required String? value,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (pauseSaved &&
        key == PendingUploads.receiptKey &&
        (value?.contains('"stage":"saved"') ?? false)) {
      pauseSaved = false;
      entered.complete();
      await resume.future;
    }
    return super.write(key: key, value: value);
  }
}

Future<void> mount(
  WidgetTester t,
  AppState state, {
  bool capture = false,
}) async {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) =>
            SchoolDayScreen(state, childId: 'child', startWithPhotos: capture),
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
  await t.pump();
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets(
    'late day response cannot cross login, and explicit reload uses GET',
    (t) async {
      final pending = Completer<http.Response>();
      final calls = <http.Request>[];
      final server = fixture.PreparationServer(pages: []);
      final state = local.account((request) {
        calls.add(request);
        if (calls.length == 1) return pending.future;
        return Future.value(fixture.response({'day': server.day}));
      });
      await mount(t, state);
      await t.pump();
      final intent = state.beginAuthentication();
      pending.complete(fixture.response({'day': server.day}));
      await fixture.settleUi(t);
      expect(find.text('Zeig mir deine Heftseiten'), findsNothing);
      expect(
        find.text(
          'Die Anmeldung hat sich geändert. Lade deinen Schultag erneut.',
        ),
        findsOneWidget,
      );
      expect(calls, hasLength(1));
      state.cancelAuthentication(intent);
      await fixture.settleUi(t);
      await fixture.tapText(t, 'Erneut laden');
      expect(find.text('Zeig mir deine Heftseiten'), findsOneWidget);
      expect(calls, hasLength(2));
      expect(calls.every((r) => r.method == 'GET'), isTrue);
    },
  );

  testWidgets('photo entry opened during login cannot read or create a day', (
    t,
  ) async {
    final calls = <http.Request>[];
    final state = local.account((request) async {
      calls.add(request);
      return fixture.response({'day': null});
    });
    final intent = state.beginAuthentication();
    await mount(t, state, capture: true);
    await fixture.settleUi(t);
    expect(calls, isEmpty);
    final retry = t.widget<ActionButton>(
      find.widgetWithText(ActionButton, 'Erneut laden'),
    );
    expect(retry.enabled, isFalse);
    await retry.onPressed();
    await t.pump();
    expect(calls, isEmpty);
    state.cancelAuthentication(intent);
    await fixture.settleUi(t);
    await fixture.tapText(t, 'Erneut laden');
    expect(calls, hasLength(1));
    expect(calls.single.method, 'GET');
    expect(t.takeException(), isNull);
  });

  testWidgets('old capture action is inert as login notification begins', (
    t,
  ) async {
    final server = fixture.PreparationServer(pages: []);
    final state = server.state();
    VoidCallback? earlyAction;
    state.authenticationChanges.addListener(() => earlyAction?.call());
    await mount(t, state);
    await fixture.settleUi(t);
    final button = t.widget<ActionButton>(
      find.byWidgetPredicate(
        (w) => w is ActionButton && w.label == 'Beispielseiten öffnen',
      ),
    );
    earlyAction = () {
      unawaited(button.onPressed());
    };
    state.beginAuthentication();
    await fixture.settleUi(t);
    expect(server.requests.every((r) => r.startsWith('GET ')), isTrue);
    expect(find.text('Beispielseiten öffnen'), findsNothing);
  });

  testWidgets(
    'pending photos survive interrupted login and are not uploaded automatically',
    (t) async {
      final server = fixture.PreparationServer(pages: []);
      final state = server.state();
      final saved = await state.pendingUploads.add(
        'kid',
        'child',
        'day',
        syntheticPhoto(),
      );
      await mount(t, state);
      await fixture.settleUi(t);
      expect(find.text('Fotos abgeben'), findsOneWidget);
      final intent = state.beginAuthentication();
      await fixture.settleUi(t);
      expect((await state.pendingUploads.read('kid')).single['key'], saved);
      state.cancelAuthentication(intent);
      await fixture.settleUi(t);
      await fixture.tapText(t, 'Erneut laden');
      expect(find.text('Fotos abgeben'), findsOneWidget);
      expect(server.uploads, 0);
      expect(server.submissions, 0);
    },
  );

  testWidgets(
    'reload after login change never recreates a missing day automatically',
    (t) async {
      final pending = Completer<http.Response>();
      final calls = <http.Request>[];
      final state = local.account((request) {
        calls.add(request);
        if (calls.length == 1) return pending.future;
        return Future.value(fixture.response({'day': null}));
      });
      await mount(t, state, capture: true);
      await t.pump();
      final intent = state.beginAuthentication();
      pending.complete(fixture.response({'day': null}));
      await fixture.settleUi(t);
      state.cancelAuthentication(intent);
      await fixture.settleUi(t);
      await fixture.tapText(t, 'Erneut laden');
      expect(find.text('Heutige Fotos beginnen'), findsOneWidget);
      expect(calls.every((r) => r.method == 'GET'), isTrue);
    },
  );

  testWidgets(
    'a pending local photo is not removed by an old upload after login changes',
    (t) async {
      final server = fixture.PreparationServer(pages: []);
      final storage = PausedReceiptStorage();
      final state =
          AppState(
              storage: storage,
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient(server.handle),
              ),
            )
            ..user = {
              'id': 'kid',
              'role': 'child',
              'child_id': 'child',
              'synthetic': true,
            };
      final key = await state.pendingUploads.add(
        'kid',
        'child',
        'day',
        syntheticPhoto(),
        receiptId: 'synthetic-receipt',
      );
      await mount(t, state);
      await fixture.settleUi(t);
      storage.pauseSaved = true;
      await t.ensureVisible(find.text('Fotos abgeben'));
      await t.tap(find.text('Fotos abgeben'));
      await t.pump();
      await t.runAsync(() => storage.entered.future);
      final intent = state.beginAuthentication();
      storage.resume.complete();
      await fixture.settleUi(t);
      expect((await state.pendingUploads.read('kid')).single['key'], key);
      expect(server.uploads, 1);
      expect(server.submissions, 0);
      state.cancelAuthentication(intent);
      await fixture.settleUi(t);
      await fixture.tapText(t, 'Erneut laden');
      expect(find.text('Fotos abgeben'), findsOneWidget);
      expect(server.uploads, 1);
    },
  );

  testWidgets('an old preparation failure cannot discard the new retry key', (
    t,
  ) async {
    fixture.mobile(t);
    final first = Completer<http.Response>(),
        second = Completer<http.Response>();
    final keys = <String>[];
    final server = fixture.PreparationServer();
    final state = local.account((request) {
      if (request.url.path.endsWith('/prepare')) {
        keys.add(request.headers['Idempotency-Key']!);
        if (keys.length == 1) return first.future;
        if (keys.length == 2) return second.future;
        return Future.value(fixture.response({'preparation': {}}, 202));
      }
      return server.handle(request);
    });
    await mount(t, state);
    await fixture.settleUi(t);
    await fixture.tapText(t, 'Fotos abgeben');
    expect(keys, hasLength(1));
    final intent = state.beginAuthentication();
    state.cancelAuthentication(intent);
    await fixture.settleUi(t);
    await fixture.tapText(t, 'Erneut laden');
    await fixture.tapText(t, 'Fotos abgeben');
    expect(keys, hasLength(2));
    expect(keys[1], keys[0]);
    first.complete(fixture.response({'detail': 'synthetic old failure'}, 503));
    await fixture.settleUi(t);
    second.completeError(TimeoutException('synthetic ambiguous transport'));
    await fixture.settleUi(t);
    await t.pump(const Duration(seconds: 5));
    await fixture.tapText(t, 'Fotos abgeben');
    expect(keys, hasLength(3));
    expect(keys[2], keys[0]);
    expect(t.takeException(), isNull);
  });
}
