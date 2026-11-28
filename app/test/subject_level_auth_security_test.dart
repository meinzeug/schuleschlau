import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/subject_level.dart';

import 'parent_learning_overview_test.dart' as fixture;
import 'parent_preferences_messages_ux87_test.dart' as levels;

void main() {
  late AppState state;
  late List<http.Request> requests;
  Future<http.Response> Function(http.Request)? intercept;

  Future<void> mount(WidgetTester tester) async {
    requests = [];
    state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) async {
                requests.add(request);
                if (intercept != null) return intercept!(request);
                return fixture.jsonResponse(
                  request.url.path.endsWith('/levels')
                      ? levels.levels()
                      : {
                          'can_manage': true,
                          'items': [levels.subject()],
                        },
                );
              }),
            ),
          )
          ..user = fixture.parentUser()
          ..familyId = 'own-family';
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (ctx) => FilledButton(
              onPressed: () => editSubjectLevel(ctx, state, 'child', 'math'),
              child: const Text('Öffnen'),
            ),
          ),
        ),
      ),
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    });
  }

  setUp(() => intercept = null);

  testWidgets(
    'opening during authentication sends no reads or writes and requires a new action',
    (tester) async {
      await mount(tester);
      final intent = state.beginAuthentication();
      await tester.tap(find.text('Öffnen'));
      await tester.pumpAndSettle();
      expect(requests, isEmpty);
      expect(find.text('Stufe festlegen'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      expect(requests, isEmpty);
      await tester.tap(find.text('Öffnen'));
      await tester.pumpAndSettle();
      expect(requests, hasLength(2));
      expect(requests.every((r) => r.method == 'GET'), isTrue);
      expect(find.text('Stufe festlegen'), findsOneWidget);
    },
  );

  testWidgets(
    'captured old selection and buttons cannot write or close a new dialog',
    (tester) async {
      await mount(tester);
      await tester.tap(find.text('Öffnen'));
      await tester.pumpAndSettle();
      final select = tester
          .widget<DropdownButtonFormField<String>>(
            find.byType(DropdownButtonFormField<String>),
          )
          .onChanged!;
      final save = tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Stufe übernehmen'),
          )
          .onPressed!;
      final cancel = tester
          .widget<TextButton>(find.widgetWithText(TextButton, 'Abbrechen'))
          .onPressed!;
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Stufe festlegen'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.tap(find.text('Öffnen'));
      await tester.pumpAndSettle();
      select('class-6');
      save();
      cancel();
      await tester.pumpAndSettle();
      expect(find.text('Stufe festlegen'), findsOneWidget);
      expect(requests.every((r) => r.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'an unfinished level read cannot open the old dialog after sign-in',
    (tester) async {
      final pending = Completer<http.Response>();
      intercept = (r) => r.url.path.endsWith('/levels')
          ? pending.future
          : Future.value(
              fixture.jsonResponse({
                'can_manage': true,
                'items': [levels.subject()],
              }),
            );
      await mount(tester);
      await tester.tap(find.text('Öffnen'));
      await tester.pump();
      expect(requests, hasLength(2));
      final intent = state.beginAuthentication();
      pending.complete(fixture.jsonResponse(levels.levels()));
      await tester.pumpAndSettle();
      expect(find.text('Stufe festlegen'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      expect(requests, hasLength(2));
      expect(find.text('Stufe festlegen'), findsNothing);
    },
  );
}
