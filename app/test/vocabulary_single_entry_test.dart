// Synthetic words and a mock transport: no provider calls or child data.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
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
          expect(find.text('Neue Sammlung'), findsOneWidget);
          expect(find.text('Meine Schulwörter'), findsOneWidget);
          for (final labelText in ['Neue Sammlung', 'Meine Schulwörter']) {
            final label = find.descendant(
              of: find.text(labelText),
              matching: find.byType(RichText),
            );
            final rendered = tester.renderObject<RenderParagraph>(label);
            expect(
              rendered.didExceedMaxLines,
              isFalse,
              reason:
                  'size=${rendered.size}, constraints=${rendered.constraints}, maxLines=${rendered.maxLines}',
            );
          }
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
  for (final caseData in [
    (total: 1, duplicates: false, expectedId: 'default'),
    (total: 2, duplicates: false, expectedId: null),
    (total: 2, duplicates: true, expectedId: null),
  ]) {
    testWidgets(
      'default collection is reused only when unambiguous: $caseData',
      (tester) async {
        final calls = <http.Request>[];
        final listing = fixture.listing();
        listing['supports_collections'] = true;
        listing['collections_total'] = caseData.total;
        listing['collections'] = [
          {
            'id': 'default',
            'title': 'Meine Schulwörter',
            'target_locale': 'en-GB',
          },
          if (caseData.duplicates)
            {
              'id': 'other',
              'title': 'Meine Schulwörter',
              'target_locale': 'en-GB',
            },
        ];
        await fixture.open(
          tester,
          calls,
          openTools: false,
          cards: false,
          wordListing: listing,
        );
        await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
        expect(
          find.text(caseData.expectedId == null ? 'Neue Sammlung' : 'Sammlung'),
          findsOneWidget,
        );
        expect(find.text('Meine Schulwörter'), findsOneWidget);
        await tester.enterText(
          find.byKey(const ValueKey('vocabulary-single-word')),
          'bird',
        );
        await tester.enterText(
          find.byKey(const ValueKey('vocabulary-single-meaning')),
          'Vogel',
        );
        await fixture.tap(tester, find.text('Wort prüfen'));
        final post = calls.singleWhere((r) => r.method == 'POST');
        expect(jsonDecode(post.body)['collection_id'], caseData.expectedId);
      },
    );
  }
  testWidgets(
    'retry preserves the suggested collection and original request key',
    (tester) async {
      final calls = <http.Request>[];
      final listing = fixture.listing()
        ..['supports_collections'] = true
        ..['collections_total'] = 1
        ..['collections'] = [
          {
            'id': 'default',
            'title': 'Meine Schulwörter',
            'target_locale': 'en-GB',
          },
        ];
      await fixture.open(
        tester,
        calls,
        openTools: false,
        cards: false,
        respond: (request) async {
          if (request.method == 'POST' &&
              request.url.path.endsWith('/imports')) {
            return http.Response(
              '{"detail":"Antwort unterwegs verloren"}',
              503,
              headers: {'content-type': 'application/json'},
            );
          }
          if (request.url.path.endsWith('/imports')) {
            return fixture.reply({'imports': []});
          }
          return fixture.reply(listing);
        },
      );
      await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-word')),
        'bird',
      );
      await tester.enterText(
        find.byKey(const ValueKey('vocabulary-single-meaning')),
        'Vogel',
      );
      await fixture.tap(tester, find.text('Wort prüfen'));
      await fixture.tap(tester, find.byTooltip('Wörter hinzufügen'));
      expect(
        tester
            .widget<TextField>(
              find.byKey(const ValueKey('vocabulary-single-word')),
            )
            .controller!
            .text,
        'bird',
      );
      await fixture.tap(tester, find.text('Wort prüfen'));
      final posts = calls.where((r) => r.method == 'POST').toList();
      expect(posts, hasLength(2));
      expect(jsonDecode(posts.first.body)['collection_id'], 'default');
      expect(posts.first.body, posts.last.body);
      expect(
        posts.first.headers['Idempotency-Key'] ??
            posts.first.headers['idempotency-key'],
        posts.last.headers['Idempotency-Key'] ??
            posts.last.headers['idempotency-key'],
      );
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
