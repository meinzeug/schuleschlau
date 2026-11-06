import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test(
    'API assertion follows current account without granting a session',
    () async {
      final requests = <http.Request>[];
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          return http.Response(
            jsonEncode({'ok': true}),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );
      final state = AppState(api: api);
      await api.get('/auth/me');
      expect(requests.last.headers['X-Schulpilot-Account'], isNull);
      state.user = {'id': 'synthetic-a', 'role': 'parent'};
      await api.get('/children/child/learning-plan');
      expect(requests.last.headers['X-Schulpilot-Account'], 'synthetic-a');
      expect(requests.last.headers['Authorization'], isNull);
      state.user = {'id': 'synthetic-b', 'role': 'child'};
      await api.post('/auth/logout');
      expect(requests.last.headers['X-Schulpilot-Account'], 'synthetic-b');
      state.user = null;
      await api.get('/auth/me');
      expect(requests.last.headers['X-Schulpilot-Account'], isNull);
      state.dispose();
    },
  );

  test('successful login replaces the assertion for later requests', () async {
    final requests = <http.Request>[];
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(
            request.url.path.endsWith('/auth/login')
                ? {
                    'user': {
                      'id': 'synthetic-new',
                      'role': 'parent',
                      'families': [],
                    },
                    'token': 'synthetic-token',
                  }
                : {'ok': true},
          ),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );
    final state = AppState(api: api);
    await state.login('synthetic-new', 'synthetic-password');
    await api.get('/auth/me');
    expect(requests.last.headers['X-Schulpilot-Account'], 'synthetic-new');
    state.dispose();
  });

  test(
    'explicit logout after changed cookie removes only local old account',
    () async {
      final requests = <http.Request>[];
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          return http.Response(
            jsonEncode({'detail': 'Bitte melde dich erneut an.'}),
            409,
            headers: {
              'content-type': 'application/json',
              'x-schulpilot-account-changed': '1',
            },
          );
        }),
      );
      final state = AppState(api: api)
        ..user = {'id': 'synthetic-old', 'role': 'parent'};
      api.token = 'synthetic-old-token';
      await state.logout(expectedAccountId: 'synthetic-old');
      expect(state.user, isNull);
      expect(api.token, isNull);
      expect(requests, hasLength(1));
      expect(requests.single.url.path, '/api/auth/logout');
      expect(requests.single.headers['X-Schulpilot-Account'], 'synthetic-old');
      state.dispose();
    },
  );

  test('other conflicts do not silently discard the local account', () async {
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({'detail': 'Anderer Konflikt'}),
          409,
          headers: {'content-type': 'application/json'},
        ),
      ),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic-old', 'role': 'parent'};
    await expectLater(state.logout(), throwsA(isA<ApiError>()));
    expect(state.user?['id'], 'synthetic-old');
    state.dispose();
  });

  test('a late mismatch cannot clear a newer account', () async {
    final reply = Completer<http.Response>();
    final sent = Completer<void>();
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) {
        sent.complete();
        return reply.future;
      }),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic-old', 'role': 'parent'};
    final logout = state.logout();
    await sent.future;
    state.user = {'id': 'synthetic-new', 'role': 'parent'};
    reply.complete(
      http.Response(
        jsonEncode({'detail': 'Bitte melde dich erneut an.'}),
        409,
        headers: {
          'content-type': 'application/json',
          'x-schulpilot-account-changed': '1',
        },
      ),
    );
    await logout;
    expect(state.user?['id'], 'synthetic-new');
    state.dispose();
  });
}
