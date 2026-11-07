import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

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
      test('$transport successful response after $change', () async {
        final response = Completer<http.Response>();
        final api = Api(
          base: 'https://example.invalid/api',
          client: MockClient((_) => response.future),
        );
        final state = AppState(api: api)
          ..user = {'id': 'synthetic-a', 'role': 'child'};
        api.token = change == 'cookie-revision' ? null : 'synthetic-old';
        final Future<dynamic> pending = switch (transport) {
          'json' => api.get('/children/test'),
          'photo' => api.upload('child', Uint8List.fromList([1])),
          'pdf' => api.uploadGradePdf(
            'child',
            Uint8List.fromList([1]),
            'synthetic-key',
          ),
          'bytes' => api.bytes('/materials/test/image'),
          'avatar' => api.profileAvatarMetadata(),
          _ => api.profileAvatarBytes('a' * 32),
        };
        if (change == 'token') api.token = 'synthetic-new';
        if (change == 'account') {
          state.user = {'id': 'synthetic-b', 'role': 'child'};
        }
        if (change == 'cookie-revision') state.beginAuthentication();
        response.complete(
          transport == 'bytes' || transport == 'avatar-bytes'
              ? http.Response.bytes(
                  [1, 2],
                  200,
                  headers: {'content-type': 'image/jpeg'},
                )
              : http.Response(jsonEncode({'ok': true}), 200),
        );
        if (change == 'none') {
          await pending;
        } else {
          await expectLater(
            pending,
            throwsA(
              isA<ApiError>().having((e) => e.code, 'code', 'stale_request'),
            ),
          );
        }
        state.dispose();
      });
    }
  }

  for (final transport in [
    'json',
    'photo',
    'pdf',
    'bytes',
    'avatar',
    'avatar-bytes',
  ]) {
    test('$transport transport error after account change is stale', () async {
      final response = Completer<http.Response>();
      final sent = Completer<void>();
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) {
          sent.complete();
          return response.future;
        }),
      );
      final state = AppState(api: api)
        ..user = {'id': 'synthetic-a', 'role': 'child'};
      final Future<dynamic> pending = switch (transport) {
        'json' => api.get('/children/test'),
        'photo' => api.upload('child', Uint8List.fromList([1])),
        'pdf' => api.uploadGradePdf(
          'child',
          Uint8List.fromList([1]),
          'synthetic-key',
        ),
        'bytes' => api.bytes('/materials/test/image'),
        'avatar' => api.profileAvatarMetadata(),
        _ => api.profileAvatarBytes('a' * 32),
      };
      final expectation = expectLater(
        pending,
        throwsA(
          isA<ApiError>()
              .having((e) => e.code, 'code', 'stale_request')
              .having((e) => e.status, 'status', 0),
        ),
      );
      await sent.future;
      state.user = {'id': 'synthetic-b', 'role': 'child'};
      response.completeError(StateError('synthetic transport error'));
      await expectation;
      state.dispose();
    });
  }

  test(
    'job does not poll in a different account after a successful start',
    () async {
      final calls = <String>[];
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request.url.path);
          return http.Response('{"id":"synthetic-job"}', 200);
        }),
      );
      final state = AppState(api: api)
        ..user = {'id': 'synthetic-a', 'role': 'child'};
      final result = api.job('/start');
      await Future<void>.delayed(const Duration(milliseconds: 20));
      state.user = {'id': 'synthetic-b', 'role': 'child'};
      await expectLater(
        result,
        throwsA(isA<ApiError>().having((e) => e.code, 'code', 'stale_request')),
      );
      expect(calls, ['/api/start']);
      state.dispose();
    },
  );

  test('an old failure cannot be presented as the new account error', () async {
    final response = Completer<http.Response>();
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) => response.future),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic-a', 'role': 'child'};
    var unauthorized = 0;
    api.onUnauthorized = () => unauthorized++;
    final pending = api.get('/children/test');
    state.user = {'id': 'synthetic-b', 'role': 'child'};
    response.complete(http.Response('{"detail":"old error"}', 401));
    await expectLater(
      pending,
      throwsA(isA<ApiError>().having((e) => e.code, 'code', 'stale_request')),
    );
    expect(unauthorized, 0);
    state.dispose();
  });

  test('a delayed successful login cannot replace the newer login', () async {
    final firstSent = Completer<void>();
    final firstReply = Completer<http.Response>();
    http.Response success(String id) => http.Response(
      jsonEncode({
        'user': {'id': id, 'role': 'parent', 'families': []},
        'token': 'synthetic-$id',
      }),
      200,
    );
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) {
        final user = jsonDecode(request.body)['username'];
        if (user == 'first') {
          firstSent.complete();
          return firstReply.future;
        }
        return Future.value(success('second'));
      }),
    );
    final state = AppState(api: api);
    final first = state.login('first', 'synthetic-password');
    await firstSent.future;
    await state.login('second', 'synthetic-password');
    firstReply.complete(success('first'));
    await expectLater(
      first,
      throwsA(isA<ApiError>().having((e) => e.code, 'code', 'stale_request')),
    );
    expect(state.user?['id'], 'second');
    state.dispose();
  });
}
