import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'exams_screen_test.dart' as fixtures;

void emptyWork(fixtures.Fixture fixture) {
  fixture.listOverride = {
    'child_id': 'child',
    'can_manage': true,
    'exams': [],
    'sources': [],
    'has_more': false,
  };
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final size in [const Size(320, 600), const Size(390, 844)]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets('Fachsuche bleibt bei $size und Schrift $scale bedienbar', (
        tester,
      ) async {
        final fixture = fixtures.Fixture();
        emptyWork(fixture);
        fixture.subjectOverride = [
          for (final name in [
            'Biologie',
            'Chemie',
            'Deutsch',
            'Englisch',
            'Geschichte',
            'Mathematik',
            'Physik',
          ])
            {'id': name, 'title': name},
        ];
        await fixture.mount(tester, tab: 'review', size: size, scale: scale);
        await fixtures.tap(tester, find.text('Arbeit hinzufügen'));
        await fixtures.tap(tester, find.text('Fach auswählen'));
        expect(find.widgetWithText(TextField, 'Fach suchen'), findsOneWidget);
        await tester.enterText(
          find.widgetWithText(TextField, 'Fach suchen'),
          'mAtHe',
        );
        await tester.pumpAndSettle();
        expect(find.text('Mathematik'), findsOneWidget);
        expect(find.text('Biologie'), findsNothing);
        await fixtures.tap(tester, find.text('Mathematik'));
        expect(find.text('Mathematik'), findsOneWidget);
        expect(fixture.writes, isEmpty);
        expect(tester.takeException(), isNull);
      });
    }
  }
  testWidgets('Kein Treffer verändert weder Fächer noch Plan', (tester) async {
    final fixture = fixtures.Fixture();
    emptyWork(fixture);
    await fixture.mount(tester, tab: 'review');
    await fixtures.tap(tester, find.text('Arbeit hinzufügen'));
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Fach suchen'),
      'unbekannt',
    );
    await tester.pumpAndSettle();
    expect(find.text('Kein Fach gefunden.'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    await fixtures.tap(tester, find.byTooltip('Fachauswahl schließen'));
    expect(find.text('Fach auswählen'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('Fachsuche bleibt bei Tastatur und Schrift $scale erreichbar', (
      tester,
    ) async {
      final fixture = fixtures.Fixture();
      emptyWork(fixture);
      await fixture.mount(
        tester,
        tab: 'review',
        size: const Size(320, 600),
        scale: scale,
      );
      await fixtures.tap(tester, find.text('Arbeit hinzufügen'));
      await fixtures.tap(tester, find.text('Fach auswählen'));
      await tester.showKeyboard(find.widgetWithText(TextField, 'Fach suchen'));
      tester.view.viewInsets = const FakeViewPadding(bottom: 260);
      addTearDown(tester.view.resetViewInsets);
      await tester.enterText(
        find.widgetWithText(TextField, 'Fach suchen'),
        'Mathe',
      );
      await tester.pumpAndSettle();
      expect(find.text('Mathematik').hitTestable(), findsOneWidget);
      await fixtures.tap(tester, find.text('Mathematik'));
      expect(fixture.writes, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }

  for (final change in ['account', 'family', 'token', 'background']) {
    testWidgets('Fachsuche schließt bei $change ohne Planänderung', (
      tester,
    ) async {
      final fixture = fixtures.Fixture();
      emptyWork(fixture);
      await fixture.mount(tester, tab: 'review');
      await fixtures.tap(tester, find.text('Arbeit hinzufügen'));
      await fixtures.tap(tester, find.text('Fach auswählen'));
      if (change == 'account') {
        fixture.state.user = {...fixture.state.user!, 'id': 'other'};
      }
      if (change == 'family') fixture.state.familyId = 'other';
      if (change == 'token') fixture.state.api.token = 'other';
      if (change == 'background') {
        await fixtures.pause(tester);
      } else {
        fixture.state.refreshState();
      }
      await tester.pumpAndSettle();
      expect(find.widgetWithText(TextField, 'Fach suchen'), findsNothing);
      expect(fixture.writes, isEmpty);
      if (change == 'background') await fixtures.resume(tester);
      expect(tester.takeException(), isNull);
    });
  }
}
