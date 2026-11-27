import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

void main() {
  testWidgets('an accepted job is never polled by a later login', (
    tester,
  ) async {
    final sent = <http.Request>[];
    final queued = Completer<void>();
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        sent.add(request);
        queued.complete();
        return http.Response('{"id":"synthetic-job"}', 200);
      }),
    );
    final state = AppState(api: api)..user = {'id': 'old', 'role': 'parent'};
    addTearDown(state.dispose);
    final pending = api.job('/materials/synthetic/extract');
    final expected = expectLater(
      pending,
      throwsA(
        isA<ApiError>()
            .having((e) => e.code, 'code', 'authentication_changed')
            .having((e) => e.status, 'uncertain status', 0),
      ),
    );
    await queued.future;
    await tester.pump();
    state.beginAuthentication();
    await tester.pump(const Duration(seconds: 2));
    await expected;
    expect(sent, hasLength(1));
    expect(sent.single.method, 'POST');
  });
  testWidgets('a current job still loads its completed result', (tester) async {
    final sent = <http.Request>[];
    final queued = Completer<void>();
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((request) async {
        sent.add(request);
        if (request.method == 'POST') {
          queued.complete();
          return http.Response('{"id":"synthetic-job"}', 200);
        }
        return http.Response(
          '{"status":"completed","result":{"ok":true}}',
          200,
        );
      }),
    );
    final state = AppState(api: api)..user = {'id': 'old', 'role': 'parent'};
    addTearDown(state.dispose);
    final future = api.job('/materials/synthetic/extract');
    await queued.future;
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    expect(await future, {'ok': true});
    expect(sent.map((r) => r.method).toList(), ['POST', 'GET']);
  });
}
