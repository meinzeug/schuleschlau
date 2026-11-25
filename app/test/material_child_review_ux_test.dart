import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'material_confirmed_uncertainties_124_test.dart' as fixture;

void main() {
  for (final size in [const Size(390, 844), const Size(320, 568)]) {
    testWidgets('Unklare Seite wird bei $size an Eltern verwiesen', (
      tester,
    ) async {
      final value = fixture.Fixture();
      value.data['confirmed'] = false;
      value.data['status'] = 'review';
      value.data['uncertainties'] = [fixture.pageWarning];
      await value.mount(tester, size: size, scale: size.width == 320 ? 2 : 1);
      expect(
        find.text(
          'Diese Seite prüfen deine Eltern. Dein Foto ist gespeichert.',
        ),
        findsOneWidget,
      );
      expect(find.text('Stimmt, weiter'), findsNothing);
      expect(find.text('Etwas verbessern'), findsNothing);
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }
}
