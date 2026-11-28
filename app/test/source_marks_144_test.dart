import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image/image.dart' as image;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/learning_content.dart';
import 'package:schulpilot/math_content.dart';
import 'package:schulpilot/notebook_photo.dart';
import 'package:schulpilot/ui.dart';

void main() {
  for (final width in [320.0, 1024.0]) {
    testWidgets('child can open marked photo while reading at $width px', (
      tester,
    ) async {
      tester.view.physicalSize = Size(width, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final semantics = tester.ensureSemantics();
      var requests = 0;
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((request) async {
                  requests++;
                  return http.Response.bytes(
                    image.encodePng(image.Image(width: 4, height: 4)),
                    200,
                  );
                }),
              ),
            )
            ..user = {'id': 'synthetic', 'role': 'child'}
            ..familyId = 'family';
      const text = '2/3 Minute = 60 40 Sekunden';
      final block = {
        'kind': 'paragraph',
        'text': text,
        'image_region': {'x': 0, 'y': 0, 'width': 1, 'height': 1},
        'annotations': [
          {'kind': 'crossout', 'quote': '60'},
          {'kind': 'correction', 'quote': '40'},
        ],
      };
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: LearningContent(
                text,
                blocks: [block],
                compactSourceFigures: true,
                figureBuilder: (_, _) => SizedBox(
                  height: 280,
                  child: NotebookPhoto(
                    state,
                    materialId: 'page',
                    figureIndex: 0,
                    revision: 1,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
      expect(find.text('Gestrichen im Foto'), findsOneWidget);
      expect(find.text('Ergänzt im Foto'), findsOneWidget);
      expect(requests, 0);
      expect(find.byType(NotebookPhoto), findsNothing);
      final tile = find.widgetWithText(
        TextButton,
        'Ausschnitt im Foto ansehen',
      );
      expect(tester.getSize(tile).height, greaterThanOrEqualTo(48));
      final node = tester.getSemantics(tile);
      expect(node.getSemanticsData().hasAction(SemanticsAction.tap), isTrue);
      expect(
        node.getSemanticsData().flagsCollection.isExpanded,
        Tristate.isFalse,
      );
      await tester.tap(tile);
      await tester.pumpAndSettle();
      expect(requests, 1);
      expect(find.byType(NotebookPhoto), findsOneWidget);
      expect(
        tester
            .getSemantics(find.byKey(const ValueKey('source-figure-toggle')))
            .getSemanticsData()
            .flagsCollection
            .isExpanded,
        Tristate.isTrue,
      );
      await tester.ensureVisible(
        find.text('Wörtliche Abschrift mit allen Einträgen'),
      );
      await tester.tap(find.text('Wörtliche Abschrift mit allen Einträgen'));
      await tester.pumpAndSettle();
      expect(
        find.byWidgetPredicate((w) => w is MathText && w.data == text),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
      semantics.dispose();
    });
  }
  testWidgets('parent view still shows the marked photo directly', (
    tester,
  ) async {
    const text = 'Falsch richtig';
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: LearningContent(
            text,
            blocks: [
              {
                'kind': 'paragraph',
                'text': text,
                'image_region': {'x': 0},
                'annotations': [
                  {'kind': 'crossout', 'quote': 'Falsch'},
                  {'kind': 'correction', 'quote': 'richtig'},
                ],
              },
            ],
            figureBuilder: (_, _) => const Text('Fotoausschnitt'),
          ),
        ),
      ),
    );
    expect(find.text('Fotoausschnitt'), findsOneWidget);
    expect(find.text('Ausschnitt im Foto ansehen'), findsNothing);
    expect(find.text('Gestrichen im Foto'), findsOneWidget);
    expect(find.text('Ergänzt im Foto'), findsOneWidget);
  });
  testWidgets(
    'highlights keep the sentence readable without hiding corrections',
    (tester) async {
      const text = 'Mara liest ein Buch.';
      final block = {
        'kind': 'paragraph',
        'text': text,
        'annotations': [
          {'kind': 'highlight', 'quote': 'Mara', 'color': 'red'},
          {'kind': 'highlight', 'quote': 'liest', 'color': 'blue'},
        ],
      };
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: LearningContent(text, blocks: [block]),
            ),
          ),
        ),
      );
      expect(find.text(text), findsOneWidget);
      expect(find.text('Markierungen im Foto'), findsNothing);
      await tester.tap(find.text('Hervorhebungen im Foto'));
      await tester.pumpAndSettle();
      expect(find.text('Mara'), findsOneWidget);
      expect(find.text('liest'), findsOneWidget);
      expect(block['text'], text);
      expect(tester.takeException(), isNull);
    },
  );
  for (final width in [320.0, 1024.0]) {
    testWidgets(
      'literal correction cards distinguish repeated numbers on $width px',
      (tester) async {
        tester.view.physicalSize = Size(width, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        const text =
            '1) 2/3 Minute = 60 40 Sekunden\nEine Minute hat 60 Sekunden.';
        final block = {
          'kind': 'paragraph',
          'text': text,
          'annotations': [
            {'kind': 'crossout', 'quote': '60', 'color': 'red'},
            {'kind': 'correction', 'quote': '40', 'color': 'red'},
          ],
        };
        await tester.pumpWidget(
          MaterialApp(
            theme: appTheme(),
            home: Scaffold(
              body: SingleChildScrollView(
                child: LearningContent(text, blocks: [block]),
              ),
            ),
          ),
        );
        expect(find.text('Gestrichen im Foto'), findsOneWidget);
        expect(find.text('Ergänzt im Foto'), findsOneWidget);
        final crossed = tester.widget<MathText>(
          find.byWidgetPredicate((w) => w is MathText && w.data == '60'),
        );
        expect(crossed.style!.decoration, TextDecoration.lineThrough);
        expect(
          find.byWidgetPredicate((w) => w is MathText && w.data == text),
          findsNothing,
        );
        expect(
          block['text'],
          text,
        ); // No source mutation or invented correct equation.
        await tester.tap(find.text('Wörtliche Abschrift mit allen Einträgen'));
        await tester.pumpAndSettle();
        expect(
          find.byWidgetPredicate((w) => w is MathText && w.data == text),
          findsOneWidget,
        );
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets('a partially unreadable marked sentence remains visible', (
    tester,
  ) async {
    const text = 'She [unleserlich durchgestrichen] a nice cake.';
    final block = {
      'kind': 'paragraph',
      'text': text,
      'annotations': [
        {'kind': 'crossout', 'quote': '[unleserlich durchgestrichen]'},
      ],
    };
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: SingleChildScrollView(
            child: LearningContent(text, blocks: [block]),
          ),
        ),
      ),
    );
    expect(find.text('Abschrift mit unleserlicher Stelle'), findsOneWidget);
    expect(
      find.byWidgetPredicate((w) => w is MathText && w.data == text),
      findsOneWidget,
    );
    expect(find.text('Gestrichen im Foto'), findsOneWidget);
    expect(block['text'], text);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'ordinary ink and stale annotations do not become correction cards',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: LearningContent(
              'Neue Fassung',
              blocks: [
                {
                  'kind': 'paragraph',
                  'text': 'Alte Fassung',
                  'annotations': [
                    {'kind': 'crossout', 'quote': 'Alte'},
                  ],
                },
              ],
            ),
          ),
        ),
      );
      expect(find.text('Markierungen im Foto'), findsNothing);
      expect(find.text('Neue Fassung'), findsOneWidget);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: LearningContent(
              'Mila liest.',
              blocks: [
                {
                  'kind': 'paragraph',
                  'text': 'Mila liest.',
                  'annotations': [
                    {'kind': 'ink', 'quote': 'Mila liest.', 'color': 'blue'},
                  ],
                },
              ],
            ),
          ),
        ),
      );
      expect(find.text('Markierungen im Foto'), findsNothing);
      expect(find.text('Mila liest.'), findsOneWidget);
    },
  );
}
