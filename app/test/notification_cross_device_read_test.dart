import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_panel.dart';
import 'package:schulpilot/push_transport.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets(
    'visible reads survive a device change and do not read unseen rows',
    (tester) async {
      tester.view.physicalSize = const Size(390, 760);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      FlutterSecureStorage.setMockInitialValues({});
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(
            PushTransport.channel,
            (_) async => <String, dynamic>{},
          );
      addTearDown(
        () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
            .setMockMethodCallHandler(PushTransport.channel, null),
      );

      final reads = <String>{};
      final writes = <String>[];
      final client = MockClient((request) async {
        final account = request.headers['Authorization'];
        if (request.url.path.endsWith('/inbox/read')) {
          expect(account, anyOf('Bearer device-one', 'Bearer device-two'));
          final ids = (jsonDecode(request.body)['ids'] as List).cast<String>();
          writes.addAll(ids);
          reads.addAll(ids);
          return http.Response('{}', 200);
        }
        if (request.url.path.endsWith('/inbox')) {
          return http.Response(
            jsonEncode({
              'items': [
                for (var i = 0; i < 20; i++)
                  {
                    'id': 'message:$i',
                    'title': 'Synthetischer Hinweis $i',
                    'read': reads.contains('message:$i'),
                    'kind': 'help',
                    'child_name': 'Beispielkind',
                    'created': 1792638000 - i,
                    'route': '/target/$i',
                  },
              ],
              'unread': 20 - reads.length,
              'next_cursor': null,
            }),
            200,
          );
        }
        return http.Response(
          jsonEncode(
            request.url.path.endsWith('/devices') ? [] : {'available': false},
          ),
          200,
        );
      });
      AppState device(String token) =>
          AppState(
              api: Api(base: 'https://example.invalid/api', client: client)
                ..token = token,
            )
            ..user = {
              'id': 'same-account',
              'role': 'parent',
              'display_name': 'Testfamilie',
            }
            ..familyId = 'same-family';
      final first = device('device-one'), second = device('device-two');
      final router = GoRouter(
        initialLocation: '/first',
        routes: [
          GoRoute(
            path: '/first',
            builder: (_, _) => NotificationsScreen(first),
          ),
          GoRoute(
            path: '/second',
            builder: (_, _) => NotificationsScreen(second),
          ),
          GoRoute(path: '/target/:id', builder: (_, _) => const Scaffold()),
        ],
      );
      try {
        await tester.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: router),
        );
        await tester.pumpAndSettle();
        expect(reads, isNotEmpty);
        expect(reads, isNot(contains('message:19')));
        final beforeScroll = Set<String>.from(reads);
        await tester.scrollUntilVisible(
          find.text('Synthetischer Hinweis 14'),
          400,
          scrollable: find.byType(Scrollable).first,
        );
        await tester.pumpAndSettle();
        expect(reads, contains('message:14'));
        expect(reads, isNot(contains('message:19')));
        expect(reads.length, greaterThan(beforeScroll.length));

        second.inbox.activate(
          'same-account',
          family: 'same-family',
          session: 'device-two',
        );
        await tester.pumpAndSettle();
        final secondStates = {
          for (final item in second.inbox.items) item['id']: item['read'],
        };
        expect(secondStates['message:14'], isTrue);
        expect(secondStates['message:19'], isFalse);
        router.go('/second');
        await tester.pumpAndSettle();
        expect(reads, isNot(contains('message:19')));
        expect(writes, isNot(contains('message:19')));
        expect(tester.takeException(), isNull);
      } finally {
        await tester.pumpWidget(const SizedBox());
        first.inbox.dispose();
        second.inbox.dispose();
        router.dispose();
      }
    },
  );
}
