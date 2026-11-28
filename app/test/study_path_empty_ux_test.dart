import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/study_path_panel.dart';

import 'child_local_tools_ux88_test.dart' as fixture;
import 'child_study_path_ux90_test.dart' as path;

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Empty learning path has no useless search at $width / $scale×',
      (tester) async {
        final requests = <http.Request>[];
        final state = fixture.account((request) async {
          requests.add(request);
          return fixture.reply(path.path([]));
        });
        await fixture.show(
          tester,
          StudyPathPanel(state, 'child', 'day'),
          size: Size(width, 844),
          scale: scale,
        );
        expect(
          find.text('Hier sind noch keine Lernschritte zu sehen.'),
          findsOneWidget,
        );
        expect(find.text('Alle Lernschritte zeigen'), findsNothing);
        expect(find.text('Suchen und filtern'), findsNothing);
        expect(requests.every((r) => r.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('A filter stays resettable after all steps disappear', (
    tester,
  ) async {
    final requests = <http.Request>[];
    var blocks = [path.block('A', 'planned')];
    final state = fixture.account((request) async {
      requests.add(request);
      return fixture.reply(path.path(blocks));
    });
    await fixture.show(tester, StudyPathPanel(state, 'child', 'day'));
    await fixture.tap(tester, find.text('Alle Lernschritte'));
    await fixture.tap(tester, find.text('Suchen und filtern'));
    await fixture.tap(tester, find.widgetWithText(ChoiceChip, 'Bereit'));
    expect(find.text('Alle Lernschritte zeigen'), findsOneWidget);
    blocks = [];
    await fixture.tap(tester, find.byTooltip('Lernweg aktualisieren'));
    expect(find.text('Alle Lernschritte zeigen'), findsOneWidget);
    await fixture.tap(tester, find.text('Alle Lernschritte zeigen'));
    expect(
      find.text('Hier sind noch keine Lernschritte zu sehen.'),
      findsOneWidget,
    );
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  for (final login in [true, false]) {
    testWidgets(
      'Stale reset cannot run after ${login ? 'sign-in' : 'account change'}',
      (tester) async {
        final requests = <http.Request>[];
        final state = fixture.account((request) async {
          requests.add(request);
          return fixture.reply(path.path([path.block('A', 'planned')]));
        });
        await fixture.show(tester, StudyPathPanel(state, 'child', 'day'));
        await fixture.tap(tester, find.text('Alle Lernschritte'));
        await fixture.tap(tester, find.text('Suchen und filtern'));
        await fixture.tap(tester, find.widgetWithText(ChoiceChip, 'Bereit'));
        final reset = tester
            .widget<TextButton>(
              find.widgetWithText(TextButton, 'Alle Lernschritte zeigen'),
            )
            .onPressed!;
        final dynamic body = tester.state(find.byType(StudyPathPanel));
        expect(body.blockFilter, 'ready');
        final before = requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          reset();
          state.cancelAuthentication(intent);
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        reset();
        expect(body.blockFilter, 'ready');
        await tester.pumpAndSettle();
        expect(requests, hasLength(before));
        expect(tester.takeException(), isNull);
      },
    );
  }
}
