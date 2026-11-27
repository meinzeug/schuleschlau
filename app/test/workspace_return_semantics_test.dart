import 'dart:ui' show PointerDeviceKind, SemanticsAction;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'workspace_tools_100_test.dart' as fixture;

void main() {
  for (final example in [
    ('/material/material', 'Zu Hefte', '/library/child'),
    ('/material/material?from=words', 'Zu Wörter', '/vocabulary/child'),
  ]) {
    testWidgets('mobile return has one accessible action: ${example.$2}', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        await fixture.workspace(tester, (state, router) async {
          final tooltip = find.byTooltip(example.$2);
          final button = find.byWidgetPredicate(
            (widget) =>
                widget is IconButton &&
                widget.icon is Icon &&
                (widget.icon as Icon).icon == Icons.arrow_back_rounded,
          );
          var data = tester.getSemantics(button).getSemanticsData();
          expect(data.label, example.$2);
          expect(data.hasAction(SemanticsAction.tap), isTrue);
          final pointer = await tester.createGesture(
            kind: PointerDeviceKind.mouse,
          );
          await pointer.addPointer(location: tester.getCenter(tooltip));
          await tester.pump(const Duration(seconds: 2));
          await tester.pumpAndSettle();
          data = tester.getSemantics(button).getSemanticsData();
          expect(data.label, example.$2);
          await pointer.removePointer();
          await tester.tap(tooltip);
          await tester.pumpAndSettle();
          expect(router.routeInformationProvider.value.uri.path, example.$3);
        }, initial: example.$1);
      } finally {
        semantics.dispose();
      }
    });
  }
}
