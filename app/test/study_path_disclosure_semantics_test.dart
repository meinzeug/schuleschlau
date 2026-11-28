import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/study_path_panel.dart';

import 'child_local_tools_ux88_test.dart' as fixture;
import 'child_study_path_ux90_test.dart' as paths;

void main() {
  testWidgets(
    'Lernschritte melden ihren geöffneten Zustand ohne Schreibzugriff',
    (tester) async {
      final semantics = tester.ensureSemantics();
      try {
        final requests = <http.Request>[];
        final state = fixture.account((request) async {
          requests.add(request);
          return fixture.reply(
            paths.path([
              paths.block('A', 'completed'),
              paths.block('B', 'ready'),
            ]),
          );
        });
        await fixture.show(tester, StudyPathPanel(state, 'child', 'day'));
        final control = find.text('Alle Lernschritte');
        final before = requests.length;
        var data = tester.getSemantics(control).getSemanticsData();
        expect(data.flagsCollection.isExpanded, Tristate.isFalse);
        expect(data.hasAction(SemanticsAction.tap), isTrue);
        await fixture.tap(tester, control);
        data = tester.getSemantics(control).getSemanticsData();
        expect(data.flagsCollection.isExpanded, Tristate.isTrue);
        expect(data.hasAction(SemanticsAction.tap), isTrue);
        final filter = find.text('Suchen und filtern');
        data = tester.getSemantics(filter).getSemanticsData();
        expect(data.flagsCollection.isExpanded, Tristate.isFalse);
        expect(data.hasAction(SemanticsAction.tap), isTrue);
        await fixture.tap(tester, filter);
        data = tester.getSemantics(filter).getSemanticsData();
        expect(data.flagsCollection.isExpanded, Tristate.isTrue);
        await fixture.tap(tester, filter);
        await fixture.tap(tester, control);
        expect(
          tester
              .getSemantics(control)
              .getSemanticsData()
              .flagsCollection
              .isExpanded,
          Tristate.isFalse,
        );
        expect(requests.every((request) => request.method == 'GET'), isTrue);
        expect(requests.length, before);
      } finally {
        semantics.dispose();
      }
    },
  );
}
