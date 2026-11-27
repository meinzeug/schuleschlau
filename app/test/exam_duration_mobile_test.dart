import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'exams_screen_test.dart' as fixtures;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final input in ['', '4', '61', '5', '23', '60']) {
    testWidgets('Lernzeit $input bleibt individuell und wird geprüft', (
      tester,
    ) async {
      final fixture = fixtures.Fixture();
      await fixture.mount(
        tester,
        editor: true,
        size: const Size(320, 600),
        scale: 2,
      );
      await fixtures.tap(tester, find.text('Weiter'));
      await fixtures.tap(tester, find.text('Weiter'));
      final field = find.widgetWithText(TextField, 'Minuten pro Lerntag');
      await tester.ensureVisible(field);
      await tester.enterText(field, input);
      await tester.pump();
      await fixtures.tap(tester, find.text('Weiter'));
      final parsed = int.tryParse(input) ?? 0;
      if (parsed < 5 || parsed > 60) {
        expect(
          find.text('Wähle zwischen 5 und 60 Minuten pro Lerntag.'),
          findsOneWidget,
        );
        expect(find.text('Schritt 3 von 4 · Lerntage'), findsOneWidget);
        expect(fixture.writes, isEmpty);
        await tester.ensureVisible(field);
        await tester.enterText(field, '23');
        await tester.pump();
        await fixtures.tap(tester, find.text('Weiter'));
      }
      await fixtures.tap(tester, find.text('Plan speichern'));
      expect(fixture.writes, hasLength(1));
      final body = jsonDecode(fixture.writes.single.body);
      expect(body['minutes'], parsed < 5 || parsed > 60 ? 23 : parsed);
      expect(body['revision'], 1);
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('Hinweise bleiben bis zur passenden Korrektur sichtbar', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(tester, editor: true, size: const Size(390, 844));
    await fixtures.tap(tester, find.text('Weiter'));
    final count = find.widgetWithText(
      TextField,
      'Aufgaben je Thema und Lerntag',
    );
    await tester.enterText(count, '0');
    await fixtures.tap(tester, find.text('Weiter'));
    const countError = 'Wähle pro Thema zwischen 1 und 50 Aufgaben je Lerntag.';
    expect(find.text(countError), findsOneWidget);
    await tester.enterText(count, '51');
    await tester.pump();
    expect(find.text(countError), findsOneWidget);
    await tester.enterText(count, '5');
    await tester.pump();
    expect(find.text(countError), findsNothing);
    await fixtures.tap(tester, find.text('Weiter'));
    final minutes = find.widgetWithText(TextField, 'Minuten pro Lerntag');
    await tester.ensureVisible(minutes);
    await tester.enterText(minutes, '4');
    await fixtures.tap(tester, find.text('Weiter'));
    const timeError = 'Wähle zwischen 5 und 60 Minuten pro Lerntag.';
    expect(find.text(timeError), findsOneWidget);
    await tester.ensureVisible(minutes);
    await tester.enterText(minutes, '61');
    await tester.pump();
    expect(find.text(timeError), findsOneWidget);
    await tester.enterText(minutes, '30');
    await tester.pump();
    expect(find.text(timeError), findsNothing);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Lerntaghinweis bleibt bei anderer Eingabe bestehen', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(tester, editor: true, size: const Size(390, 844));
    await fixtures.tap(tester, find.text('Weiter'));
    await fixtures.tap(tester, find.text('Weiter'));
    final date = find.byType(InputChip);
    expect(date, findsOneWidget);
    tester.widget<InputChip>(date).onDeleted!();
    await tester.pump();
    await fixtures.tap(tester, find.text('Weiter'));
    const dateError = 'Wähle mindestens einen konkreten Lerntag.';
    expect(find.text(dateError), findsOneWidget);
    final minutes = find.widgetWithText(TextField, 'Minuten pro Lerntag');
    await tester.ensureVisible(minutes);
    await tester.enterText(minutes, '30');
    await tester.pump();
    expect(find.text(dateError), findsOneWidget);
    await fixtures.tap(tester, find.text('Einzelnen Lerntag auswählen'));
    await fixtures.tap(tester, find.text('OK'));
    expect(find.text(dateError), findsNothing);
    expect(find.byType(InputChip), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Lernzeit und Weiter bleiben mit Bildschirmtastatur erreichbar', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(
      tester,
      editor: true,
      size: const Size(320, 600),
      scale: 2,
    );
    await fixtures.tap(tester, find.text('Weiter'));
    await fixtures.tap(tester, find.text('Weiter'));
    final field = find.widgetWithText(TextField, 'Minuten pro Lerntag');
    await tester.ensureVisible(field);
    await tester.showKeyboard(field);
    tester.view.viewInsets = const FakeViewPadding(bottom: 250);
    addTearDown(tester.view.resetViewInsets);
    await tester.pumpAndSettle();
    await tester.ensureVisible(field);
    await tester.enterText(field, '23');
    await tester.pumpAndSettle();
    expect(tester.getRect(field).bottom, lessThanOrEqualTo(350));
    final next = find.widgetWithText(FilledButton, 'Weiter');
    expect(tester.getRect(next).bottom, lessThanOrEqualTo(350));
    await tester.tap(next);
    await tester.pumpAndSettle();
    expect(find.text('Schritt 4 von 4 · Überblick'), findsOneWidget);
    expect(find.textContaining('23 Minuten empfohlen'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });
}
