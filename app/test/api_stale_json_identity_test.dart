import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

class ChunkedClient extends http.BaseClient {
  final entered = Completer<void>();
  final body = StreamController<List<int>>();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    entered.complete();
    return http.StreamedResponse(body.stream, 200);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  for (final method in ['GET', 'POST', 'PUT', 'DELETE']) {
    for (final change in ['account', 'token', 'intent']) {
      test(
        'late $method JSON is not delivered after $change changes',
        () async {
          final delayed = Completer<http.Response>();
          var sends = 0;
          final api = Api(
            base: 'https://example.invalid/api',
            client: MockClient((_) {
              sends++;
              return delayed.future;
            }),
          );
          final state = AppState(api: api)
            ..user = {'id': 'synthetic-old', 'role': 'parent'};
          api.token = 'synthetic-old-token';
          var unauthorized = 0;
          api.onUnauthorized = () => unauthorized++;
          final future = api.call(method, '/children/synthetic/private', {
            'x': 1,
          });
          final result = expectLater(
            future,
            throwsA(
              isA<ApiError>()
                  .having((e) => e.code, 'code', 'authentication_changed')
                  .having((e) => e.status, 'uncertain status', 0),
            ),
          );
          switch (change) {
            case 'account':
              state.user = {'id': 'synthetic-new', 'role': 'parent'};
            case 'token':
              api.token = 'synthetic-new-token';
            default:
              state.beginAuthentication();
          }
          delayed.complete(http.Response('{"private":"old"}', 200));
          await result;
          expect(sends, 1);
          expect(unauthorized, 0);
          state.dispose();
        },
      );
    }
  }

  test('a current JSON response still returns normally', () async {
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) async => http.Response('{"ok":true}', 200)),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic', 'role': 'parent'};
    expect(await api.get('/children/synthetic'), {'ok': true});
    state.dispose();
  });

  test('a late transport failure is also tied to its original login', () async {
    final delayed = Completer<http.Response>();
    final entered = Completer<void>();
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) {
        entered.complete();
        return delayed.future;
      }),
    );
    final state = AppState(api: api)
      ..user = {'id': 'synthetic', 'role': 'parent'};
    final future = api.post('/children/synthetic/write', {'x': 1});
    final result = expectLater(
      future,
      throwsA(
        isA<ApiError>()
            .having((e) => e.code, 'code', 'authentication_changed')
            .having((e) => e.status, 'uncertain status', 0),
      ),
    );
    await entered.future;
    state.beginAuthentication();
    delayed.completeError(http.ClientException('synthetic disconnect'));
    await result;
    state.dispose();
  });

  test(
    'a login change while reading response bytes discards the body',
    () async {
      final client = ChunkedClient();
      final state = AppState(
        api: Api(base: 'https://example.invalid/api', client: client),
      )..user = {'id': 'synthetic', 'role': 'parent'};
      final future = state.api.get('/children/synthetic/private');
      final result = expectLater(
        future,
        throwsA(
          isA<ApiError>().having(
            (e) => e.code,
            'code',
            'authentication_changed',
          ),
        ),
      );
      await client.entered.future;
      state.beginAuthentication();
      client.body.add('{"private":"old"}'.codeUnits);
      await client.body.close();
      await result;
      state.dispose();
    },
  );

  test(
    'a stale 401 does not expose its detail or revoke the new session',
    () async {
      final delayed = Completer<http.Response>();
      final entered = Completer<void>();
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) {
          entered.complete();
          return delayed.future;
        }),
      );
      final state = AppState(api: api)
        ..user = {'id': 'synthetic-old', 'role': 'parent'};
      var unauthorized = 0;
      api.onUnauthorized = () => unauthorized++;
      final result = expectLater(
        api.get('/children/synthetic/private'),
        throwsA(
          isA<ApiError>()
              .having((e) => e.code, 'code', 'authentication_changed')
              .having(
                (e) => e.message.contains('private'),
                'no old detail',
                isFalse,
              ),
        ),
      );
      await entered.future;
      state.beginAuthentication();
      delayed.complete(http.Response('{"detail":"private old session"}', 401));
      await result;
      expect(unauthorized, 0);
      state.dispose();
    },
  );
}
