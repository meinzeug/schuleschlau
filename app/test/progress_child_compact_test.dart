import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/progress_screen.dart';

import 'child_hierarchy_103_test.dart' as hierarchy;
import 'progress_cards_ux88_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final size in [(390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Kinder-Lernstand zeigt Fach und optionalen Überblick bei $size',
      (tester) async {
        final requests = <http.Request>[];
        final state = AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) async {
              requests.add(request);
              final value = fixture.data(request);
              value['selected_totals'] = {
                ...fixture.evidence(4),
                'independent_tasks': 1,
                'assisted_tasks': 1,
                'needs_practice_tasks': 1,
                'uncertain_tasks': 1,
              };
              return fixture.reply(value);
            }),
          ),
        )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'kid'};
        await hierarchy.mountPage(
          tester,
          state,
          ProgressScreen(state, childId: 'kid'),
          size: Size(size.$1, 844),
          scale: size.$2,
        );
        final summary = find.byKey(const ValueKey('child-progress-summary'));
        final detail = find.descendant(
          of: summary,
          matching: find.text('1 mit Hilfe/erneut gelöst'),
        );
        expect(find.text('Dein Überblick'), findsOneWidget);
        expect(find.text('4 Aufgaben geübt'), findsOneWidget);
        expect(detail, findsNothing);
        expect(find.text('Mathematik'), findsOneWidget);
        expect(find.text('Seite 1 von 1'), findsNothing);
        await tester.ensureVisible(find.text('Dein Überblick'));
        await tester.tap(find.text('Dein Überblick'));
        await tester.pumpAndSettle();
        expect(detail, findsOneWidget);
        expect(
          find.descendant(of: summary, matching: find.text('1 weiter üben')),
          findsOneWidget,
        );
        expect(
          find.descendant(
            of: summary,
            matching: find.text('1 Bewertung offen'),
          ),
          findsOneWidget,
        );
        expect(
          find.descendant(of: summary, matching: find.text('1 alleine gelöst')),
          findsOneWidget,
        );
        await tester.ensureVisible(find.text('Dein Überblick'));
        await tester.tap(find.text('Dein Überblick'));
        await tester.pumpAndSettle();
        expect(detail, findsNothing);
        expect(find.text('Mathematik'), findsOneWidget);
        expect(requests.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
