import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/coaching_panel.dart';
import 'package:schulpilot/ui.dart';

import 'coaching_test.dart' as fixtures;

void main() {
  for (final supported in [false, true]) {
    testWidgets(
      'Saved report uses ${supported ? 'bound' : 'safe legacy'} recheck',
      (tester) async {
        final unit = fixtures.savedUnit(uncertain: true);
        unit['supports_recheck'] = true;
        if (supported) unit['supports_recheck_attempt_id'] = true;
        final q = (unit['questions'] as List).first as Map;
        (q['attempts'] as List).first['id'] = 'artificial-attempt';
        final requests = <http.Request>[];
        var refreshed = false;
        final state = AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((r) async {
              requests.add(r);
              return http.Response(
                '{}',
                200,
                headers: {'content-type': 'application/json'},
              );
            }),
          ),
        )..user = {'id': 'kid', 'role': 'child', 'child_id': 'child'};
        await tester.pumpWidget(
          MaterialApp(
            theme: appTheme(),
            home: Scaffold(
              body: SingleChildScrollView(
                child: CoachingPanel(
                  state: state,
                  unit: unit,
                  refresh: () async {
                    refreshed = true;
                  },
                ),
              ),
            ),
          ),
        );
        await tester.ensureVisible(find.text('Deine Antworten'));
        await tester.tap(find.text('Deine Antworten'));
        await tester.pumpAndSettle();
        final button = find.text('Antwort erneut prüfen');
        if (supported) {
          await tester.ensureVisible(button);
          await tester.tap(button);
          await tester.pumpAndSettle();
          expect(requests, hasLength(1));
          expect(jsonDecode(requests.single.body), {
            'attempt_id': 'artificial-attempt',
          });
          expect(refreshed, isTrue);
        } else {
          expect(button, findsNothing);
          expect(
            find.textContaining('nicht sicher erneut prüfen'),
            findsOneWidget,
          );
          expect(requests, isEmpty);
        }
        await tester.pumpWidget(const SizedBox());
      },
    );
  }
  testWidgets(
    'A stale saved report shows the server conflict without refreshing',
    (tester) async {
      final unit = fixtures.savedUnit(uncertain: true)
        ..['supports_recheck'] = true
        ..['supports_recheck_attempt_id'] = true;
      final q = (unit['questions'] as List).first as Map;
      (q['attempts'] as List).first['id'] = 'artificial-attempt';
      var refreshed = false;
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((r) async {
            expect(jsonDecode(r.body), {'attempt_id': 'artificial-attempt'});
            return http.Response(
              '{"detail":"Die Antwort hat sich geändert."}',
              409,
              headers: {'content-type': 'application/json'},
            );
          }),
        ),
      )..user = {'id': 'kid', 'role': 'child', 'child_id': 'child'};
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: CoachingPanel(
                state: state,
                unit: unit,
                refresh: () async {
                  refreshed = true;
                },
              ),
            ),
          ),
        ),
      );
      await tester.ensureVisible(find.text('Deine Antworten'));
      await tester.tap(find.text('Deine Antworten'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Antwort erneut prüfen'));
      await tester.tap(find.text('Antwort erneut prüfen'));
      await tester.pumpAndSettle();
      expect(find.text('Die Antwort hat sich geändert.'), findsOneWidget);
      expect(refreshed, isFalse);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
}
