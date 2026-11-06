import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_inbox.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  http.Response response(List<Map<String, Object>> items, [String? cursor]) =>
      http.Response(
        jsonEncode({
          'items': items,
          'unread': items.length,
          'next_cursor': cursor,
        }),
        200,
      );

  test('delayed page is refetched before publishing', () async {
    final gate = Completer<NoticePublishGate>();
    var pages = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.url.queryParameters['cursor'] == null) {
            return response([
              {'id': 'head', 'read': true},
            ], 'next');
          }
          pages++;
          return response([
            {'id': pages == 1 ? 'stale' : 'fresh', 'read': true},
          ]);
        }),
      ),
    );
    inbox.activate('child', family: 'family', session: 'session');
    await Future<void>.delayed(Duration.zero);
    var gates = 0;
    final request = inbox.loadMore(
      beforePublish: () {
        gates++;
        return gates == 1 ? gate.future : Future.value(NoticePublishGate.ready);
      },
    );
    await Future<void>.delayed(Duration.zero);
    expect(inbox.loadingMore, isTrue);
    expect(inbox.items.map((item) => item['id']), ['head']);
    gate.complete(NoticePublishGate.delayed);
    await request;
    expect(pages, 2);
    expect(inbox.items.map((item) => item['id']), ['head', 'fresh']);
    expect(inbox.loadingMore, isFalse);
    inbox.dispose();
  });

  test(
    'two gestures defer without a false error and allow another load',
    () async {
      var pages = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (r.url.queryParameters['cursor'] == null) {
              return response([
                {'id': 'head', 'read': true},
              ], 'next');
            }
            pages++;
            return response([
              {'id': pages < 3 ? 'stale-$pages' : 'fresh', 'read': true},
            ]);
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      await inbox.loadMore(
        beforePublish: () async => NoticePublishGate.delayed,
      );
      expect(pages, 2);
      expect(inbox.items.map((item) => item['id']), ['head']);
      expect(inbox.nextCursor, 'next');
      expect(inbox.moreError, isNull);
      expect(inbox.loadingMore, isFalse);
      await inbox.loadMore();
      expect(pages, 3);
      expect(inbox.items.map((item) => item['id']), ['head', 'fresh']);
      expect(inbox.moreError, isNull);
      inbox.dispose();
    },
  );

  for (final change in ['cancelled', 'account', 'background']) {
    test(
      'blocked page is discarded after $change and does not retain loading',
      () async {
        final gate = Completer<NoticePublishGate>();
        final inbox = NotificationInbox(
          Api(
            base: 'https://example.invalid/api',
            client: MockClient(
              (r) async => r.url.queryParameters['cursor'] == null
                  ? response([
                      {'id': 'head', 'read': true},
                    ], 'next')
                  : response([
                      {'id': 'old-page', 'read': true},
                    ]),
            ),
          ),
        );
        inbox.activate('child', family: 'family', session: 'session');
        await Future<void>.delayed(Duration.zero);
        final request = inbox.loadMore(beforePublish: () => gate.future);
        await Future<void>.delayed(Duration.zero);
        if (change == 'account') {
          inbox.activate('other', family: 'other', session: 'new');
        }
        if (change == 'background') inbox.foreground(false);
        gate.complete(
          change == 'cancelled'
              ? NoticePublishGate.cancelled
              : NoticePublishGate.ready,
        );
        await request;
        expect(
          inbox.items.map((item) => item['id']),
          isNot(contains('old-page')),
        );
        expect(inbox.loadingMore, isFalse);
        inbox.dispose();
      },
    );
  }

  test('a read while publication waits survives the bounded refetch', () async {
    final gate = Completer<NoticePublishGate>();
    var pageCalls = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.method == 'POST') {
            return http.Response(
              '{}',
              200,
              headers: {'content-type': 'application/json'},
            );
          }
          if (r.url.queryParameters['cursor'] == null) {
            return response([
              {'id': 'head', 'read': false},
            ], 'next');
          }
          pageCalls++;
          return response([
            {'id': 'head', 'read': pageCalls > 1},
            {'id': 'older', 'read': false},
          ]);
        }),
      ),
    );
    inbox.activate('child', family: 'family', session: 'session');
    await Future<void>.delayed(Duration.zero);
    var gates = 0;
    final loading = inbox.loadMore(
      beforePublish: () {
        gates++;
        return gates == 1 ? gate.future : Future.value(NoticePublishGate.ready);
      },
    );
    await Future<void>.delayed(Duration.zero);
    await inbox.markRead(['head']);
    gate.complete(NoticePublishGate.delayed);
    await loading;
    expect(pageCalls, 2);
    expect(
      inbox.items.singleWhere((item) => item['id'] == 'head')['read'],
      isTrue,
    );
    expect(inbox.unread, 1);
    inbox.dispose();
  });

  test('two reads keep receipts and allow a new explicit load', () async {
    var pages = 0;
    var receipts = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.method == 'POST') {
            receipts++;
            return http.Response(
              '{}',
              200,
              headers: {'content-type': 'application/json'},
            );
          }
          if (r.url.queryParameters['cursor'] == null) {
            return response([
              {'id': 'a', 'read': false},
              {'id': 'b', 'read': false},
            ], 'next');
          }
          pages++;
          return response([
            {'id': 'a', 'read': pages < 3 ? false : true},
            {'id': 'b', 'read': pages < 3 ? false : true},
            {'id': pages < 3 ? 'stale' : 'fresh', 'read': false},
          ]);
        }),
      ),
    );
    inbox.activate('child', family: 'family', session: 'session');
    await Future<void>.delayed(Duration.zero);
    var gates = 0;
    await inbox.loadMore(
      beforePublish: () async {
        await inbox.markRead([++gates == 1 ? 'a' : 'b']);
        return NoticePublishGate.ready;
      },
    );
    expect(pages, 2);
    expect(receipts, 2);
    expect(inbox.items.map((item) => item['id']), ['a', 'b']);
    expect(inbox.items.every((item) => item['read'] == true), isTrue);
    expect(inbox.nextCursor, 'next');
    expect(inbox.moreError, isNull);
    expect(inbox.loadingMore, isFalse);
    await inbox.loadMore();
    expect(pages, 3);
    expect(inbox.items.map((item) => item['id']), ['a', 'b', 'fresh']);
    expect(inbox.items.take(2).every((item) => item['read'] == true), isTrue);
    inbox.dispose();
  });

  test(
    'loads an empty intermediate page and appends later unique notices',
    () async {
      final requests = <Uri>[];
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            requests.add(r.url);
            switch (r.url.queryParameters['cursor']) {
              case null:
                return response([
                  {'id': 'one', 'read': false},
                ], 'page + 1');
              case 'page + 1':
                return response([], 'page-2');
              default:
                return response([
                  {'id': 'one', 'read': false},
                  {'id': 'two', 'read': false},
                ]);
            }
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      expect(inbox.nextCursor, 'page + 1');
      await inbox.loadMore();
      expect(inbox.nextCursor, 'page-2');
      await inbox.loadMore();
      expect(inbox.items.map((item) => item['id']), ['one', 'two']);
      expect(inbox.unread, 2);
      expect(inbox.nextCursor, isNull);
      expect(
        requests.every((url) => url.queryParameters['paginate'] == '1'),
        isTrue,
      );
      expect(requests[1].queryParameters['cursor'], 'page + 1');
      inbox.dispose();
    },
  );

  for (final duringPage in [false, true]) {
    test(
      'resume refreshes after an in-flight ${duringPage ? 'history page' : 'head'}',
      () async {
        final delayed = Completer<http.Response>();
        var heads = 0;
        final inbox = NotificationInbox(
          Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) async {
              if (request.url.queryParameters['cursor'] != null) {
                return delayed.future;
              }
              heads++;
              if (!duringPage && heads == 1) {
                return delayed.future;
              }
              return response([
                {'id': heads == 1 ? 'before' : 'after', 'read': true},
              ], duringPage && heads == 1 ? 'older' : null);
            }),
          ),
        );
        inbox.activate('child', family: 'family', session: 'session');
        await Future<void>.delayed(Duration.zero);
        Future<void>? pending;
        if (duringPage) pending = inbox.loadMore();
        inbox.foreground(false);
        inbox.foreground(true);
        delayed.complete(
          response([
            {'id': 'stale', 'read': true},
          ]),
        );
        if (pending != null) await pending;
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);
        expect(heads, 2);
        expect(inbox.items.first['id'], 'after');
        inbox.dispose();
      },
    );
  }

  test('resume defers the retry if the app returns to background', () async {
    final delayed = Completer<http.Response>();
    var heads = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          heads++;
          return heads == 1
              ? delayed.future
              : response([
                  {'id': 'fresh'},
                ]);
        }),
      ),
    );
    inbox.activate('child');
    inbox.foreground(false);
    inbox.foreground(true);
    inbox.foreground(false);
    delayed.complete(
      response([
        {'id': 'stale'},
      ]),
    );
    await Future<void>.delayed(Duration.zero);
    expect(heads, 1);
    inbox.foreground(true);
    await Future<void>.delayed(Duration.zero);
    expect(heads, 2);
    expect(inbox.items.single['id'], 'fresh');
    inbox.dispose();
  });

  test('queued resume refresh cannot cross an account change', () async {
    final old = Completer<http.Response>();
    var heads = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          heads++;
          return heads == 1
              ? old.future
              : response([
                  {'id': 'new-account'},
                ]);
        }),
      ),
    );
    inbox.activate('old');
    inbox.foreground(false);
    inbox.foreground(true);
    inbox.activate('new');
    await Future<void>.delayed(Duration.zero);
    old.complete(
      response([
        {'id': 'old-private'},
      ]),
    );
    await Future<void>.delayed(Duration.zero);
    expect(heads, 2);
    expect(inbox.items.single['id'], 'new-account');
    inbox.dispose();
  });

  test('old backend without a cursor remains usable', () async {
    var calls = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          calls++;
          return http.Response(
            jsonEncode({
              'items': [
                {'id': 'legacy'},
              ],
              'unread': 1,
            }),
            200,
          );
        }),
      ),
    );
    inbox.activate('child');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    expect(inbox.items.single['id'], 'legacy');
    expect(inbox.nextCursor, isNull);
    expect(calls, 1);
    inbox.dispose();
  });

  test('a delayed page cannot cross a family or session change', () async {
    final oldPage = Completer<http.Response>();
    var firstRequests = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.url.queryParameters['cursor'] != null) return oldPage.future;
          firstRequests++;
          return response([
            {'id': firstRequests == 1 ? 'old' : 'new'},
          ], 'next');
        }),
      ),
    );
    inbox.activate('child', family: 'old', session: 'old');
    await Future<void>.delayed(Duration.zero);
    final pending = inbox.loadMore();
    inbox.activate('child', family: 'new', session: 'new');
    await Future<void>.delayed(Duration.zero);
    oldPage.complete(
      response([
        {'id': 'private'},
      ]),
    );
    await pending;
    expect(inbox.items.map((item) => item['id']), ['new']);
    expect(inbox.nextCursor, 'next');
    inbox.dispose();
  });

  test('a non advancing cursor is rejected and can be retried', () async {
    var pages = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.url.queryParameters['cursor'] == null) {
            return response([], 'next');
          }
          pages++;
          return pages == 1
              ? response([
                  {'id': 'broken'},
                ], 'next')
              : response([
                  {'id': 'good'},
                ]);
        }),
      ),
    );
    inbox.activate('child');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    expect(inbox.items, isEmpty);
    expect(inbox.moreError, isNotNull);
    await inbox.loadMore();
    expect(inbox.items.single['id'], 'good');
    expect(inbox.moreError, isNull);
    inbox.dispose();
  });

  test(
    'refresh keeps loaded history and merges the latest page once',
    () async {
      var heads = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (r.url.queryParameters['cursor'] != null) {
              return response([
                {'id': 'old', 'read': false},
              ], 'later');
            }
            heads++;
            return heads == 1
                ? response([
                    {'id': 'one', 'read': false},
                  ], 'next')
                : response([
                    {'id': 'new', 'read': false},
                    {'id': 'one', 'read': true},
                  ], 'new-head');
          }),
        ),
      );
      inbox.activate('child');
      await Future<void>.delayed(Duration.zero);
      await inbox.loadMore();
      await inbox.refresh();
      expect(inbox.items.map((item) => item['id']), ['new', 'one', 'old']);
      expect(inbox.items[1]['read'], true);
      expect(inbox.nextCursor, 'later');
      inbox.dispose();
    },
  );

  test(
    'reading an existing item while another page loads keeps the receipt',
    () async {
      final page = Completer<http.Response>();
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (r.method == 'POST') return http.Response('{}', 200);
            if (r.url.queryParameters['cursor'] != null) return page.future;
            return response([
              {'id': 'one', 'read': false},
            ], 'next');
          }),
        ),
      );
      inbox.activate('child');
      await Future<void>.delayed(Duration.zero);
      final pending = inbox.loadMore();
      await inbox.markRead(['one']);
      page.complete(
        response([
          {'id': 'one', 'read': false},
          {'id': 'old', 'read': false},
        ]),
      );
      await pending;
      expect(inbox.items.map((item) => item['id']), ['one', 'old']);
      expect(inbox.items.first['read'], true);
      expect(inbox.unread, 1);
      inbox.dispose();
    },
  );

  test(
    'refresh revalidates history and drops events after access is revoked',
    () async {
      var revoked = false;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            if (revoked) return response([]);
            return r.url.queryParameters['cursor'] == null
                ? response([
                    {'id': 'new', 'read': false},
                  ], 'next')
                : response([
                    {'id': 'private-old', 'read': false},
                  ]);
          }),
        ),
      );
      inbox.activate('parent', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      await inbox.loadMore();
      expect(inbox.items.length, 2);
      revoked = true;
      await inbox.refresh();
      expect(inbox.items, isEmpty);
      expect(inbox.nextCursor, isNull);
      inbox.dispose();
    },
  );
  test(
    'history window stays bounded and refresh revalidates only three pages',
    () async {
      final requests = <String?>[];
      var revoked = false;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            final cursor = request.url.queryParameters['cursor'];
            requests.add(cursor);
            if (revoked && cursor != null) return response([]);
            final number = cursor == null ? 0 : int.parse(cursor.substring(1));
            return response([
              {'id': 'item-$number', 'read': false},
            ], number == 8 ? null : 'p${number + 1}');
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      for (var i = 0; i < 6; i++) {
        await inbox.loadMore();
        expect(inbox.items.length, lessThanOrEqualTo(3));
      }
      expect(inbox.historyTrimmed, isTrue);
      expect(inbox.items.map((item) => item['id']), [
        'item-0',
        'item-5',
        'item-6',
      ]);
      expect(inbox.nextCursor, 'p7');
      requests.clear();
      await inbox.refresh();
      expect(requests, [null, 'p5', 'p6']);
      expect(inbox.items.map((item) => item['id']), [
        'item-0',
        'item-5',
        'item-6',
      ]);
      await inbox.loadMore();
      expect(inbox.items.map((item) => item['id']), [
        'item-0',
        'item-6',
        'item-7',
      ]);
      revoked = true;
      requests.clear();
      await inbox.refresh();
      expect(requests, [null, 'p6']);
      expect(inbox.items.map((item) => item['id']), ['item-0']);
      expect(inbox.nextCursor, isNull);
      await inbox.showLatest();
      expect(inbox.historyTrimmed, isFalse);
      expect(inbox.items.single['id'], 'item-0');
      expect(inbox.nextCursor, 'p1');
      inbox.dispose();
    },
  );

  test(
    'empty validation pages advance the bounded window and retain continuity',
    () async {
      final requests = <String?>[];
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            final cursor = request.url.queryParameters['cursor'];
            requests.add(cursor);
            final number = cursor == null ? 0 : int.parse(cursor.substring(1));
            return response(
              number == 4
                  ? [
                      {'id': 'old'},
                    ]
                  : [],
              number == 4 ? null : 'p${number + 1}',
            );
          }),
        ),
      );
      inbox.activate('child');
      await Future<void>.delayed(Duration.zero);
      for (var i = 0; i < 4; i++) {
        await inbox.loadMore();
      }
      expect(inbox.items.single['id'], 'old');
      expect(inbox.historyTrimmed, isTrue);
      expect(inbox.nextCursor, isNull);
      requests.clear();
      await inbox.refresh();
      expect(requests, [null, 'p3', 'p4']);
      expect(inbox.items.single['id'], 'old');
      inbox.dispose();
    },
  );

  test(
    'a delayed page and receipt cannot survive context change after eviction',
    () async {
      final delayedPage = Completer<http.Response>();
      final delayedReceipt = Completer<http.Response>();
      var switched = false;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            if (request.method == 'POST') return delayedReceipt.future;
            final cursor = request.url.queryParameters['cursor'];
            if (switched) {
              return response([
                {'id': 'fresh', 'read': false},
              ]);
            }
            if (cursor == 'p4') return delayedPage.future;
            final number = cursor == null ? 0 : int.parse(cursor.substring(1));
            return response([
              {'id': 'item-$number', 'read': false},
            ], 'p${number + 1}');
          }),
        ),
      );
      inbox.activate('same', family: 'first', session: 'old');
      await Future<void>.delayed(Duration.zero);
      for (var i = 0; i < 3; i++) {
        await inbox.loadMore();
      }
      expect(inbox.historyTrimmed, isTrue);
      final receipt = inbox.markRead(['item-0']);
      final page = inbox.loadMore();
      switched = true;
      inbox.activate('same', family: 'second', session: 'new');
      await Future<void>.delayed(Duration.zero);
      delayedPage.complete(
        response([
          {'id': 'stale'},
        ]),
      );
      delayedReceipt.complete(http.Response('{}', 200));
      await Future.wait([receipt, page]);
      expect(inbox.historyTrimmed, isFalse);
      expect(inbox.items.single['id'], 'fresh');
      expect(inbox.items.single['read'], false);
      inbox.dispose();
    },
  );
  test('acknowledging a duplicated item survives window eviction', () async {
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'POST') return http.Response('{}', 200);
          final cursor = request.url.queryParameters['cursor'];
          switch (cursor) {
            case null:
              return response([
                {'id': 'head', 'read': true},
              ], 'p1');
            case 'p1':
              return response([
                {'id': 'duplicate', 'read': false},
              ], 'p2');
            case 'p2':
              return response([
                {'id': 'duplicate', 'read': false},
              ], 'p3');
            default:
              return response([
                {'id': 'older', 'read': false},
              ]);
          }
        }),
      ),
    );
    inbox.activate('child');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    await inbox.loadMore();
    await inbox.markRead(['duplicate']);
    expect(
      inbox.items.singleWhere((row) => row['id'] == 'duplicate')['read'],
      true,
    );
    await inbox.loadMore();
    expect(inbox.historyTrimmed, isTrue);
    expect(
      inbox.items.singleWhere((row) => row['id'] == 'duplicate')['read'],
      true,
    );
    expect(inbox.unread, 1);
    inbox.dispose();
  });
  test('two-cursor cycle stops without claiming the history ended', () async {
    var calls = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls++;
          switch (request.url.queryParameters['cursor']) {
            case null:
              return response([], 'A');
            case 'A':
              return response([
                {'id': 'one'},
              ], 'B');
            default:
              return response([
                {'id': 'two'},
              ], 'A');
          }
        }),
      ),
    );
    inbox.activate('child');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    expect(inbox.nextCursor, 'B');
    await inbox.loadMore();
    expect(inbox.items.single['id'], 'one');
    expect(inbox.nextCursor, 'B');
    expect(inbox.moreError, contains('angehalten'));
    await inbox.showLatest();
    expect(inbox.nextCursor, 'A');
    expect(inbox.moreError, isNull);
    expect(calls, 4);
    inbox.dispose();
  });

  test(
    'large distinct cursor stream is explicitly stopped at its bound',
    () async {
      var calls = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            calls++;
            final cursor = request.url.queryParameters['cursor'];
            final index = cursor == null ? 0 : int.parse(cursor.substring(1));
            return response([], 'p${index + 1}');
          }),
        ),
      );
      inbox.activate('child');
      await Future<void>.delayed(Duration.zero);
      for (
        var index = 0;
        index < NotificationInbox.maxHistoryCursors;
        index++
      ) {
        await inbox.loadMore();
      }
      final saved = inbox.nextCursor;
      await inbox.loadMore();
      expect(calls, 1 + NotificationInbox.maxHistoryCursors);
      expect(inbox.nextCursor, saved);
      expect(inbox.nextCursor, isNotNull);
      expect(inbox.moreError, contains('Sehr viele Seiten'));
      expect(inbox.historyTrimmed, isTrue);
      await inbox.refresh();
      expect(inbox.nextCursor, saved);
      expect(inbox.moreError, isNull);
      await inbox.loadMore();
      expect(inbox.nextCursor, 'p2050');
      await inbox.showLatest();
      expect(inbox.nextCursor, 'p1');
      expect(inbox.moreError, isNull);
      inbox.dispose();
    },
  );
  test('a stale duplicate page is retried after a concurrent read', () async {
    final delayed = Completer<http.Response>();
    var pageGets = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'POST') return http.Response('{}', 200);
          final cursor = request.url.queryParameters['cursor'];
          if (cursor == null) {
            return response([
              {'id': 'head', 'read': true},
            ], 'p1');
          }
          if (cursor == 'p1') {
            return response([
              {'id': 'duplicate', 'read': false},
            ], 'p2');
          }
          if (cursor == 'p2') {
            pageGets++;
            if (pageGets == 1) return delayed.future;
            return response([
              {'id': 'duplicate', 'read': true},
            ], 'p3');
          }
          return response([
            {'id': 'older', 'read': false},
          ]);
        }),
      ),
    );
    inbox.activate('child');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    final pending = inbox.loadMore();
    await inbox.markRead(['duplicate']);
    delayed.complete(
      response([
        {'id': 'duplicate', 'read': false},
      ], 'p3'),
    );
    await pending;
    expect(pageGets, 2);
    await inbox.loadMore();
    expect(inbox.historyTrimmed, isTrue);
    expect(
      inbox.items.singleWhere((row) => row['id'] == 'duplicate')['read'],
      true,
    );
    inbox.dispose();
  });
  test(
    'a failed revalidation hides old private rows until a fresh check succeeds',
    () async {
      var fail = false;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            if (fail) return http.Response('{"detail":"Unavailable"}', 503);
            return request.url.queryParameters['cursor'] == null
                ? response([
                    {'id': 'head'},
                  ], 'p1')
                : response([
                    {'id': 'old-private'},
                  ]);
          }),
        ),
      );
      inbox.activate('parent', family: 'family');
      await Future<void>.delayed(Duration.zero);
      await inbox.loadMore();
      expect(inbox.items.length, 2);
      fail = true;
      await inbox.refresh();
      expect(inbox.items, isEmpty);
      expect(inbox.unread, 0);
      expect(inbox.nextCursor, isNull);
      expect(inbox.error, isNotNull);
      fail = false;
      await inbox.refresh();
      expect(inbox.items.single['id'], 'head');
      expect(inbox.error, isNull);
      inbox.dispose();
    },
  );
}
