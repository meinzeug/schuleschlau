import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/public_image_card.dart';
import 'package:schulpilot/ui.dart';

http.Response jsonReply(Object value, [int status = 200]) => http.Response(
  jsonEncode(value),
  status,
  headers: {'content-type': 'application/json'},
);

void main() {
  testWidgets('pending image status resumes after another route closes', (
    tester,
  ) async {
    var reads = 0;
    final navigator = GlobalKey<NavigatorState>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          reads++;
          return jsonReply({'status': 'queued'});
        }),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        navigatorKey: navigator,
        theme: appTheme(),
        home: Scaffold(
          body: Builder(
            builder: (context) => Column(
              children: [
                PublicImageCard(
                  state: state,
                  unit: {
                    'id': 'unit',
                    'explanation_visual_status': 'incomplete',
                  },
                  isCurrent: () => true,
                ),
                TextButton(
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) =>
                          const Scaffold(body: Text('Weitere Seite')),
                    ),
                  ),
                  child: const Text('Öffnen'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(reads, 1);
    await tester.tap(find.text('Öffnen'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 6));
    expect(reads, 1);
    navigator.currentState!.pop();
    await tester.pumpAndSettle();
    expect(reads, 2);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('an exhausted image attempt does not offer a futile retry', (
    tester,
  ) async {
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (request) async =>
              jsonReply({'status': 'failed', 'retry_allowed': false}),
        ),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: PublicImageCard(
            state: state,
            unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
            isCurrent: () => true,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.text('Bild erneut versuchen'), findsNothing);
    expect(
      find.text('Das Bild ist gerade nicht verfügbar. Du kannst weiterlernen.'),
      findsOneWidget,
    );
  });

  testWidgets('a late response from another account is discarded', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) => pending.future),
      ),
    )..user = {'id': 'first', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: PublicImageCard(
            state: state,
            unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
            isCurrent: () => true,
          ),
        ),
      ),
    );
    await tester.pump();
    state.user = {'id': 'second', 'role': 'child', 'families': <Json>[]};
    pending.complete(jsonReply({'status': 'missing'}));
    await tester.pump();
    expect(find.text('Bild zum Thema erstellen'), findsNothing);
  });

  testWidgets(
    'read never generates; explicit request sends one idempotent POST',
    (tester) async {
      final requests = <http.Request>[];
      var status = 'missing';
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            if (request.method == 'POST') {
              status = 'queued';
              return jsonReply({'status': status}, 202);
            }
            return jsonReply({'status': status});
          }),
        ),
      )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: PublicImageCard(
              state: state,
              unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
              isCurrent: () => true,
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump();
      expect(requests.map((e) => e.method), ['GET']);
      await tester.tap(find.text('Bild zum Thema erstellen'));
      await tester.pump();
      await tester.pump();
      final posted = requests.where((e) => e.method == 'POST').toList();
      expect(posted.length, 1);
      expect(posted.single.url.path, '/api/units/unit/public-image');
      expect(posted.single.headers['Idempotency-Key'], isNotEmpty);
      expect(find.text('Dein Themenbild entsteht …'), findsOneWidget);
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );

  testWidgets('ready image is read and labelled as unverified', (tester) async {
    final requests = <http.Request>[];
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          return jsonReply({'status': 'ready'});
        }),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: PublicImageCard(
            state: state,
            unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
            isCurrent: () => true,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(find.text('KI-Bild · fachlich noch nicht geprüft'), findsOneWidget);
    expect(requests.every((request) => request.method == 'GET'), isTrue);
    expect(requests.last.url.path, '/api/units/unit/public-image/file');
  });

  testWidgets(
    'a failed file download offers a read retry, never regeneration',
    (tester) async {
      final requests = <http.Request>[];
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            if (request.url.path.endsWith('/file')) {
              return jsonReply({'detail': 'temporarily unavailable'}, 503);
            }
            return jsonReply({'status': 'ready'});
          }),
        ),
      )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: PublicImageCard(
              state: state,
              unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
              isCurrent: () => true,
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump();
      expect(find.text('Bild erneut laden'), findsOneWidget);
      await tester.tap(find.text('Bild erneut laden'));
      await tester.pump();
      await tester.pump();
      expect(requests.every((r) => r.method == 'GET'), isTrue);
    },
  );
}
