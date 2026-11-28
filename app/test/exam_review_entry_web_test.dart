import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'exams_screen_test.dart' as exam;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('written work date is clear and can be removed', (tester) async {
    final fixture = exam.Fixture()
      ..listOverride = {
        'child_id': 'child',
        'can_manage': true,
        'exams': [],
        'sources': [],
        'has_more': false,
      };
    await fixture.mount(tester, tab: 'review', size: const Size(390, 844));
    await exam.tap(tester, find.text('Arbeit hinzufügen'));
    await exam.tap(tester, find.text('Geschrieben am (optional)'));
    await exam.tap(tester, find.text('OK'));
    expect(find.textContaining('Geschrieben am:'), findsOneWidget);
    await exam.tap(tester, find.text('Datum entfernen'));
    expect(find.text('Geschrieben am (optional)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
  });

  testWidgets('child saves a written work after the compact entry', (
    tester,
  ) async {
    final fixture = exam.Fixture()
      ..listOverride = {
        'child_id': 'child',
        'can_manage': true,
        'exams': [],
        'sources': [],
        'has_more': false,
      };
    await fixture.mount(tester, tab: 'review', size: const Size(390, 844));
    await exam.tap(tester, find.text('Arbeit hinzufügen'));
    expect(find.text('Deine geschriebene Arbeit'), findsOneWidget);
    expect(find.textContaining('Schritt 1 von 1'), findsNothing);
    expect(fixture.writes, isEmpty);
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Meine Beispielarbeit',
    );
    await exam.tap(tester, find.text('Fach auswählen'));
    await exam.tap(tester, find.text('Mathematik'));
    await exam.tap(tester, find.text('Arbeit speichern'));
    expect(fixture.writes, hasLength(1));
    final payload = jsonDecode(fixture.writes.single.body);
    expect(payload['purpose'], 'review');
    expect(payload['subject'], 'Mathematik');
    expect(fixture.writes.single.headers['Idempotency-Key'], isNotEmpty);
  });
}
