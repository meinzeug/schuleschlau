import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_inbox.dart';

http.Response page(List<Map<String, Object>> items, [String? cursor]) =>
    http.Response(
      jsonEncode({'items': items, 'next_cursor': cursor}),
      200,
      headers: {'content-type': 'application/json'},
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  for (final status in [401, 403]) {
    test(
      'loadMore HTTP $status clears private cache without waiting for UI',
      () async {
        var gateCalls = 0;
        final inbox = NotificationInbox(
          Api(
            base: 'https://example.invalid/api',
            client: MockClient((r) async {
              if (r.url.queryParameters['cursor'] == null) {
                return page([
                  {'id': 'private', 'read': true},
                ], 'next');
              }
              return http.Response(
                '{}',
                status,
                headers: {'content-type': 'application/json'},
              );
            }),
          ),
        );
        inbox.activate('child', family: 'family', session: 'session');
        await Future<void>.delayed(Duration.zero);
        await inbox.loadMore(
          beforePublish: () {
            gateCalls++;
            return Completer<NoticePublishGate>().future;
          },
        );
        expect(inbox.items, isEmpty);
        expect(inbox.error, isNotNull);
        expect(inbox.loadingMore, isFalse);
        expect(gateCalls, 0);
        inbox.dispose();
      },
    );
  }

  test(
    'UI gate exceptions are not mistaken for HTTP authorization errors',
    () async {
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (r) async => r.url.queryParameters['cursor'] == null
                ? page([
                    {'id': 'head', 'read': true},
                  ], 'next')
                : page([
                    {'id': 'old', 'read': true},
                  ]),
          ),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      await inbox.loadMore(
        beforePublish: () async => throw ApiError('synthetic', 403),
      );
      expect(inbox.items.map((x) => x['id']), ['head']);
      expect(inbox.error, isNull);
      expect(inbox.loadingMore, isFalse);
      inbox.dispose();
    },
  );

  test('a delayed refresh revalidates the full bounded history', () async {
    final gate = Completer<NoticePublishGate>();
    var head = 0, older = 0, gateCalls = 0;
    final inbox = NotificationInbox(
      Api(
        base: 'https://example.invalid/api',
        client: MockClient((r) async {
          if (r.url.queryParameters['cursor'] == null) {
            head++;
            return page([
              {'id': 'head-$head', 'read': true},
            ], 'next');
          }
          older++;
          return page([
            {'id': 'history-$older', 'read': true},
          ]);
        }),
      ),
    );
    inbox.activate('child', family: 'family', session: 'session');
    await Future<void>.delayed(Duration.zero);
    await inbox.loadMore();
    final owner = Object();
    inbox.registerRefreshGate(
      owner,
      () => ++gateCalls == 1
          ? gate.future
          : Future.value(NoticePublishGate.ready),
    );
    final request = inbox.refresh();
    await Future<void>.delayed(Duration.zero);
    expect(inbox.items.map((x) => x['id']), ['head-1', 'history-1']);
    gate.complete(NoticePublishGate.delayed);
    await request;
    expect(head, 3);
    expect(older, 3);
    expect(inbox.items.map((x) => x['id']), ['head-3', 'history-3']);
    expect(inbox.loading, isFalse);
    inbox.unregisterRefreshGate(owner);
    inbox.dispose();
  });

  for (final status in [401, 403]) {
    for (final failure in ['head', 'history', 'retry']) {
      test(
        'HTTP $status authorization failure on $failure clears immediately without waiting for a gate',
        () async {
          final gate = Completer<NoticePublishGate>();
          var fail = false, gateCalls = 0, heads = 0;
          final inbox = NotificationInbox(
            Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                final isHead = r.url.queryParameters['cursor'] == null;
                if (isHead) heads++;
                if (fail &&
                    (failure == 'head' && isHead ||
                        failure == 'history' && !isHead ||
                        failure == 'retry' && isHead && heads >= 3)) {
                  return http.Response(
                    '{}',
                    status,
                    headers: {'content-type': 'application/json'},
                  );
                }
                return isHead
                    ? page([
                        {'id': 'head', 'read': true},
                      ], 'next')
                    : page([
                        {'id': 'older', 'read': true},
                      ]);
              }),
            ),
          );
          inbox.activate('child', family: 'family', session: 'session');
          await Future<void>.delayed(Duration.zero);
          await inbox.loadMore();
          final owner = Object();
          inbox.registerRefreshGate(owner, () {
            gateCalls++;
            return gate.future;
          });
          fail = true;
          final request = inbox.refresh();
          if (failure == 'retry') {
            await Future<void>.delayed(Duration.zero);
            expect(inbox.items, isNotEmpty);
            gate.complete(NoticePublishGate.delayed);
          }
          await request;
          expect(inbox.items, isEmpty);
          expect(inbox.error, isNotNull);
          expect(inbox.loading, isFalse);
          expect(gateCalls, failure == 'retry' ? 1 : 0);
          inbox.unregisterRefreshGate(owner);
          inbox.dispose();
        },
      );
    }
  }

  for (final change in [
    'account',
    'family',
    'session',
    'unregister',
    'background',
    'dispose',
  ]) {
    test('refresh waiting at gate cannot publish after $change', () async {
      final gate = Completer<NoticePublishGate>();
      var head = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((_) async {
            head++;
            return page([
              {
                'id': head == 1
                    ? 'old'
                    : head == 2
                    ? 'must-not-publish'
                    : 'new-account',
                'read': true,
              },
            ]);
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      final owner = Object();
      inbox.registerRefreshGate(owner, () => gate.future);
      final request = inbox.refresh();
      await Future<void>.delayed(Duration.zero);
      switch (change) {
        case 'account':
          inbox.activate('other', family: 'family', session: 'session');
        case 'family':
          inbox.activate('child', family: 'other', session: 'session');
        case 'session':
          inbox.activate('child', family: 'family', session: 'other');
        case 'unregister':
          inbox.unregisterRefreshGate(owner);
        case 'background':
          inbox.foreground(false);
        case 'dispose':
          inbox.dispose();
      }
      gate.complete(NoticePublishGate.ready);
      await request;
      if (['account', 'family', 'session'].contains(change)) {
        // New context starts its own GET; wait for its independent completion.
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);
        expect(inbox.items.map((x) => x['id']), ['new-account']);
      }
      expect(
        inbox.items.map((x) => x['id']),
        isNot(contains('must-not-publish')),
      );
      expect(inbox.loading, isFalse);
      if (change != 'dispose') inbox.dispose();
    });
  }

  test(
    'receipt during gate waiting causes fresh read and remains read',
    () async {
      final gate = Completer<NoticePublishGate>();
      var heads = 0, calls = 0;
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
            heads++;
            return page([
              {'id': 'head', 'read': heads > 2},
            ]);
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await Future<void>.delayed(Duration.zero);
      final owner = Object();
      inbox.registerRefreshGate(
        owner,
        () =>
            ++calls == 1 ? gate.future : Future.value(NoticePublishGate.ready),
      );
      final request = inbox.refresh();
      await Future<void>.delayed(Duration.zero);
      await inbox.markRead(['head']);
      gate.complete(NoticePublishGate.delayed);
      await request;
      expect(heads, 3);
      expect(inbox.items.single['read'], isTrue);
      expect(inbox.unread, 0);
      inbox.unregisterRefreshGate(owner);
      inbox.dispose();
    },
  );

  for (final stage in [
    'refresh-http',
    'refresh-gate',
    'more-http',
    'more-gate',
  ]) {
    test(
      'foreground epoch discards old response at $stage before fresh resume GET',
      () async {
        final old = Completer<http.Response>();
        final fresh = Completer<http.Response>();
        final gate = Completer<NoticePublishGate>();
        var heads = 0;
        final inbox = NotificationInbox(
          Api(
            base: 'https://example.invalid/api',
            client: MockClient((r) async {
              if (r.url.queryParameters['cursor'] != null) {
                return stage == 'more-http'
                    ? old.future
                    : page([
                        {'id': 'stale', 'read': true},
                      ]);
              }
              heads++;
              if (heads == 1) {
                return page([
                  {'id': 'original', 'read': true},
                ], 'next');
              }
              if (stage == 'refresh-http' && heads == 2) return old.future;
              if (stage == 'refresh-gate' && heads == 2) {
                return page([
                  {'id': 'stale', 'read': true},
                ], 'next');
              }
              return fresh.future;
            }),
          ),
        );
        inbox.activate('child', family: 'family', session: 'session');
        await Future<void>.delayed(Duration.zero);
        final owner = Object();
        if (stage == 'refresh-gate') {
          inbox.registerRefreshGate(owner, () => gate.future);
        }
        final request = stage.startsWith('refresh')
            ? inbox.refresh()
            : inbox.loadMore(
                beforePublish: stage == 'more-gate' ? () => gate.future : null,
              );
        await Future<void>.delayed(Duration.zero);
        inbox.foreground(false);
        inbox.foreground(true);
        if (stage.endsWith('http')) {
          old.complete(
            page([
              {'id': 'stale', 'read': true},
            ]),
          );
        }
        if (stage.endsWith('gate')) gate.complete(NoticePublishGate.ready);
        await request;
        await Future<void>.delayed(Duration.zero);
        expect(inbox.items.map((x) => x['id']), ['original']);
        expect(heads, stage.startsWith('refresh') ? 3 : 2);
        fresh.complete(
          page([
            {'id': 'fresh', 'read': true},
          ]),
        );
        await Future<void>.delayed(Duration.zero);
        await Future<void>.delayed(Duration.zero);
        expect(inbox.items.map((x) => x['id']), ['fresh']);
        inbox.unregisterRefreshGate(owner);
        inbox.dispose();
      },
    );
  }

  for (final kind in ['refresh', 'more']) {
    for (final status in [403, 429]) {
      test(
        '$kind HTTP $status after background and resume preserves authorization policy',
        () async {
          final delayed = Completer<http.Response>();
          final fresh = Completer<http.Response>();
          var heads = 0;
          final inbox = NotificationInbox(
            Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                if (r.url.queryParameters['cursor'] != null) {
                  return delayed.future;
                }
                heads++;
                if (heads == 1) {
                  return page([
                    {'id': 'original', 'read': true},
                  ], 'next');
                }
                if (kind == 'refresh' && heads == 2) return delayed.future;
                return fresh.future;
              }),
            ),
          );
          inbox.activate('child', family: 'family', session: 'session');
          await Future<void>.delayed(Duration.zero);
          final request = kind == 'refresh'
              ? inbox.refresh()
              : inbox.loadMore();
          await Future<void>.delayed(Duration.zero);
          inbox.foreground(false);
          inbox.foreground(true);
          delayed.complete(
            http.Response(
              '{}',
              status,
              headers: {'content-type': 'application/json'},
            ),
          );
          await request;
          await Future<void>.delayed(Duration.zero);
          if (status == 403) {
            expect(inbox.items, isEmpty);
            expect(inbox.error, isNotNull);
            expect(heads, kind == 'refresh' ? 3 : 2);
            fresh.complete(
              page([
                {'id': 'fresh', 'read': true},
              ]),
            );
            await Future<void>.delayed(Duration.zero);
            await Future<void>.delayed(Duration.zero);
          } else {
            expect(inbox.items.map((x) => x['id']), ['original']);
            expect(inbox.moreError, isNull);
            expect(heads, kind == 'refresh' ? 2 : 1);
          }
          inbox.dispose();
        },
      );
    }
  }
  for (final status in [401, 403]) {
    for (final kind in ['refresh', 'more']) {
      test(
        'old account $kind $status cannot clear newly loaded account',
        () async {
          final delayed = Completer<http.Response>();
          var heads = 0;
          final inbox = NotificationInbox(
            Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                if (r.url.queryParameters['cursor'] != null) {
                  return delayed.future;
                }
                heads++;
                if (heads == 1) {
                  return page([
                    {'id': 'old-account', 'read': true},
                  ], 'next');
                }
                if (kind == 'refresh' && heads == 2) return delayed.future;
                return page([
                  {'id': 'new-account', 'read': true},
                ]);
              }),
            ),
          );
          inbox.activate('old', family: 'old', session: 'old');
          await Future<void>.delayed(Duration.zero);
          final request = kind == 'refresh'
              ? inbox.refresh()
              : inbox.loadMore();
          await Future<void>.delayed(Duration.zero);
          inbox.activate('new', family: 'new', session: 'new');
          await Future<void>.delayed(Duration.zero);
          expect(inbox.items.map((x) => x['id']), ['new-account']);
          delayed.complete(
            http.Response(
              '{}',
              status,
              headers: {'content-type': 'application/json'},
            ),
          );
          await request;
          expect(inbox.items.map((x) => x['id']), ['new-account']);
          expect(inbox.error, isNull);
          inbox.dispose();
        },
      );
    }
  }

  test(
    'gate registered after activation gates its in-flight first GET',
    () async {
      final response = Completer<http.Response>();
      final gate = Completer<NoticePublishGate>();
      var gateCalls = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((_) => response.future),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      inbox.registerRefreshGate(Object(), () {
        gateCalls++;
        return gate.future;
      });
      response.complete(
        page([
          {'id': 'new', 'read': true},
        ]),
      );
      await Future<void>.delayed(Duration.zero);
      expect(gateCalls, 1);
      expect(inbox.items, isEmpty);
      gate.complete(NoticePublishGate.ready);
      await Future<void>.delayed(Duration.zero);
      expect(inbox.items.map((x) => x['id']), ['new']);
      inbox.dispose();
    },
  );
  testWidgets(
    'timed out gate preserves snapshot and a later refresh recovers',
    (tester) async {
      var heads = 0;
      final inbox = NotificationInbox(
        Api(
          base: 'https://example.invalid/api',
          client: MockClient((_) async {
            heads++;
            return page([
              {'id': heads == 1 ? 'old' : 'fresh', 'read': true},
            ]);
          }),
        ),
      );
      inbox.activate('child', family: 'family', session: 'session');
      await tester.pump();
      await tester.pump();
      expect(inbox.items.map((x) => x['id']), ['old']);
      final owner = Object();
      inbox.registerRefreshGate(
        owner,
        () => Completer<NoticePublishGate>().future,
      );
      final request = inbox.refresh();
      await tester.pump();
      await tester.pump(const Duration(seconds: 4));
      await request;
      expect(inbox.loading, isFalse);
      expect(inbox.items.map((x) => x['id']), ['old']);
      expect(heads, 2);
      inbox.unregisterRefreshGate(owner);
      final retry = inbox.refresh();
      await tester.pump();
      await retry;
      expect(inbox.items.map((x) => x['id']), ['fresh']);
      expect(heads, 3);
      inbox.dispose();
    },
  );
}
