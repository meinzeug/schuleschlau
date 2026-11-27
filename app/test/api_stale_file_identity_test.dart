import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

class ChunkedFileClient extends http.BaseClient {
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
  for (final transport in ['bytes', 'photo', 'pdf']) {
    for (final change in ['account', 'token', 'intent']) {
      test(
        'late $transport result is not delivered after $change changes',
        () async {
          final delayed = Completer<http.Response>();
          final entered = Completer<void>();
          var sends = 0;
          final requests = <http.Request>[];
          final api = Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) {
              sends++;
              requests.add(request);
              entered.complete();
              return delayed.future;
            }),
          );
          final state = AppState(api: api)
            ..user = {'id': 'synthetic-old', 'role': 'parent'};
          api.token = 'synthetic-token';
          final Future<dynamic> request = switch (transport) {
            'bytes' => api.bytes('/materials/synthetic/image'),
            'photo' => api.upload(
              'synthetic',
              Uint8List.fromList([1]),
              uploadKey: 'synthetic-key',
            ),
            _ => api.uploadGradePdf(
              'synthetic',
              Uint8List.fromList([1]),
              'synthetic-key',
            ),
          };
          final result = expectLater(
            request,
            throwsA(
              isA<ApiError>()
                  .having((e) => e.code, 'code', 'authentication_changed')
                  .having((e) => e.status, 'uncertain status', 0),
            ),
          );
          await entered.future;
          switch (change) {
            case 'account':
              state.user = {'id': 'synthetic-new', 'role': 'parent'};
            case 'token':
              api.token = 'synthetic-new-token';
            default:
              state.beginAuthentication();
          }
          delayed.complete(
            transport == 'bytes'
                ? http.Response.bytes([1, 2, 3], 200)
                : http.Response('{"id":"synthetic"}', 200),
          );
          await result;
          expect(sends, 1);
          if (transport != 'bytes') {
            expect(requests.single.headers['Idempotency-Key'], 'synthetic-key');
          }
          state.dispose();
        },
      );
    }
  }
  for (final transport in ['bytes', 'photo', 'pdf']) {
    test('late $transport 401 cannot clear a newer login', () async {
      final delayed = Completer<http.Response>();
      final entered = Completer<void>();
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) {
          entered.complete();
          return delayed.future;
        }),
      );
      final state = AppState(api: api)..user = {'id': 'old', 'role': 'parent'};
      var unauthorized = 0;
      api.onUnauthorized = () => unauthorized++;
      final Future<dynamic> request = switch (transport) {
        'bytes' => api.bytes('/materials/synthetic/image'),
        'photo' => api.upload(
          'synthetic',
          Uint8List.fromList([1]),
          uploadKey: 'key',
        ),
        _ => api.uploadGradePdf('synthetic', Uint8List.fromList([1]), 'key'),
      };
      final result = expectLater(
        request,
        throwsA(
          isA<ApiError>().having(
            (e) => e.code,
            'code',
            'authentication_changed',
          ),
        ),
      );
      await entered.future;
      state.beginAuthentication();
      delayed.complete(http.Response('{"detail":"old session"}', 401));
      await result;
      expect(unauthorized, 0);
      state.dispose();
    });
    test(
      'late $transport transport error is reported as changed authentication',
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
          ..user = {'id': 'old', 'role': 'parent'};
        final Future<dynamic> request = switch (transport) {
          'bytes' => api.bytes('/materials/synthetic/image'),
          'photo' => api.upload(
            'synthetic',
            Uint8List.fromList([1]),
            uploadKey: 'key',
          ),
          _ => api.uploadGradePdf('synthetic', Uint8List.fromList([1]), 'key'),
        };
        final result = expectLater(
          request,
          throwsA(
            isA<ApiError>()
                .having((e) => e.code, 'code', 'authentication_changed')
                .having((e) => e.status, 'uncertain status', 0),
          ),
        );
        await entered.future;
        state.beginAuthentication();
        delayed.completeError(StateError('synthetic disconnected transport'));
        await result;
        state.dispose();
      },
    );
  }
  for (final transport in ['bytes', 'photo', 'pdf']) {
    test('a current $transport response is returned', () async {
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (_) async => transport == 'bytes'
              ? http.Response.bytes([7, 8], 200)
              : http.Response('{"id":"synthetic"}', 200),
        ),
      );
      final state = AppState(api: api)
        ..user = {'id': 'synthetic', 'role': 'parent'};
      final Object result = await switch (transport) {
        'bytes' => api.bytes('/materials/synthetic/image'),
        'photo' => api.upload(
          'synthetic',
          Uint8List.fromList([1]),
          uploadKey: 'key',
        ),
        _ => api.uploadGradePdf('synthetic', Uint8List.fromList([1]), 'key'),
      };
      if (transport == 'bytes') {
        expect(result, [7, 8]);
      } else {
        expect(result, {'id': 'synthetic'});
      }
      state.dispose();
    });
    test(
      'a $transport response is discarded if login changes during streaming',
      () async {
        final client = ChunkedFileClient();
        final api = Api(base: 'https://example.invalid/api', client: client);
        final state = AppState(api: api)
          ..user = {'id': 'old', 'role': 'parent'};
        final Future<dynamic> request = switch (transport) {
          'bytes' => api.bytes('/materials/synthetic/image'),
          'photo' => api.upload(
            'synthetic',
            Uint8List.fromList([1]),
            uploadKey: 'key',
          ),
          _ => api.uploadGradePdf('synthetic', Uint8List.fromList([1]), 'key'),
        };
        final expected = expectLater(
          request,
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
        client.body.add(
          transport == 'bytes' ? [7, 8] : '{"id":"synthetic"}'.codeUnits,
        );
        await client.body.close();
        await expected;
        state.dispose();
      },
    );
  }
}
