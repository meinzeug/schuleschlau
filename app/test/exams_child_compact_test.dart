import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/ui.dart';
import 'package:schulpilot/learning_start_illustration.dart';

import 'exams_screen_test.dart' as fixtures;
import 'page_tools_test_helpers.dart' as tools;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final size in [const Size(320, 600), const Size(390, 844)]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets(
        'Leere Arbeiten führen bei $size/$scale zur nächsten Aktion',
        (tester) async {
          final fixture = fixtures.Fixture();
          fixture.listOverride = {
            'child_id': 'child',
            'can_manage': true,
            'exams': [],
            'sources': [],
            'has_more': false,
          };
          await fixture.mount(tester, size: size, scale: scale);
          expect(find.byType(LearningStartIllustration), findsOneWidget);
          expect(find.text('Bereit für deine nächste Arbeit?'), findsOneWidget);
          expect(find.text('Arbeit planen'), findsOneWidget);
          expect(fixture.writes, isEmpty);
          await fixtures.tap(tester, find.text('Nacharbeiten'));
          expect(find.text('Eine Arbeit nacharbeiten'), findsOneWidget);
          expect(find.text('Arbeit hinzufügen'), findsOneWidget);
          expect(fixture.writes, isEmpty);
          await fixtures.tap(tester, find.text('Arbeit hinzufügen'));
          expect(
            find.widgetWithText(TextField, 'Titel der Arbeit'),
            findsOneWidget,
          );
          expect(fixture.writes, isEmpty);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }

  testWidgets('Ohne Änderungsrecht bleibt der leere Zustand ehrlich', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.listOverride = {
      'child_id': 'child',
      'can_manage': false,
      'exams': [],
      'sources': [],
      'has_more': false,
    };
    await fixture.mount(tester);
    expect(find.text('Bereit für deine nächste Arbeit?'), findsOneWidget);
    expect(find.text('Arbeit planen'), findsNothing);
    expect(fixture.writes, isEmpty);
  });

  testWidgets(
    'Weitere geladene Arbeiten werden nicht als leerer Bestand ausgegeben',
    (tester) async {
      final fixture = fixtures.Fixture();
      fixture.listOverride = {
        'child_id': 'child',
        'can_manage': true,
        'exams': [],
        'sources': [],
        'has_more': true,
      };
      await fixture.mount(tester);
      expect(find.text('Bereit für deine nächste Arbeit?'), findsNothing);
      expect(
        find.text(
          'Hier sind noch keine passenden Arbeiten geladen. Lade weitere Arbeiten.',
        ),
        findsOneWidget,
      );
      expect(find.text('Weitere Arbeiten laden'), findsOneWidget);
      expect(fixture.writes, isEmpty);
    },
  );

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

  testWidgets('Lerntagsdetails sind kompakt und berührungsfreundlich', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(tester, selected: 'exam');
    final action = find.widgetWithText(TextButton, 'Mehr zum Lerntag');
    expect(tester.getSize(action).width, lessThan(250));
    expect(tester.getSize(action).height, greaterThanOrEqualTo(48));
    expect(fixture.writes, isEmpty);
  });

  for (final size in [const Size(320, 600), const Size(390, 844)]) {
    testWidgets('Weitere Lerntage bleiben bei ${size.width} erreichbar', (
      tester,
    ) async {
      final fixture = fixtures.Fixture();
      (fixture.details['sessions'] as List).add({
        'id': 'session2',
        'date': '2027-01-21',
        'minutes': 15,
        'topics': [
          {'id': 'topic2', 'label': 'Wasser', 'question_count': 3},
        ],
        'status': 'stale',
        'requested_questions': 3,
        'planned_rounds': 1,
        'completed_rounds': 0,
        'rounds': [],
      });
      await fixture.mount(tester, selected: 'exam', size: size, scale: 2);
      expect(find.text('Wasser'), findsNothing);
      expect(
        find.text('Ein weiterer Lerntag braucht deine Aufmerksamkeit.'),
        findsOneWidget,
      );
      expect(find.text('Lernrunde starten'), findsOneWidget);
      expect(fixture.writes, isEmpty);
      await fixtures.tap(tester, find.text('Weitere Lerntage (1)'));
      expect(find.text('Wasser'), findsOneWidget);
      expect(
        find.text('Quelle geändert · Vorbereitung prüfen'),
        findsOneWidget,
      );
      expect(fixture.writes, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Unbekannter Lerntag täuscht keinen Abschluss vor', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(tester, selected: 'exam', sessionId: 'missing');
    expect(
      find.text('Dieser Lerntag ist nicht verfügbar. Wähle einen anderen.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Alle geplanten Sitzungen sind bearbeitet'),
      findsNothing,
    );
    expect(find.text('Weitere Lerntage (1)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
  });

  testWidgets('Leerer Fehlertext erfindet keine Warnung', (tester) async {
    final fixture = fixtures.Fixture();
    (fixture.details['sessions'] as List).add({
      'id': 'session2',
      'date': '2027-01-21',
      'minutes': 15,
      'topics': [],
      'status': 'planned',
      'requested_questions': 3,
      'rounds': [
        {'id': 'round2', 'error': '  '},
      ],
    });
    await fixture.mount(tester, selected: 'exam');
    expect(
      find.text('Ein weiterer Lerntag braucht deine Aufmerksamkeit.'),
      findsNothing,
    );
    expect(find.text('Weitere Lerntage (1)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
  });

  testWidgets('Eltern sehen weitere Lerntage weiterhin direkt', (tester) async {
    final fixture = fixtures.Fixture(role: 'parent');
    (fixture.details['sessions'] as List).add({
      'id': 'session2',
      'date': '2027-01-21',
      'minutes': 15,
      'topics': [
        {'id': 'topic2', 'label': 'Wasser', 'question_count': 3},
      ],
      'status': 'planned',
      'requested_questions': 3,
      'rounds': [],
    });
    await fixture.mount(tester, selected: 'exam');
    expect(find.text('Wasser · 3 Aufgaben'), findsOneWidget);
    expect(find.text('Weitere Lerntage (1)'), findsNothing);
    expect(fixture.writes, isEmpty);
  });

  testWidgets(
    'Nacharbeit führt mobil zum eigenen Versuch und hält Hilfe bereit',
    (tester) async {
      final fixture = fixtures.Fixture();
      fixture.report['pages'] = [
        {'id': 'page', 'title': 'Beispielfoto', 'confirmed': true},
      ];
      await fixture.mount(
        tester,
        selected: 'exam',
        tab: 'review',
        size: const Size(320, 600),
        scale: 2,
      );
      final field = find.widgetWithText(TextField, 'Dein Verbesserungsversuch');
      await tester.ensureVisible(field);
      await tester.enterText(field, 'Mein eigener Versuch');
      await tester.pump();
      expect(find.text('Meinen Versuch ansehen lassen'), findsOneWidget);
      expect(find.text('Kleiner Hinweis'), findsOneWidget);
      expect(find.text('Mit passendem Heftstoff üben'), findsNothing);
      expect(find.text('Beispielfoto · Bestätigt · ansehen'), findsNothing);
      expect(fixture.writes, isEmpty);

      await fixtures.tap(tester, find.text('Fotos der Arbeit'));
      expect(find.text('Beispielfoto · Bestätigt · ansehen'), findsOneWidget);
      expect(fixture.writes, isEmpty);

      await fixtures.tap(tester, find.text('Mehr Hilfe'));
      expect(find.text('Erklärung'), findsOneWidget);
      expect(find.text('Mit passendem Heftstoff üben'), findsOneWidget);
      expect(
        tester.widget<TextField>(field).controller!.text,
        'Mein eigener Versuch',
      );
      expect(fixture.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );
}
