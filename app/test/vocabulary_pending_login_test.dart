import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/vocabulary_screen.dart';

import 'child_context_forms_ux_test.dart' as f;
import 'vocabulary_test.dart' as v;

void main() {
  testWidgets('old family card cannot navigate during login', (tester) async {
    final requests = <http.Request>[];
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                requests.add(r);
                return v.reply({
                  'children': [
                    {'id': 'child', 'display_name': 'Künstliches Kind'},
                  ],
                });
              }),
            ),
          )
          ..user = {
            'id': 'parent',
            'role': 'parent',
            'families': [
              {'id': 'family', 'permission': 'owner'},
            ],
          }
          ..familyId = 'family';
    await tester.pumpWidget(f.home(FamilyVocabularyScreen(state)));
    await tester.pumpAndSettle();
    final card = tester.widget<ListTile>(
      find.widgetWithText(ListTile, 'Künstliches Kind'),
    );
    final count = requests.length;
    state.beginAuthentication();
    card.onTap!();
    await tester.pump();
    expect(requests, hasLength(count));
    expect(find.text('Künstliches Kind'), findsNothing);
    expect(tester.takeException(), isNull);
  });
  for (final change in ['account', 'family', 'session']) {
    testWidgets('old family card cannot navigate after $change changes', (
      tester,
    ) async {
      final requests = <http.Request>[];
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((r) async {
                  requests.add(r);
                  return v.reply({
                    'children': [
                      {'id': 'child', 'display_name': 'Künstliches Kind'},
                    ],
                  });
                }),
              ),
            )
            ..user = {
              'id': 'parent',
              'role': 'parent',
              'families': [
                {'id': 'family', 'permission': 'owner'},
              ],
            }
            ..familyId = 'family';
      await tester.pumpWidget(f.home(FamilyVocabularyScreen(state)));
      await tester.pumpAndSettle();
      final card = tester.widget<ListTile>(
        find.widgetWithText(ListTile, 'Künstliches Kind'),
      );
      final count = requests.length;
      if (change == 'account') state.user = {'id': 'other', 'role': 'parent'};
      if (change == 'family') state.familyId = 'other-family';
      if (change == 'session') state.api.token = 'other-session';
      card.onTap!();
      await tester.pump();
      expect(requests, hasLength(count));
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('family word overview waits for explicit reload after login', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((r) async {
                requests.add(r);
                return v.reply({
                  'children': [
                    {'id': 'child', 'display_name': 'Künstliches Kind'},
                  ],
                });
              }),
            ),
          )
          ..user = {
            'id': 'parent',
            'role': 'parent',
            'families': [
              {'id': 'family', 'permission': 'owner'},
            ],
          }
          ..familyId = 'family';
    final intent = state.beginAuthentication();
    await tester.pumpWidget(f.home(FamilyVocabularyScreen(state)));
    await tester.pump();
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pump();
    expect(requests, isEmpty);
    await f.tap(tester, find.text('Wörter neu laden'));
    expect(requests.map((r) => r.method), ['GET']);
    expect(find.text('Künstliches Kind'), findsOneWidget);
  });
  testWidgets('opening words during login waits for explicit reload', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) async {
        requests.add(r);
        return v.reply(
          r.url.path.endsWith('/imports') ? {'imports': []} : v.listing(),
        );
      }),
    );
    final intent = state.beginAuthentication();
    await tester.pumpWidget(f.home(VocabularyScreen(state, childId: 'child')));
    await tester.pump();
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pump(const Duration(seconds: 4));
    expect(requests, isEmpty);
    await f.tap(tester, find.text('Wörter neu laden'));
    expect(requests, hasLength(2));
    expect(find.text('Apfel'), findsOneWidget);
    expect(requests.every((r) => r.method == 'GET'), isTrue);
  });

  testWidgets('login hides old words and does not reload after cancellation', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) async {
        requests.add(r);
        return v.reply(
          r.url.path.endsWith('/imports') ? {'imports': []} : v.listing(),
        );
      }),
    );
    await tester.pumpWidget(f.home(VocabularyScreen(state, childId: 'child')));
    await tester.pumpAndSettle();
    expect(find.text('Apfel'), findsOneWidget);
    final count = requests.length;
    final intent = state.beginAuthentication();
    await tester.pump();
    expect(find.text('Apfel'), findsNothing);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pump(const Duration(seconds: 4));
    expect(requests, hasLength(count));
    await f.tap(tester, find.text('Wörter neu laden'));
    expect(find.text('Apfel'), findsOneWidget);
    expect(requests.every((r) => r.method == 'GET'), isTrue);
  });

  testWidgets('pending word import keeps its idempotency key across login', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) {
        requests.add(r);
        if (r.method == 'POST' && r.url.path.endsWith('/imports')) {
          return pending.future;
        }
        return Future.value(
          v.reply(
            r.url.path.endsWith('/imports') ? {'imports': []} : v.listing(),
          ),
        );
      }),
    );
    await tester.pumpWidget(f.home(VocabularyScreen(state, childId: 'child')));
    await tester.pumpAndSettle();
    await f.tap(tester, find.byTooltip('Wörter hinzufügen'));
    await f.tap(tester, find.text('Mehrere Wörter oder Text'));
    final fields = find.descendant(
      of: find.byType(AlertDialog),
      matching: find.byType(TextField),
    );
    await tester.enterText(fields.last, 'dog = Hund');
    await tester.ensureVisible(find.text('Wortpaare prüfen'));
    await tester.tap(find.text('Wortpaare prüfen'));
    for (var i = 0; i < 20 && !requests.any((r) => r.method == 'POST'); i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    final post = requests.singleWhere((r) => r.method == 'POST');
    final savedKey = post.headers['Idempotency-Key'];
    expect(savedKey, isNotEmpty);
    final intent = state.beginAuthentication();
    await tester.pump();
    state.cancelAuthentication(intent);
    pending.complete(v.reply({'id': 'old', 'status': 'review', 'pairs': []}));
    await tester.pump();
    await tester.pump();
    await f.tap(tester, find.text('Wörter neu laden'));
    final saved = state.collectionViews.entries
        .singleWhere((e) => e.key.endsWith(':pending-import'))
        .value;
    expect(saved['key'], savedKey);
    expect(requests.where((r) => r.method == 'POST'), hasLength(1));
    expect(find.text('Stimmen deine Wörter?'), findsNothing);
  });

  testWidgets('closing an old word dialog cannot send after sign-in changes', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) async {
        requests.add(r);
        return v.reply(
          r.url.path.endsWith('/imports') ? {'imports': []} : v.listing(),
        );
      }),
    );
    await tester.pumpWidget(f.home(VocabularyScreen(state, childId: 'child')));
    await tester.pumpAndSettle();
    await f.tap(tester, find.byTooltip('Wörter hinzufügen'));
    await f.tap(tester, find.text('Mehrere Wörter oder Text'));
    final fields = find.descendant(
      of: find.byType(AlertDialog),
      matching: find.byType(TextField),
    );
    await tester.enterText(fields.last, 'dog = Hund');
    await tester.ensureVisible(find.text('Wortpaare prüfen'));
    await tester.tap(find.text('Wortpaare prüfen'));
    final intent = state.beginAuthentication();
    state.cancelAuthentication(intent);
    await tester.pump();
    final reload = tester.widget<TextButton>(
      find.widgetWithText(TextButton, 'Wörter neu laden', skipOffstage: false),
    );
    reload.onPressed!();
    await tester.pumpAndSettle();
    expect(requests.where((r) => r.method == 'POST'), isEmpty);
    expect(find.text('Stimmen deine Wörter?'), findsNothing);
  });
}
