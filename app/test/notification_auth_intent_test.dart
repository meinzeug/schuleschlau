import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_inbox.dart';

http.Response page(String id, {String? next}) => http.Response(
  jsonEncode({
    'items': [
      {'id': id, 'read': false},
    ],
    'next_cursor': next,
  }),
  200,
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('a head response is discarded when another login begins', () async {
    final pending = Completer<http.Response>();
    var intent = 0;
    final api = Api(
      base: 'https://example.invalid/api',
      client: MockClient((_) => pending.future),
    )..currentAuthenticationRevision = () => intent;
    final inbox = NotificationInbox(api);
    inbox.activate('first', family: 'family');
    await Future<void>.delayed(Duration.zero);
    intent++;
    pending.complete(page('old'));
    await Future<void>.delayed(Duration.zero);
    expect(inbox.items, isEmpty);
    expect(inbox.hasLoaded, isFalse);
    expect(inbox.loading, isFalse);
    inbox.dispose();
  });

  test(
    'a stale denied response cannot erase the earlier account snapshot',
    () async {
      final pending = Completer<http.Response>();
      var intent = 0, reads = 0;
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          reads++;
          return reads == 1 ? page('known') : pending.future;
        }),
      )..currentAuthenticationRevision = () => intent;
      final inbox = NotificationInbox(api);
      inbox.activate('first', family: 'family');
      await Future<void>.delayed(Duration.zero);
      final refresh = inbox.refresh();
      await Future<void>.delayed(Duration.zero);
      intent++;
      pending.complete(http.Response(jsonEncode({'detail': 'denied'}), 403));
      await refresh;
      expect(inbox.items.single['id'], 'known');
      expect(inbox.error, isNull);
      inbox.dispose();
    },
  );

  test(
    'a history page behind a publication gate cannot cross login intent',
    () async {
      final gate = Completer<NoticePublishGate>();
      var intent = 0;
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (request) async => request.url.queryParameters['cursor'] == null
              ? page('head', next: 'next')
              : page('older'),
        ),
      )..currentAuthenticationRevision = () => intent;
      final inbox = NotificationInbox(api);
      inbox.activate('first', family: 'family');
      await Future<void>.delayed(Duration.zero);
      final load = inbox.loadMore(beforePublish: () => gate.future);
      await Future<void>.delayed(Duration.zero);
      intent++;
      gate.complete(NoticePublishGate.ready);
      await load;
      expect(inbox.items.map((item) => item['id']), ['head']);
      expect(inbox.loadingMore, isFalse);
      inbox.dispose();
    },
  );

  test(
    'a delayed receipt cannot update a snapshot after a new login begins',
    () async {
      final pending = Completer<http.Response>();
      var intent = 0;
      final api = Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (request) async =>
              request.method == 'POST' ? pending.future : page('unread'),
        ),
      )..currentAuthenticationRevision = () => intent;
      final inbox = NotificationInbox(api);
      inbox.activate('first', family: 'family');
      await Future<void>.delayed(Duration.zero);
      final read = inbox.markRead(['unread']);
      await Future<void>.delayed(Duration.zero);
      intent++;
      pending.complete(http.Response('{}', 200));
      await read;
      expect(inbox.items.single['read'], isFalse);
      expect(inbox.unread, 1);
      inbox.dispose();
    },
  );
}
