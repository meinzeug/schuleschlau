import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/ui.dart';

import 'exams_screen_test.dart' as fixtures;
import 'page_tools_test_helpers.dart' as tools;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('Kind sieht den nächsten Schritt vor zusätzlichen Plandetails', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    final session = (fixture.details['sessions'] as List).first as Map;
    session['status'] = 'stale';
    (session['rounds'] as List).first['error'] =
        'Beispiel: Bitte erneut versuchen';
    await fixture.mount(
      tester,
      selected: 'exam',
      size: const Size(320, 600),
      scale: 2,
    );
    expect(find.text('Brüche'), findsOneWidget);
    expect(find.text('Quelle geändert · Vorbereitung prüfen'), findsOneWidget);
    expect(find.text('Beispiel: Bitte erneut versuchen'), findsOneWidget);
    expect(find.text('0 von 2 Runden bearbeitet'), findsNothing);
    final start = find.widgetWithText(ActionButton, 'Lernrunde starten');
    expect(start, findsOneWidget);
    expect(
      tester.getTopLeft(start).dy,
      lessThan(tester.getTopLeft(find.text('Mehr zum Lerntag')).dy),
    );
    await fixtures.tap(tester, find.text('Mehr zum Lerntag'));
    expect(find.text('0 von 2 Runden bearbeitet'), findsOneWidget);
    await tools.openPageTools(tester, 'exam-plan-details');
    expect(find.text('1 Lerntag geplant'), findsOneWidget);
    expect(find.text('15 Min. empfohlen'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Gespeicherte Runde bleibt die klare Hauptaktion', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    final session = (fixture.details['sessions'] as List).first as Map;
    final round = (session['rounds'] as List).first as Map;
    round['unit_id'] = 'saved';
    round['unit_status'] = 'paused';
    await fixture.mount(tester, selected: 'exam');
    expect(find.text('Gespeicherte Runde fortsetzen'), findsOneWidget);
    expect(find.text('Lernrunde starten'), findsNothing);
    expect(fixture.writes, isEmpty);
  });
}
