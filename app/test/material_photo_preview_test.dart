import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/notebook_photo.dart';

import 'material_reader_101_test.dart' as material;

void main() {
  for (final size in [
    const Size(320, 568),
    const Size(390, 844),
    const Size(1200, 900),
  ]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets(
        'Photo preview and zoom work at $size and $scale text scale',
        (tester) async {
          final fixture = material.Fixture();
          await fixture.mount(
            tester,
            width: size.width,
            height: size.height,
            scale: scale,
          );
          final preview = find.byKey(const ValueKey('material-photo-preview'));
          await tester.ensureVisible(preview);
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull, reason: 'preview');
          expect(tester.getSize(preview).height, inInclusiveRange(150, 260));
          if (size.height >= 800) {
            expect(tester.getSize(preview).height, greaterThan(150));
          }
          expect(find.text('Foto vergrößern'), findsOneWidget);
          expect(
            find.descendant(of: preview, matching: find.byType(NotebookPhoto)),
            findsOneWidget,
          );
          expect(
            find.descendant(
              of: preview,
              matching: find.byWidgetPredicate(
                (w) => w is Image && w.fit == BoxFit.contain,
              ),
            ),
            findsOneWidget,
          );

          await material.tap(tester, find.text('Foto vergrößern'));
          expect(tester.takeException(), isNull, reason: 'zoom');
          expect(find.byTooltip('Foto nach links drehen'), findsOneWidget);
          await material.tap(tester, find.byTooltip('Schließen'));
          expect(find.text('Text öffnen'), findsOneWidget);
          expect(
            fixture.requests.where((request) => request.method != 'GET'),
            isEmpty,
          );
          expect(tester.takeException(), isNull);
        },
      );
    }
  }

  testWidgets('An old preview cannot open after a new session', (tester) async {
    final fixture = material.Fixture();
    await fixture.mount(tester);
    final preview = find.byKey(const ValueKey('material-photo-preview'));
    final ink = find
        .ancestor(of: preview, matching: find.byType(InkWell))
        .first;
    final oldAction = tester.widget<InkWell>(ink).onTap!;
    final previousReads = fixture.requests.length;
    fixture.state.user = {...fixture.state.user!};
    oldAction();
    await tester.pumpAndSettle();
    expect(find.byTooltip('Foto nach links drehen'), findsNothing);
    expect(fixture.requests.length, previousReads);
    expect(tester.takeException(), isNull);
  });
}
