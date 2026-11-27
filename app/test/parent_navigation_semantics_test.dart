import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'mobile_parent_child_navigation_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final canPick in [true, false]) {
    testWidgets(
      'compact parent menu exposes its state (child picker: $canPick)',
      (tester) async {
        final semantics = tester.ensureSemantics();
        try {
          final app = fixture.Fixture();
          if (!canPick) app.state.familyId = null;
          await app.mount(tester);
          final label = canPick
              ? 'Bereiche und Kindwechsel'
              : 'Bereiche öffnen';
          final toggle = find.byWidgetPredicate(
            (widget) => widget is IconButton && widget.tooltip == label,
          );
          var data = tester.getSemantics(toggle).getSemanticsData();
          expect(data.label, label);
          expect(data.flagsCollection.isExpanded, Tristate.isFalse);
          expect(data.hasAction(SemanticsAction.tap), isTrue);
          await fixture.tap(tester, toggle);
          data = tester.getSemantics(toggle).getSemanticsData();
          expect(data.flagsCollection.isExpanded, Tristate.isTrue);
          expect(
            app.requests.every((request) => request.method == 'GET'),
            isTrue,
          );
        } finally {
          semantics.dispose();
        }
      },
    );
  }
}
