import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_inbox.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'two resumed devices receive own new notice and a sibling stays isolated',
    () async {
      var released = false;
      final methods = <String>[];
      final client = MockClient((request) async {
        methods.add(request.method);
        final own =
            request.headers['Authorization'] != 'Bearer sibling-session';
        final entries = own && released
            ? [
                {'id': 'own-ready', 'read': false},
              ]
            : <Map<String, Object>>[];
        return http.Response(
          jsonEncode({'items': entries, 'next_cursor': null}),
          200,
        );
      });
      NotificationInbox device(String token, String account) {
        final inbox = NotificationInbox(
          Api(base: 'https://example.invalid/api', client: client)
            ..token = token,
        );
        inbox.activate(account, family: 'family', session: token);
        return inbox;
      }

      final first = device('child-session-one', 'child');
      final second = device('child-session-two', 'child');
      final sibling = device('sibling-session', 'sibling');
      addTearDown(first.dispose);
      addTearDown(second.dispose);
      addTearDown(sibling.dispose);
      await Future<void>.delayed(Duration.zero);
      first.foreground(false);
      second.foreground(false);
      sibling.foreground(false);
      released = true;
      first.foreground(true);
      await Future<void>.delayed(Duration.zero);
      expect(first.items.single['id'], 'own-ready');
      expect(second.items, isEmpty);
      expect(sibling.items, isEmpty);
      second.foreground(true);
      sibling.foreground(true);
      await Future<void>.delayed(Duration.zero);
      expect(second.items.single['id'], 'own-ready');
      expect(sibling.items, isEmpty);
      expect(methods.every((method) => method == 'GET'), isTrue);
    },
  );
}
