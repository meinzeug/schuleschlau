import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
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

  for (final role in ['child', 'parent']) {
    testWidgets('Fehlende Heftseiten verständlich für $role erklären', (
      tester,
    ) async {
      final fixture = fixtures.Fixture(role: role);
      fixture.listOverride = {
        'child_id': 'child',
        'can_manage': true,
        'exams': [],
        'sources': [],
        'has_more': false,
      };
      await fixture.mount(tester, size: const Size(390, 844));
      await fixtures.tap(tester, find.text('Arbeit planen'));
      expect(find.textContaining('fehlen geprüfte Heftseiten'), findsNothing);
      await tester.enterText(
        find.widgetWithText(TextField, 'Titel der Arbeit'),
        'Mathearbeit',
      );
      await fixtures.tap(tester, find.text('Fach auswählen'));
      await fixtures.tap(tester, find.text('Mathematik').last);
      await fixtures.tap(tester, find.text('Weiter'));
      expect(
        find.text(
          role == 'child'
              ? 'Hier sind keine geprüften Seiten für dieses Fach geladen. Fotografiere deine Seiten. Falls eine Prüfung offen ist, helfen deine Eltern.'
              : 'Hier sind keine bestätigten Seiten für dieses Fach geladen. Ergänze oder bestätige passende Seiten im Hefter.',
        ),
        findsOneWidget,
      );
      expect(fixture.writes, isEmpty);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Elternhinweis bleibt bei großer Schrift erreichbar', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.listOverride = {
      'child_id': 'child',
      'can_manage': true,
      'exams': [],
      'sources': [],
      'has_more': false,
    };
    await fixture.mount(tester, size: const Size(320, 600), scale: 2);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    final notice = find.text(
      'Hier sind keine geprüften Seiten für dieses Fach geladen. Fotografiere deine Seiten. Falls eine Prüfung offen ist, helfen deine Eltern.',
    );
    await tester.ensureVisible(notice);
    await tester.pumpAndSettle();
    expect(notice, findsOneWidget);
    final bounds = tester.getRect(notice);
    expect(bounds.top, greaterThanOrEqualTo(0));
    await Scrollable.ensureVisible(tester.element(notice), alignment: 1);
    await tester.pumpAndSettle();
    expect(tester.getRect(notice).bottom, lessThanOrEqualTo(600));
    expect(tester.takeException(), isNull);
    expect(fixture.writes, isEmpty);
  });

  testWidgets('Kind bekommt bei fehlendem Thema Hilfe statt Prüfauftrag', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.listOverride = {
      'child_id': 'child',
      'can_manage': true,
      'exams': [],
      'sources': [],
      'has_more': false,
    };
    await fixture.mount(tester, size: const Size(390, 844));
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.text(
        'Hier sind keine geprüften Seiten für dieses Fach geladen. Fotografiere deine Seiten. Falls eine Prüfung offen ist, helfen deine Eltern.',
      ),
      findsOneWidget,
    );
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsNothing);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Kind wählt ein Thema aus den geprüften Heftseiten', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.listOverride = {
      'child_id': 'child',
      'can_manage': true,
      'exams': [],
      'sources': [fixtures.source()],
      'has_more': false,
    };
    await fixture.mount(tester, size: const Size(390, 844));
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    await fixtures.tap(tester, find.text('Thema aus dem Heft wählen (0/8)'));
    expect(find.text('Wähle ein Thema aus deinem Heft'), findsOneWidget);
    await fixtures.tap(tester, find.text('Brüche').last);
    expect(find.text('Thema aus dem Heft wählen (1/8)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Seiten eines anderen Fachs werden nicht als Themen angeboten', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.subjectOverride = [
      {'id': 'biology', 'title': 'Biologie'},
    ];
    fixture.listOverride = {
      'child_id': 'child',
      'can_manage': true,
      'exams': [],
      'sources': [fixtures.source()],
      'has_more': false,
    };
    await fixture.mount(tester, size: const Size(390, 844));
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Bioarbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Biologie').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.textContaining('Hier sind keine geprüften Seiten'),
      findsOneWidget,
    );
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsNothing);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Weitere Heftseiten laden ohne gewählte Themen zu verlieren', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.sourceHandler = (request) async {
      final cursor = request.url.queryParameters['cursor'];
      return fixtures.reply({
        'items': [
          {
            ...fixtures.source(),
            'id': cursor == null ? 'a' * 32 : 'b' * 32,
            'topic': cursor == null ? 'Brüche' : 'Vielfache',
          },
        ],
        'has_more': cursor == null,
        'next_cursor': cursor == null ? 'a' * 32 : null,
      });
    };
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    await fixtures.tap(tester, find.text('Thema aus dem Heft wählen (0/8)'));
    await fixtures.tap(tester, find.text('Brüche').last);
    await fixtures.tap(tester, find.text('Weitere Heftseiten laden'));
    expect(find.text('Brüche'), findsOneWidget);
    await fixtures.tap(tester, find.text('Thema aus dem Heft wählen (1/8)'));
    await fixtures.tap(tester, find.text('Vielfache').last);
    expect(find.text('Brüche'), findsOneWidget);
    expect(find.text('Vielfache'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Auch eine leere Zwischenportion kann weitergeladen werden', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.sourceHandler = (request) async {
      final next = request.url.queryParameters['cursor'] != null;
      return fixtures.reply({
        'items': next ? [fixtures.source()] : [],
        'has_more': !next,
        'next_cursor': next ? null : 'a' * 32,
      });
    };
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Arbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.textContaining('Hier sind keine geprüften Seiten'),
      findsNothing,
    );
    await fixtures.tap(tester, find.text('Weitere Heftseiten laden'));
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Ein Ladefehler lässt sich bewusst erneut lesen', (tester) async {
    final fixture = fixtures.Fixture();
    var count = 0;
    fixture.sourceHandler = (request) async => ++count == 1
        ? fixtures.reply({'detail': 'Künstlicher Fehler'}, 503)
        : fixtures.reply({
            'items': [fixtures.source()],
            'has_more': false,
            'next_cursor': null,
          });
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.text('Die Heftseiten konnten nicht geladen werden.'),
      findsOneWidget,
    );
    expect(count, 1);
    await fixtures.tap(tester, find.text('Heftseiten neu laden'));
    expect(count, 2);
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Eine unvollständige Serverantwort gilt nicht als leeres Heft', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.sourceHandler = (_) async => fixtures.reply({'items': []});
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Arbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.text('Die Heftseiten konnten nicht geladen werden.'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Hier sind keine geprüften Seiten'),
      findsNothing,
    );
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Älteres Backend zeigt begrenzte vorhandene Seiten', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.sourceHandler = (_) async =>
        fixtures.reply({'detail': 'Nicht gefunden'}, 404);
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Mathearbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.text('Hier siehst du die zuletzt geladenen Seiten.'),
      findsOneWidget,
    );
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsOneWidget);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Alte Vorschau erscheint bei entzogenem Zugriff nicht erneut', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    await fixture.mount(tester);
    fixture.sourceHandler = (_) async =>
        fixtures.reply({'detail': 'Kind nicht gefunden.'}, 404);
    fixture.examListHandler = (_) async =>
        fixtures.reply({'detail': 'Kind nicht gefunden.'}, 404);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Arbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Weiter'));
    expect(
      find.text('Die Heftseiten konnten nicht geladen werden.'),
      findsOneWidget,
    );
    expect(
      find.text('Hier siehst du die zuletzt geladenen Seiten.'),
      findsNothing,
    );
    expect(find.text('Thema aus dem Heft wählen (0/8)'), findsNothing);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Verspätete Seiten des alten Fachs erscheinen nicht im neuen', (
    tester,
  ) async {
    final fixture = fixtures.Fixture();
    fixture.subjectOverride = [
      {'id': 'math', 'title': 'Mathematik'},
      {'id': 'biology', 'title': 'Biologie'},
    ];
    final pending = Completer<http.Response>();
    fixture.sourceHandler = (request) =>
        request.url.queryParameters['subject'] == 'Mathematik'
        ? pending.future
        : Future.value(
            fixtures.reply({
              'items': [],
              'has_more': false,
              'next_cursor': null,
            }),
          );
    await fixture.mount(tester);
    await fixtures.tap(tester, find.text('Arbeit planen'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Titel der Arbeit'),
      'Arbeit',
    );
    await fixtures.tap(tester, find.text('Fach auswählen'));
    await fixtures.tap(tester, find.text('Mathematik').last);
    await tester.tap(find.text('Weiter'));
    await tester.pump();
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.tap(find.text('Zurück'));
    await tester.pumpAndSettle();
    await fixtures.tap(tester, find.text('Mathematik').last);
    await fixtures.tap(tester, find.text('Biologie').last);
    await fixtures.tap(tester, find.text('Weiter'));
    pending.complete(
      fixtures.reply({
        'items': [fixtures.source()],
        'has_more': false,
        'next_cursor': null,
      }),
    );
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Hier sind keine geprüften Seiten'),
      findsOneWidget,
    );
    expect(find.text('Brüche'), findsNothing);
    expect(fixture.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'Unterbrochenes Laden kann nach Rückkehr erneut gestartet werden',
    (tester) async {
      final fixture = fixtures.Fixture();
      final pending = Completer<http.Response>();
      var requests = 0;
      fixture.sourceHandler = (_) => ++requests == 1
          ? pending.future
          : Future.value(
              fixtures.reply({
                'items': [fixtures.source()],
                'has_more': false,
                'next_cursor': null,
              }),
            );
      await fixture.mount(tester);
      await fixtures.tap(tester, find.text('Arbeit planen'));
      await tester.enterText(
        find.widgetWithText(TextField, 'Titel der Arbeit'),
        'Arbeit',
      );
      await fixtures.tap(tester, find.text('Fach auswählen'));
      await fixtures.tap(tester, find.text('Mathematik').last);
      await tester.tap(find.text('Weiter'));
      await tester.pump();
      await fixtures.pause(tester);
      pending.complete(
        fixtures.reply({
          'items': [fixtures.source()],
          'has_more': false,
          'next_cursor': null,
        }),
      );
      await tester.pump();
      await fixtures.resume(tester);
      await tester.pumpAndSettle();
      expect(find.text('Thema aus dem Heft wählen (0/8)'), findsNothing);
      expect(requests, 1);
      await fixtures.tap(tester, find.text('Arbeit planen'));
      await tester.enterText(
        find.widgetWithText(TextField, 'Titel der Arbeit'),
        'Arbeit',
      );
      await fixtures.tap(tester, find.text('Fach auswählen'));
      await fixtures.tap(tester, find.text('Mathematik').last);
      await fixtures.tap(tester, find.text('Weiter'));
      expect(requests, 2);
      expect(find.text('Thema aus dem Heft wählen (0/8)'), findsOneWidget);
      expect(fixture.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );

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
