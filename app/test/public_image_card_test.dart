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
  testWidgets(
    'same-round refresh keeps the pending image review and its retry key',
    (tester) async {
      final pending = Completer<http.Response>();
      final posts = <http.Request>[];
      final png = base64Decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
      );
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            if (request.method == 'POST') {
              posts.add(request);
              return posts.length == 1
                  ? pending.future
                  : jsonReply({'review_status': 'pending'}, 202);
            }
            if (request.url.path.endsWith('/file')) {
              return http.Response.bytes(
                png,
                200,
                headers: {'content-type': 'image/png'},
              );
            }
            return jsonReply({
              'status': 'ready',
              'review_status': 'unavailable',
              'review_request_allowed': true,
            });
          }),
        ),
      )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
      addTearDown(state.dispose);
      Widget screen() => MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: PublicImageCard(
            state: state,
            unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
            isCurrent: () => true,
          ),
        ),
      );
      await tester.pumpWidget(screen());
      await tester.pump();
      await tester.pump();
      await tester.pump();
      await tester.tap(find.text('KI-Bildprüfung starten'));
      await tester.pump();
      await tester.pumpWidget(screen());
      await tester.pump();
      await tester.pump();
      await tester.pump();
      expect(find.text('Wird angefragt …'), findsOneWidget);
      pending.complete(jsonReply({'detail': 'Verbindung unterbrochen'}, 503));
      await tester.pump();
      await tester.pump();
      await tester.tap(find.text('KI-Bildprüfung starten'));
      await tester.pump();
      expect(posts.length, 2);
      expect(
        posts.first.headers['Idempotency-Key'],
        posts.last.headers['Idempotency-Key'],
      );
      await tester.pumpWidget(const SizedBox.shrink());
    },
  );

  testWidgets('late image request cannot unlock a new round', (tester) async {
    final pending = [Completer<http.Response>(), Completer<http.Response>()];
    final posts = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'GET') return jsonReply({'status': 'missing'});
          posts.add(request);
          return pending[posts.length - 1].future;
        }),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    Widget screen(String id) => MaterialApp(
      theme: appTheme(),
      home: Scaffold(
        body: PublicImageCard(
          state: state,
          unit: {'id': id, 'explanation_visual_status': 'incomplete'},
          isCurrent: () => true,
        ),
      ),
    );
    await tester.pumpWidget(screen('first'));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Bild zum Thema erstellen'));
    await tester.pump();
    await tester.pumpWidget(screen('second'));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Bild zum Thema erstellen'));
    await tester.pump();
    expect(posts.length, 2);
    expect(
      posts.first.headers['Idempotency-Key'],
      isNot(posts.last.headers['Idempotency-Key']),
    );
    pending.first.complete(jsonReply({'status': 'queued'}, 202));
    await tester.pump();
    await tester.pump();
    expect(find.text('Wird angefragt …'), findsOneWidget);
    pending.last.complete(jsonReply({'status': 'queued'}, 202));
    await tester.pump();
    await tester.pump();
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('same-round refresh preserves an uncertain image request key', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final posts = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'GET') return jsonReply({'status': 'missing'});
          posts.add(request);
          return posts.length == 1
              ? pending.future
              : jsonReply({'status': 'queued'}, 202);
        }),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    Widget screen() => MaterialApp(
      theme: appTheme(),
      home: Scaffold(
        body: PublicImageCard(
          state: state,
          unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
          isCurrent: () => true,
        ),
      ),
    );
    await tester.pumpWidget(screen());
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Bild zum Thema erstellen'));
    await tester.pump();
    // Rebuilding the same unit while its POST is unresolved must retain its key.
    await tester.pumpWidget(screen());
    await tester.pump();
    pending.complete(jsonReply({'detail': 'Kurz nicht erreichbar.'}, 503));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Bild zum Thema erstellen'));
    await tester.pump();
    expect(posts.length, 2);
    expect(
      posts[1].headers['Idempotency-Key'],
      posts[0].headers['Idempotency-Key'],
    );
    await tester.pumpWidget(const SizedBox.shrink());
  });

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

  for (final width in [320.0, 390.0]) {
    testWidgets('compact image opens and closes without writes at $width px', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final requests = <http.Request>[];
      final png = base64Decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
      );
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            return request.url.path.endsWith('/file')
                ? http.Response.bytes(
                    png,
                    200,
                    headers: {'content-type': 'image/png'},
                  )
                : jsonReply({'status': 'ready'});
          }),
        ),
      )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: MediaQuery(
            data: MediaQueryData(
              size: Size(width, 844),
              textScaler: const TextScaler.linear(2),
            ),
            child: Scaffold(
              body: PublicImageCard(
                state: state,
                unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
                isCurrent: () => true,
                compact: true,
              ),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump();
      expect(find.text('Bild ansehen'), findsOneWidget);
      expect(find.text('KI-Bild · fachlich ungeprüft'), findsOneWidget);
      expect(tester.getSize(find.byType(Image)).height, 44);
      await tester.tap(find.text('Bild ansehen'));
      await tester.pumpAndSettle();
      expect(
        find.text('KI-Bild · fachlich noch nicht geprüft'),
        findsOneWidget,
      );
      expect(tester.getSize(find.byType(Image)).height, 180);
      await tester.tap(find.text('Bild schließen'));
      await tester.pumpAndSettle();
      expect(tester.getSize(find.byType(Image)).height, 44);
      expect(requests.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('pending review updates by reads and labels a KI assessment', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    var checks = 0;
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
          checks++;
          return jsonReply({
            'status': 'ready',
            'review_status': checks == 1 ? 'pending' : 'approved',
            'review_reference_available': true,
            'review_request_allowed': false,
          });
        }),
      ),
    )..user = {'id': 'child', 'role': 'child', 'families': <Json>[]};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: const TextScaler.linear(2)),
          child: child!,
        ),
        home: Scaffold(
          body: PublicImageCard(
            state: state,
            unit: {'id': 'unit', 'explanation_visual_status': 'incomplete'},
            isCurrent: () => true,
            compact: true,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(
      find.text('KI prüft das Bild … · fachlich ungeprüft'),
      findsOneWidget,
    );
    await tester.pump(const Duration(seconds: 5));
    await tester.pump();
    expect(
      find.text('Von KI eingeschätzt · nicht fachlich garantiert'),
      findsOneWidget,
    );
    expect(requests.where((r) => r.url.path.endsWith('/file')).length, 1);
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('an AI assessment without factual references says so', (
    tester,
  ) async {
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          return jsonReply({
            'status': 'ready',
            'review_status': 'approved',
            'review_reference_available': false,
          });
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
    expect(
      find.text('Von KI eingeschätzt · ohne Sachquelle, Fehler möglich'),
      findsOneWidget,
    );
    expect(
      find.text('Von KI eingeschätzt · nicht fachlich garantiert'),
      findsNothing,
    );
  });

  testWidgets('a rejected image is hidden rather than shown as verified', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          // Fail closed even if a server response is internally contradictory.
          return jsonReply({'status': 'ready', 'review_status': 'rejected'});
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
    expect(
      find.text(
        'Das Bild hat die KI-Prüfung nicht bestanden. Du kannst weiterlernen.',
      ),
      findsOneWidget,
    );
    expect(find.byType(Image), findsNothing);
    expect(requests.single.method, 'GET');
  });

  testWidgets('a later rejection removes already displayed image bytes', (
    tester,
  ) async {
    var checks = 0;
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          checks++;
          return jsonReply(
            checks == 1
                ? {'status': 'ready', 'review_status': 'pending'}
                : {'status': 'unavailable', 'review_status': 'rejected'},
          );
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
    expect(find.byType(Image), findsOneWidget);
    await tester.pump(const Duration(seconds: 5));
    await tester.pump();
    expect(find.byType(Image), findsNothing);
    expect(
      find.text(
        'Das Bild hat die KI-Prüfung nicht bestanden. Du kannst weiterlernen.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('a permitted review requires one explicit action', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    var pending = false;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') {
            pending = true;
            return jsonReply({'review_status': 'pending'}, 202);
          }
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          return jsonReply({
            'status': 'ready',
            'review_status': pending ? 'pending' : 'unavailable',
            'review_request_allowed': !pending,
          });
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
            compact: true,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump();
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    expect(
      find.text('KI-Prüfung nicht verfügbar · fachlich ungeprüft'),
      findsOneWidget,
    );
    await tester.tap(find.text('Bild ansehen'));
    await tester.pump();
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    await tester.pump();
    expect(requests.where((r) => r.method == 'POST').length, 1);
    expect(
      requests
          .where((r) => r.method == 'POST')
          .single
          .headers['Idempotency-Key'],
      isNotEmpty,
    );
    expect(requests.last.url.path, '/api/units/unit/public-image');
    expect(
      find.text('KI prüft das Bild … · fachlich ungeprüft'),
      findsOneWidget,
    );
    expect(find.text('KI-Bildprüfung starten'), findsNothing);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('a rejected image can only be regenerated by explicit action', (
    tester,
  ) async {
    final requests = <http.Request>[];
    var pending = false;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') {
            pending = true;
            return jsonReply({'status': 'queued'}, 202);
          }
          return jsonReply(
            pending
                ? {'status': 'queued'}
                : {
                    'status': 'missing',
                    'review_status': 'rejected',
                    'image_rejected': true,
                    'retry_allowed': true,
                  },
          );
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
    expect(find.byType(Image), findsNothing);
    expect(
      find.text(
        'Das Bild hat die KI-Prüfung nicht bestanden. Du kannst weiterlernen.',
      ),
      findsOneWidget,
    );
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    await tester.tap(find.text('Neues Bild erstellen'));
    await tester.pump();
    await tester.pump();
    expect(requests.where((r) => r.method == 'POST').length, 1);
    expect(find.text('Dein Themenbild entsteht …'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('a review retry after a lost response reuses its key', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    var posts = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') {
            posts++;
            return posts == 1
                ? jsonReply({'detail': 'Verbindung unterbrochen'}, 503)
                : jsonReply({'review_status': 'pending'}, 202);
          }
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          return jsonReply({
            'status': 'ready',
            'review_status': posts > 1 ? 'pending' : 'unavailable',
            'review_request_allowed': posts < 2,
          });
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
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    await tester.pump();
    final keys = requests
        .where((r) => r.method == 'POST')
        .map((r) => r.headers['Idempotency-Key'])
        .toList();
    expect(keys.length, 2);
    expect(keys.first, isNotEmpty);
    expect(keys[0], keys[1]);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('an explicitly requested new review uses a new key', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    var posts = 0;
    var readsAfterFirst = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') {
            posts++;
            return jsonReply({'review_status': 'pending'}, 202);
          }
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          if (posts == 0) {
            return jsonReply({
              'status': 'ready',
              'review_status': 'unavailable',
              'review_request_allowed': true,
            });
          }
          if (posts == 1 && ++readsAfterFirst > 1) {
            return jsonReply({
              'status': 'ready',
              'review_status': 'uncertain',
              'review_request_allowed': true,
            });
          }
          return jsonReply({
            'status': 'ready',
            'review_status': 'pending',
            'review_request_allowed': false,
          });
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
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    await tester.pump();
    await tester.pump(const Duration(seconds: 5));
    await tester.pump();
    expect(find.text('KI-Prüfung unklar · fachlich ungeprüft'), findsOneWidget);
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    await tester.pump();
    final keys = requests
        .where((r) => r.method == 'POST')
        .map((r) => r.headers['Idempotency-Key'])
        .toList();
    expect(keys.length, 2);
    expect(keys[0], isNot(equals(keys[1])));
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('a late review request cannot reload a different account', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final requests = <http.Request>[];
    final png = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl61Z8AAAAASUVORK5CYII=',
    );
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.method == 'POST') return pending.future;
          if (request.url.path.endsWith('/file')) {
            return http.Response.bytes(
              png,
              200,
              headers: {'content-type': 'image/png'},
            );
          }
          return jsonReply({
            'status': 'ready',
            'review_status': 'unavailable',
            'review_request_allowed': true,
          });
        }),
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
    await tester.pump();
    await tester.tap(find.text('KI-Bildprüfung starten'));
    await tester.pump();
    state.user = {'id': 'second', 'role': 'child', 'families': <Json>[]};
    pending.complete(jsonReply({'review_status': 'pending'}, 202));
    await tester.pump();
    await tester.pump();
    expect(requests.map((request) => request.method), ['GET', 'GET', 'POST']);
    await tester.pumpWidget(const SizedBox.shrink());
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
