// Synthetic vocabulary only. Opening or adjusting the dialog must not start a round.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'vocabulary_test.dart' as fixture;

void main() {
  for (final width in [320.0, 390.0]) {
    testWidgets(
      'word round has one clear start with optional settings at $width',
      (tester) async {
        final calls = <http.Request>[];
        await fixture.open(
          tester,
          calls,
          width: width,
          openTools: false,
          cards: false,
        );
        await fixture.tap(tester, find.text('Wörter üben'));
        expect(
          find.text('Aus allen Sammlungen dieser Sprache'),
          findsOneWidget,
        );
        expect(
          find.text('Lies die Bedeutung und schreibe das Wort selbst.'),
          findsOneWidget,
        );
        expect(
          find.text('Bis zu 10 Wörter. Sind weniger verfügbar, übst du diese.'),
          findsOneWidget,
        );
        expect(
          find.text('Wörter schreiben · Deutsch in die Lernsprache'),
          findsOneWidget,
        );
        expect(
          find.widgetWithText(FilledButton, 'Runde beginnen'),
          findsOneWidget,
        );
        expect(find.byKey(const ValueKey('word-mode-spelling')), findsNothing);
        expect(find.text('Zusätzliche Runde'), findsNothing);
        expect(calls.every((request) => request.method == 'GET'), isTrue);
        await fixture.tap(tester, find.text('Runde beginnen'));
        final request = calls.singleWhere(
          (request) => request.url.path.endsWith('/rounds'),
        );
        final body = jsonDecode(request.body);
        expect(body['skill'], 'spelling');
        expect(body['direction'], 'de_to_target');
        expect(body['count'], 10);
        expect(body['voluntary'], false);
        expect(request.headers['Idempotency-Key'], isNotEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('the simple start fits a short phone with large text', (
    tester,
  ) async {
    final calls = <http.Request>[];
    await fixture.open(
      tester,
      calls,
      width: 320,
      textScale: 2,
      openTools: false,
      cards: false,
    );
    tester.view.physicalSize = const Size(320, 600);
    await tester.pumpAndSettle();
    await fixture.tap(tester, find.text('Wörter üben'));
    expect(
      find.widgetWithText(FilledButton, 'Runde beginnen').hitTestable(),
      findsOneWidget,
    );
    expect(find.text('Übung anpassen'), findsOneWidget);
    expect(calls.every((request) => request.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'optional settings retain selected mode, size and listening notice',
    (tester) async {
      final calls = <http.Request>[];
      await fixture.open(tester, calls, openTools: false, cards: false);
      await fixture.tap(tester, find.text('Wörter üben'));
      await fixture.tap(tester, find.text('Übung anpassen'));
      for (final mode in ['spelling', 'recognition', 'recall', 'listening']) {
        expect(find.byKey(ValueKey('word-mode-$mode')), findsOneWidget);
      }
      await fixture.tap(
        tester,
        find.byKey(const ValueKey('word-mode-listening')),
      );
      expect(find.textContaining('passende Gerätestimme'), findsOneWidget);
      await fixture.tap(tester, find.byType(DropdownButtonFormField<int>));
      await fixture.tap(tester, find.text('5 Vokabeln').last);
      await fixture.tap(tester, find.text('Zusätzliche Runde'));
      await fixture.tap(tester, find.text('Übung anpassen'));
      expect(
        find.text('Bis zu 5 Wörter. Sind weniger verfügbar, übst du diese.'),
        findsOneWidget,
      );
      expect(find.textContaining('auch geübte Wörter'), findsOneWidget);
      expect(find.textContaining('passende Gerätestimme'), findsOneWidget);
      expect(calls.every((request) => request.method == 'GET'), isTrue);
      await fixture.tap(tester, find.text('Runde beginnen'));
      final request = calls.singleWhere(
        (request) => request.url.path.endsWith('/rounds'),
      );
      final body = jsonDecode(request.body);
      expect(body['skill'], 'listening');
      expect(body['direction'], 'target_to_de');
      expect(body['count'], 5);
      expect(body['voluntary'], true);
      expect(tester.takeException(), isNull);
    },
  );
}
