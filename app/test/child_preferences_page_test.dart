import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/dashboard.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets('new child creation shows defaults and permits changing them', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                requests.add(request);
                return http.Response(
                  '{}',
                  201,
                  headers: {'content-type': 'application/json'},
                );
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
    state.api.token = 'test-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => showChildDialog(context, state),
              child: const Text('Öffnen'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Öffnen'));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<SwitchListTile>(
            find.widgetWithText(
              SwitchListTile,
              'Push auf dem Kindergerät erlauben',
            ),
          )
          .value,
      isTrue,
    );
    expect(
      tester
          .widget<SwitchListTile>(
            find.widgetWithText(SwitchListTile, 'Lernerinnerung in der App'),
          )
          .value,
      isTrue,
    );
    await tester.ensureVisible(
      find.widgetWithText(SwitchListTile, 'Push auf dem Kindergerät erlauben'),
    );
    await tester.tap(
      find.widgetWithText(SwitchListTile, 'Push auf dem Kindergerät erlauben'),
    );
    await tester.ensureVisible(find.text('Kinderzugang erstellen'));
    await tester.tap(find.text('Kinderzugang erstellen'));
    await tester.pumpAndSettle();
    expect(jsonDecode(requests.single.body)['push_consent'], isFalse);
    expect(jsonDecode(requests.single.body)['reminders'], isTrue);
  });
  testWidgets('read-only family member cannot edit the settings', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                requests.add(request);
                return http.Response('{}', 200);
              }),
            ),
          )
          ..user = {
            'id': 'parent',
            'role': 'parent',
            'families': [
              {'id': 'family', 'permission': 'view'},
            ],
          }
          ..familyId = 'family';
    state.api.token = 'test-session';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: ChildPreferencesPage(
              state: state,
              child: {
                'id': 'child',
                'display_name': 'Testkind',
                'preferences_revision': 1,
                'preferences': {
                  'daily_minutes': 20,
                  'reminders': false,
                  'push_consent': false,
                },
              },
              onSaved: () {},
            ),
          ),
        ),
      ),
    );
    expect(
      tester
          .widget<SwitchListTile>(
            find.widgetWithText(
              SwitchListTile,
              'Push für dieses Kind erlauben',
            ),
          )
          .onChanged,
      isNull,
    );
    expect(find.text('Einstellungen speichern'), findsNothing);
    expect(requests, isEmpty);
  });
  testWidgets(
    'parent can edit child reminders and save with the source revision',
    (tester) async {
      final requests = <http.Request>[];
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((request) async {
                  requests.add(request);
                  return http.Response(
                    '{}',
                    200,
                    headers: {'content-type': 'application/json'},
                  );
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
      state.api.token = 'test-session';
      var saved = 0;
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: ChildPreferencesPage(
                state: state,
                child: {
                  'id': 'child',
                  'display_name': 'Testkind',
                  'preferences_revision': 4,
                  'preferences': {
                    'daily_minutes': 20,
                    'reminders': false,
                    'push_consent': false,
                    'quiet_start': 20,
                    'quiet_end': 8,
                  },
                },
                onSaved: () => saved++,
              ),
            ),
          ),
        ),
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Tägliches Mindestziel'),
        '30',
      );
      await tester.tap(
        find.widgetWithText(SwitchListTile, 'Lernerinnerung in der App'),
      );
      await tester.tap(
        find.widgetWithText(SwitchListTile, 'Push für dieses Kind erlauben'),
      );
      await tester.ensureVisible(find.text('Einstellungen speichern'));
      await tester.tap(find.text('Einstellungen speichern'));
      await tester.pumpAndSettle();
      expect(saved, 1);
      expect(requests.single.method, 'PUT');
      expect(requests.single.headers['If-Match'], '4');
      expect(jsonDecode(requests.single.body), {
        'daily_minutes': 30,
        'reminders': true,
        'push_consent': true,
        'quiet_start': 20,
        'quiet_end': 8,
      });
    },
  );
}
