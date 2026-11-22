import 'dart:convert';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/admin_beta_applications.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/auth_screens.dart';
import 'package:schulpilot/parent_beta_application.dart';
import 'package:schulpilot/store_screens.dart';
import 'package:schulpilot/ui.dart';

http.Response reply(Object value, [int status = 200]) => http.Response(
  jsonEncode(value),
  status,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Finder field(String label) => find.byWidgetPredicate(
  (w) => w is TextField && w.decoration?.labelText == label,
);

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('Beta landing requires explicit server availability', (
    tester,
  ) async {
    var beta = false;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (request) async => reply({
            'beta': {'enabled': beta},
          }),
        ),
      ),
    );
    Future<void> mount() async {
      await tester.pumpWidget(
        MaterialApp(theme: appTheme(), home: LandingScreen(state)),
      );
      await tester.pumpAndSettle();
    }

    await mount();
    expect(find.text('Für die Beta anmelden'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    beta = true;
    await mount();
    expect(find.text('Für die Beta anmelden'), findsOneWidget);
    expect(find.textContaining('erst nach Freigabe'), findsOneWidget);
  });

  testWidgets('Beta registration sends opt-in and keeps adult consent', (
    tester,
  ) async {
    Json? posted;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          if (request.method == 'POST' &&
              request.url.path.endsWith('/auth/register')) {
            posted = Json.from(jsonDecode(request.body));
            return reply({
              'message': 'Bitte E-Mail bestätigen.',
              'access_notice': 'Die Beta-Anmeldung wird geprüft.',
            }, 201);
          }
          return reply({
            'beta': {'enabled': true},
          });
        }),
      ),
    );
    final router = GoRouter(
      initialLocation: '/register?beta=1',
      routes: [
        GoRoute(
          path: '/register',
          builder: (_, s) =>
              AuthScreen(state, mode: 'register', linkUri: s.uri),
        ),
        GoRoute(path: '/login', builder: (_, _) => const Scaffold()),
        GoRoute(path: '/privacy', builder: (_, _) => const Scaffold()),
      ],
    );
    addTearDown(router.dispose);
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pumpAndSettle();
    expect(find.text('Für die Beta anmelden'), findsOneWidget);
    expect(find.text('Mit Google anmelden'), findsNothing);
    await tester.enterText(field('E-Mail-Adresse'), 'parent@example.invalid');
    await tester.enterText(field('Dein Anzeigename'), 'Elternteil');
    await tester.enterText(field('Name deiner Familie'), 'Beispielfamilie');
    await tester.enterText(field('Neues Passwort'), 'Artificial-Password-123!');
    await tester.ensureVisible(find.byType(CheckboxListTile));
    await tester.tap(find.byType(CheckboxListTile));
    await tester.ensureVisible(find.text('Beta-Anmeldung absenden'));
    await tester.tap(find.text('Beta-Anmeldung absenden'));
    await tester.pumpAndSettle();
    expect(posted?['adult_consent'], true);
    expect(posted?['beta_requested'], true);
    expect(find.text('Die Beta-Anmeldung wird geprüft.'), findsOneWidget);
  });

  testWidgets('admin sees pending and explicitly approves with revision', (
    tester,
  ) async {
    final sent = <http.Request>[];
    const actor = '11111111111111111111111111111111';
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                sent.add(request);
                if (request.method == 'POST') {
                  return reply({'status': 'approved'});
                }
                return reply({
                  'items': [
                    {
                      'id': '22222222222222222222222222222222',
                      'display_name': 'Elternteil',
                      'family_name': 'Beispielfamilie',
                      'email': 'parent@example.invalid',
                      'email_verified': true,
                      'status': 'pending',
                      'revision': 4,
                    },
                  ],
                  'page': 1,
                  'has_more': false,
                });
              }),
            ),
          )
          ..user = {'id': actor, 'role': 'admin', 'display_name': 'Admin'}
          ..api.token = 'synthetic-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(child: AdminBetaApplications(state)),
        ),
      ),
    );
    await tester.tap(find.text('Beta-Anmeldungen'));
    await tester.pumpAndSettle();
    expect(find.text('Elternteil'), findsOneWidget);
    await tester.tap(find.byTooltip('Freigeben'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('ohne persönliche KI-Mengen- und Kostengrenzen'),
      findsOneWidget,
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Freigeben'));
    await tester.pumpAndSettle();
    final post = sent.singleWhere((request) => request.method == 'POST');
    expect(jsonDecode(post.body), {'revision': 4, 'decision': 'approve'});
    expect(post.headers['x-schulpilot-account'], actor);
    expect(find.text('Beta-Zugang freigegeben.'), findsOneWidget);
  });

  testWidgets('unverified email cannot be approved', (tester) async {
    var posts = 0;
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                if (request.method == 'POST') posts++;
                return reply({
                  'items': [
                    {
                      'id': '22222222222222222222222222222222',
                      'display_name': 'Elternteil',
                      'family_name': 'Beispielfamilie',
                      'email': 'parent@example.invalid',
                      'email_verified': false,
                      'status': 'pending',
                      'revision': 4,
                    },
                  ],
                  'page': 1,
                  'has_more': false,
                });
              }),
            ),
          )
          ..user = {'id': '11111111111111111111111111111111', 'role': 'admin'}
          ..api.token = 'synthetic-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(child: AdminBetaApplications(state)),
        ),
      ),
    );
    await tester.tap(find.text('Beta-Anmeldungen'));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<IconButton>(
            find.byWidgetPredicate(
              (widget) => widget is IconButton && widget.tooltip == 'Freigeben',
            ),
          )
          .onPressed,
      isNull,
    );
    expect(find.textContaining('E-Mail noch nicht bestätigt'), findsOneWidget);
    expect(posts, 0);
  });

  testWidgets('stale revision is refreshed without retrying decision', (
    tester,
  ) async {
    var posts = 0, reads = 0;
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                if (request.method == 'POST') {
                  posts++;
                  return reply({'detail': 'Anmeldung wurde geändert.'}, 409);
                }
                reads++;
                return reply({
                  'items': [
                    {
                      'id': '22222222222222222222222222222222',
                      'display_name': 'Elternteil',
                      'family_name': 'Beispielfamilie',
                      'email': 'parent@example.invalid',
                      'email_verified': true,
                      'status': 'pending',
                      'revision': 4,
                    },
                  ],
                  'page': 1,
                  'has_more': false,
                });
              }),
            ),
          )
          ..user = {'id': '11111111111111111111111111111111', 'role': 'admin'}
          ..api.token = 'synthetic-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(child: AdminBetaApplications(state)),
        ),
      ),
    );
    await tester.tap(find.text('Beta-Anmeldungen'));
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('Freigeben'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Freigeben'));
    await tester.pumpAndSettle();
    expect(posts, 1);
    expect(reads, 2);
    expect(find.text('Anmeldung wurde geändert.'), findsOneWidget);
  });

  testWidgets(
    'account change closes the approval dialog and prevents mutation',
    (tester) async {
      var posts = 0;
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((request) async {
                  if (request.method == 'POST') posts++;
                  return reply({
                    'items': [
                      {
                        'id': '22222222222222222222222222222222',
                        'display_name': 'Elternteil',
                        'family_name': 'Beispielfamilie',
                        'email': 'parent@example.invalid',
                        'email_verified': true,
                        'status': 'pending',
                        'revision': 4,
                      },
                    ],
                    'page': 1,
                    'has_more': false,
                  });
                }),
              ),
            )
            ..user = {'id': '11111111111111111111111111111111', 'role': 'admin'}
            ..api.token = 'synthetic-session';
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(child: AdminBetaApplications(state)),
          ),
        ),
      );
      await tester.tap(find.text('Beta-Anmeldungen'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Freigeben'));
      await tester.pumpAndSettle();
      expect(find.text('Beta-Zugang freigeben?'), findsOneWidget);
      state.user = {'id': '33333333333333333333333333333333', 'role': 'admin'};
      state.notifyListeners();
      await tester.pumpAndSettle();
      expect(find.text('Beta-Zugang freigeben?'), findsNothing);
      expect(find.text('Elternteil'), findsNothing);
      expect(posts, 0);
    },
  );

  testWidgets('admin beta review fits a narrow screen with larger text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient(
                (_) async => reply({
                  'items': [
                    {
                      'id': '22222222222222222222222222222222',
                      'display_name': 'Künstliches Elternkonto',
                      'family_name': 'Beispielfamilie',
                      'email': 'parent@example.invalid',
                      'email_verified': true,
                      'status': 'pending',
                      'revision': 4,
                      'usage': {
                        'calls': 4,
                        'known_usd_micros': 10000,
                        'unknown_calls': 1,
                        'input_tokens': 123,
                        'output_tokens': 45,
                        'by_model': {
                          'public/test-model': {
                            'calls': 4,
                            'known_usd_micros': 10000,
                            'unknown_calls': 1,
                          },
                        },
                      },
                    },
                  ],
                  'page': 1,
                  'has_more': false,
                }),
              ),
            ),
          )
          ..user = {'id': '11111111111111111111111111111111', 'role': 'admin'}
          ..api.token = 'synthetic-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: const TextScaler.linear(2)),
          child: child!,
        ),
        home: Scaffold(
          body: SingleChildScrollView(child: AdminBetaApplications(state)),
        ),
      ),
    );
    await tester.tap(find.text('Beta-Anmeldungen'));
    await tester.pumpAndSettle();
    expect(find.textContaining('1 noch unbekannt'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('beta setting is a revision-bound unsaved admin draft', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          return reply({});
        }),
      ),
    )..user = {'id': '11111111111111111111111111111111', 'role': 'admin'};
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: StoreAdminForm(state, {
              'recipient': '',
              'iban': '',
              'bank_name': '',
              'tax_mode': 'unconfirmed',
              'enabled': false,
              'beta_enabled': false,
              'revision': 7,
              'missing': [],
              'plans': [
                {
                  'id': 'start',
                  'name': 'Start',
                  'price_cents': 990,
                  'children': 1,
                  'calls': 100,
                },
              ],
            }, onSaved: () {}),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    final betaSwitch = find.byWidgetPredicate(
      (w) =>
          w is SwitchListTile &&
          w.title is Text &&
          (w.title as Text).data ==
              'Beta-Bewerbungen auf der Startseite anbieten',
    );
    await tester.ensureVisible(betaSwitch);
    await tester.tap(betaSwitch);
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    final save = find.text('Verkaufseinstellungen speichern');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(requests, hasLength(1));
    expect(jsonDecode(requests.single.body)['beta_enabled'], true);
    expect(jsonDecode(requests.single.body)['revision'], 7);
  });

  testWidgets('existing owner sees status and explicitly applies once', (
    tester,
  ) async {
    var posts = 0;
    const family = '44444444444444444444444444444444';
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                if (request.method == 'POST') {
                  posts++;
                  return reply({'status': 'pending', 'revision': 1}, 202);
                }
                if (request.url.path.endsWith('/store/catalog')) {
                  return reply({
                    'beta': {'enabled': true},
                  });
                }
                return reply({'status': 'none'});
              }),
            ),
          )
          ..user = {
            'id': '11111111111111111111111111111111',
            'role': 'parent',
            'families': [
              {'id': family, 'permission': 'owner'},
            ],
          }
          ..familyId = family
          ..api.token = 'synthetic-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(child: ParentBetaApplication(state)),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(posts, 0);
    await tester.tap(find.text('Für die Beta anmelden'));
    await tester.pumpAndSettle();
    expect(posts, 1);
    expect(find.textContaining('Deine Anmeldung wird geprüft'), findsOneWidget);
    expect(find.text('Für die Beta anmelden'), findsNothing);
  });

  testWidgets('old server without beta support is not presented as an error', (
    tester,
  ) async {
    final requests = <String>[];
    const family = '44444444444444444444444444444444';
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                requests.add(request.url.path);
                return reply({});
              }),
            ),
          )
          ..user = {
            'id': '11111111111111111111111111111111',
            'role': 'parent',
            'families': [
              {'id': family, 'permission': 'owner'},
            ],
          }
          ..familyId = family;
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(body: ParentBetaApplication(state)),
      ),
    );
    await tester.pumpAndSettle();
    expect(requests, ['/api/store/catalog']);
    expect(find.text('SchuleSchlau Beta'), findsNothing);
  });

  testWidgets('late beta status from a different parent is discarded', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    const family = '44444444444444444444444444444444';
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                if (request.url.path.endsWith('/store/catalog')) {
                  return reply({
                    'beta': {'enabled': true},
                  });
                }
                return pending.future;
              }),
            ),
          )
          ..user = {
            'id': '11111111111111111111111111111111',
            'role': 'parent',
            'families': [
              {'id': family, 'permission': 'owner'},
            ],
          }
          ..familyId = family;
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(body: ParentBetaApplication(state)),
      ),
    );
    await tester.pump();
    state.user = {
      'id': '33333333333333333333333333333333',
      'role': 'parent',
      'families': [
        {'id': family, 'permission': 'owner'},
      ],
    };
    state.notifyListeners();
    pending.complete(reply({'status': 'approved'}));
    await tester.pumpAndSettle();
    expect(
      find.text('Deine Familie ist für die Beta freigegeben.'),
      findsNothing,
    );
    expect(find.text('SchuleSchlau Beta'), findsNothing);
  });
}
