import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/family_call_service.dart';

class PausedCalls extends FamilyCallService {
  PausedCalls(super.state) : super(nativeEnabled: false);
  final entered = Completer<void>();
  final release = Completer<void>();
  @override
  Future<void> clear() async {
    if (!entered.isCompleted) entered.complete();
    await release.future;
  }
}

class PausedStorage extends FlutterSecureStorage {
  final entered = Completer<void>();
  final release = Completer<void>();
  @override
  Future<void> delete({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (key == 'notebook_requests_v1') {
      entered.complete();
      await release.future;
    }
    await super.delete(
      key: key,
      iOptions: iOptions,
      aOptions: aOptions,
      lOptions: lOptions,
      webOptions: webOptions,
      mOptions: mOptions,
      wOptions: wOptions,
    );
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final transport in [
    'json',
    'photo',
    'pdf',
    'bytes',
    'avatar',
    'avatar-bytes',
  ]) {
    for (final change in ['none', 'token', 'account', 'cookie-revision']) {
      test(
        '$transport 401 belongs only to its $change request identity',
        () async {
          final response = Completer<http.Response>();
          final api = Api(
            base: 'https://example.invalid/api',
            client: MockClient((_) => response.future),
          );
          final state = AppState(api: api)
            ..user = {'id': 'synthetic', 'role': 'child'};
          api.token = change == 'cookie-revision' ? null : 'old-token';
          var unauthorized = 0;
          api.onUnauthorized = () => unauthorized++;
          final Future<dynamic> request = switch (transport) {
            'json' => api.get('/jobs/job'),
            'photo' => api.upload('child', Uint8List.fromList([1])),
            'pdf' => api.uploadGradePdf(
              'child',
              Uint8List.fromList([1]),
              'synthetic-key',
            ),
            'bytes' => api.bytes('/materials/page/image'),
            'avatar' => api.profileAvatarMetadata(),
            _ => api.profileAvatarBytes('a' * 32),
          };
          if (change == 'token') api.token = 'new-token';
          if (change == 'account') state.user = {'id': 'new', 'role': 'child'};
          if (change == 'cookie-revision') state.beginAuthentication();
          response.complete(
            http.Response(jsonEncode({'detail': 'expired'}), 401),
          );
          await expectLater(request, throwsA(isA<ApiError>()));
          expect(unauthorized, change == 'none' ? 1 : 0);
          state.dispose();
        },
      );
    }
  }

  test(
    'new authentication before the unauthorized cleanup microtask wins',
    () async {
      final state = AppState()..user = {'id': 'synthetic', 'role': 'child'};
      state.api.token = 'old';
      final owner = state.user;
      state.api.onUnauthorized!();
      state.beginAuthentication();
      state.api.token = 'new';
      await Future<void>.delayed(Duration.zero);
      expect(identical(state.user, owner), isTrue);
      expect(state.api.token, 'new');
      state.dispose();
    },
  );

  test('incorrect new login preserves the existing account', () async {
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient(
        (_) async => http.Response('{"detail":"Ungültig"}', 401),
      ),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic', 'role': 'child'};
    api.token = 'existing-session';
    final owner = state.user;
    await expectLater(
      state.login('synthetic', 'wrong'),
      throwsA(isA<ApiError>()),
    );
    await Future<void>.delayed(Duration.zero);
    expect(identical(state.user, owner), isTrue);
    expect(api.token, 'existing-session');
    state.dispose();
  });

  test(
    'current unauthorized response actually clears the revoked session',
    () async {
      late PausedCalls calls;
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (_) async => http.Response('{"detail":"expired"}', 401),
        ),
      );
      final state = AppState(
        api: api,
        familyCallFactory: (s) => calls = PausedCalls(s),
      )..user = {'id': 'synthetic', 'role': 'child'};
      expect(state.familyCalls, same(calls));
      api.token = 'revoked-session';
      final cleared = Completer<void>();
      state.addListener(() {
        if (state.user == null && !cleared.isCompleted) cleared.complete();
      });
      await expectLater(api.get('/jobs/job'), throwsA(isA<ApiError>()));
      await calls.entered.future;
      calls.release.complete();
      await cleared.future.timeout(const Duration(seconds: 10));
      expect(api.token, isNull);
      expect(state.user, isNull);
      state.dispose();
    },
  );

  test('account disappearance is notified before storage cleanup can be superseded', () async {
    late PausedCalls calls;
    final storage = PausedStorage();
    final state = AppState(
      storage: storage,
      familyCallFactory: (s) => calls = PausedCalls(s),
    )..user = {'id': 'synthetic', 'role': 'child'};
    expect(state.familyCalls, same(calls));
    state.api.token = 'revoked-session';
    var notifiedEmpty = false;
    state.addListener(() {
      if (state.user == null) notifiedEmpty = true;
    });
    final cleanup = state.clear();
    await calls.entered.future;
    calls.release.complete();
    await storage.entered.future;
    expect(notifiedEmpty, isTrue);
    state.beginAuthentication();
    storage.release.complete();
    await cleanup;
    expect(state.user, isNull);
    state.dispose();
  });

  test('unparseable proxy 401 does not authorize global logout', () async {
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) async => http.Response('<html>proxy</html>', 401)),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic', 'role': 'child'};
    var unauthorized = 0;
    api.onUnauthorized = () => unauthorized++;
    await expectLater(api.get('/jobs/job'), throwsA(isA<ApiError>()));
    expect(unauthorized, 0);
    expect(state.user, isNotNull);
    state.dispose();
  });

  for (final duringRequest in [false, true]) {
    test(
      'new login during logout ${duringRequest ? "request" : "preparation"} survives',
      () async {
        late PausedCalls calls;
        final sent = Completer<void>();
        final reply = Completer<http.Response>();
        final api = Api(
          base: 'https://example.invalid/api',
          client: MockClient((_) {
            sent.complete();
            return reply.future;
          }),
        );
        final state = AppState(
          api: api,
          familyCallFactory: (s) => calls = PausedCalls(s),
        )..user = {'id': 'synthetic', 'role': 'child'};
        expect(state.familyCalls, same(calls));
        api.token = 'old';
        final owner = state.user;
        final logout = state.logout();
        await calls.entered.future;
        if (duringRequest) {
          calls.release.complete();
          await sent.future;
        }
        state.beginAuthentication();
        if (duringRequest) {
          reply.complete(http.Response('{}', 200));
        } else {
          calls.release.complete();
        }
        await logout;
        expect(identical(state.user, owner), isTrue);
        expect(api.token, 'old');
        expect(sent.isCompleted, duringRequest);
        state.dispose();
      },
    );
  }

  for (final path in [
    '/setup/unlock',
    '/orders/example/payment-checkout',
    '/orders/example/withdrawal-form',
    '/admin/withdrawals/dashboard',
  ]) {
    test(
      'independent cookie failure at $path does not revoke app session',
      () async {
        final api = Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (_) async => http.Response('{"detail":"missing"}', 401),
          ),
        );
        final state = AppState(api: api)
          ..user = {'id': 'synthetic', 'role': 'parent'};
        var unauthorized = 0;
        api.onUnauthorized = () => unauthorized++;
        final request = path == '/setup/unlock'
            ? api.post(path)
            : api.get(path);
        await expectLater(request, throwsA(isA<ApiError>()));
        expect(unauthorized, 0);
        state.dispose();
      },
    );
  }

  test(
    'a new cookie-login intent while cleanup waits preserves the session',
    () async {
      late PausedCalls calls;
      final state = AppState(familyCallFactory: (s) => calls = PausedCalls(s))
        ..user = {'id': 'synthetic', 'role': 'child'};
      expect(state.familyCalls, same(calls));
      final owner = state.user;
      state.api.onUnauthorized!();
      await calls.entered.future;
      state.beginAuthentication();
      calls.release.complete();
      await Future<void>.delayed(Duration.zero);
      expect(identical(state.user, owner), isTrue);
      expect(state.api.token, isNull);
      state.dispose();
    },
  );
}
