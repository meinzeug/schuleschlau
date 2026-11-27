import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'child_school_day_actions_ux88_test.dart' as view;
import 'school_day_background_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets('day details expose the current expansion state', (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      final server = fixture.PreparationServer(pages: []);
      final state = server.state();
      await view.open(tester, state);
      final control = find.text('Mehr zu diesem Tag');
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await view.tap(tester, 'Mehr zu diesem Tag');
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(
        find.text(
          'Deine Eltern können die Heftseiten und deine Übungen ansehen.',
        ),
        findsOneWidget,
      );
      await view.tap(tester, 'Mehr zu diesem Tag');
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
    } finally {
      semantics.dispose();
    }
  });
}
