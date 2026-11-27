// Synthetic words and a mock transport: no provider calls or child data.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'vocabulary_test.dart' as fixture;

void main() {
  for (final width in [320.0, 390.0]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets(
        'one word has two clear fields and an explicit review at $width/$scale',
        (tester) async {
          final calls = <http.Request>[];
          await fixture.open(
            tester,
            calls,
            width: width,
            textScale: scale,
            openTools: false,
            cards: false,
          );
          await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
          final word = find.byKey(const ValueKey('vocabulary-single-word'));
          final meaning = find.byKey(
            const ValueKey('vocabulary-single-meaning'),
          );
          expect(word, findsOneWidget);
          expect(meaning, findsOneWidget);
          expect(find.text('Lernsprache bestätigen'), findsOneWidget);
          expect(find.text('Sammlung: Meine Schulwörter'), findsOneWidget);
          expect(find.text('Wörter speichern in'), findsNothing);
          await fixture.tap(tester, find.text('Wort prüfen'));
          expect(
            find.text('Gib ein Wort und seine Bedeutung ein.'),
            findsOneWidget,
          );
          expect(calls.where((r) => r.method == 'POST'), isEmpty);
          await tester.enterText(word, 'cat');
          await tester.enterText(meaning, 'Katze');
          await fixture.tap(tester, find.text('Wort prüfen'));
          final sent = calls.where((r) => r.method == 'POST').toList();
          expect(sent, hasLength(1));
          expect(sent.single.url.path, endsWith('/imports'));
          final body = jsonDecode(sent.single.body);
          expect(body['target_locale'], 'en-GB');
          expect(body['language_confirmed'], isTrue);
          expect(body['pairs'], [
            {'word': 'cat', 'meaning': 'Katze'},
          ]);
          expect(find.text('Stimmt dieses Wort?'), findsOneWidget);
          expect(find.text('Wortvorschläge durchsuchen'), findsNothing);
          expect(find.text('Zum nächsten offenen Wortpaar'), findsNothing);
          await fixture.tap(tester, find.text('Wort speichern'));
          expect(calls.where((r) => r.method == 'POST'), hasLength(1));
          expect(
            find.textContaining('Wähle mindestens ein Wort'),
            findsOneWidget,
          );
          await fixture.tap(tester, find.text('Stimmt'));
          expect(calls.where((r) => r.method == 'POST'), hasLength(1));
          await fixture.tap(tester, find.text('Wort speichern'));
          final finalWrites = calls.where((r) => r.method == 'POST').toList();
          expect(finalWrites, hasLength(2));
          expect(
            finalWrites.last.url.path,
            endsWith('/imports/import/confirm'),
          );
          expect(
            jsonDecode(finalWrites.last.body)['pairs'].single['word'],
            'cat',
          );
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
  testWidgets(
    'switching to a list retains both partial entries without sending',
    (tester) async {
      final calls = <http.Request>[];
      await fixture.open(tester, calls, openTools: false, cards: false);
      await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-word')),
        'bird',
      );
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-meaning')),
        'Vogel',
      );
      await fixture.tap(tester, find.text('Mehrere Wörter oder Text'));
      final field = find.byWidgetPredicate(
        (w) => w is TextField && w.minLines == 4,
      );
      expect(tester.widget<TextField>(field).controller!.text, 'bird = Vogel');
      expect(calls.where((r) => r.method == 'POST'), isEmpty);
    },
  );
  testWidgets(
    'missing collection name reopens its field without losing the word',
    (tester) async {
      final calls = <http.Request>[];
      await fixture.open(tester, calls, openTools: false, cards: false);
      await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
      await fixture.tap(
        tester,
        find.byKey(const ValueKey('vocabulary-collection-toggle')),
      );
      final collection = find.byWidgetPredicate(
        (w) => w is TextField && w.decoration?.labelText == 'Sammlung',
      );
      await tester.enterText(collection, '');
      await fixture.tap(
        tester,
        find.byKey(const ValueKey('vocabulary-collection-toggle')),
      );
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-word')),
        'bird',
      );
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-meaning')),
        'Vogel',
      );
      await fixture.tap(tester, find.text('Wort prüfen'));
      expect(find.text('Gib deiner Sammlung einen Namen.'), findsOneWidget);
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('vocabulary-single-word')),
            )
            .controller!
            .text,
        'bird',
      );
      expect(calls.where((r) => r.method == 'POST'), isEmpty);
    },
  );
  testWidgets('parent retains the existing list entry form', (tester) async {
    final calls = <http.Request>[];
    await fixture.open(
      tester,
      calls,
      parent: true,
      manage: true,
      openTools: false,
      cards: false,
    );
    await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
    expect(find.byKey(const ValueKey('vocabulary-single-word')), findsNothing);
    expect(find.text('Wörter übernehmen aus'), findsOneWidget);
    expect(find.text('Wortpaare prüfen'), findsOneWidget);
    expect(calls.where((r) => r.method == 'POST'), isEmpty);
  });
}
