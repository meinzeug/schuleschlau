import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/material_screen.dart';
import 'package:schulpilot/material_visual_review.dart';

import 'material_confirmed_uncertainties_124_test.dart' as fixture;

void main() {
  testWidgets(
    'Bildbefunde stehen getrennt und erkennbar vorläufig neben der Abschrift',
    (tester) async {
      final page = fixture.Fixture();
      page.data['confirmed'] = false;
      page.data['status'] = 'review';
      page.data['visual_observations'] = [
        {
          'description': 'Drei von sieben Feldern sind markiert.',
          'image_region': {
            'left': 100,
            'top': 200,
            'right': 800,
            'bottom': 500,
          },
          'uncertainty': 'Die Farbe ist schwer zu erkennen.',
        },
      ];
      await page.mount(tester, size: const Size(390, 844));
      expect(find.text('Bilder auf der Seite'), findsOneWidget);
      expect(
        find.text(
          'Prüfe die Bildhinweise am Foto. „Stimmt, weiter“ bestätigt nur den Text. '
          'Bildhinweise werden nicht zum Lernen verwendet.',
        ),
        findsOneWidget,
      );
      expect(
        find.text('Drei von sieben Feldern sind markiert.'),
        findsOneWidget,
      );
      expect(
        find.text('Unsicher: Die Farbe ist schwer zu erkennen.'),
        findsOneWidget,
      );
      final review = tester.widget<MaterialReview>(find.byType(MaterialReview));
      expect(review.data['content'], page.data['content']);
      expect(page.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Fehlende und ungültige Befunde erzeugen keine Anzeige', (
    tester,
  ) async {
    for (final value in [
      null,
      <Object>[],
      'unexpected',
      [
        null,
        42,
        {'description': ''},
      ],
    ]) {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MaterialVisualReview(
              state: fixture.Fixture().state,
              data: {'visual_observations': value},
              onRefresh: () {},
            ),
          ),
        ),
      );
      expect(find.text('Bilder auf der Seite'), findsNothing);
      expect(tester.takeException(), isNull);
    }
  });
}
