import 'dart:async';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'exams_screen_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets(
    'initial backgrounded exam mount loads the actual detail on resume',
    (tester) async {
      await fixture.pause(tester);
      final value = fixture.Fixture();
      await value.mount(tester, selected: 'exam');
      expect(find.text('Bruchtest vorbereiten'), findsNothing);
      await fixture.resume(tester);
      await tester.pumpAndSettle();
      expect(find.text('Bruchtest vorbereiten'), findsOneWidget);
      expect(find.text('Lernrunde starten'), findsOneWidget);
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'interrupted detail reload reauthorizes once resumed and ignores old response',
    (tester) async {
      final value = fixture.Fixture();
      await value.mount(tester, selected: 'exam');
      final delayed = Completer<http.Response>();
      value.listWait = delayed;
      await tester.tap(find.byTooltip('Arbeiten aktualisieren'));
      await tester.pump();
      await fixture.pause(tester);
      value.listWait = null;
      value.details = {
        ...value.details,
        'title': 'Aktueller gespeicherter Plan',
        'revision': 2,
      };
      await fixture.resume(tester);
      await tester.pumpAndSettle();
      expect(find.text('Aktueller gespeicherter Plan'), findsOneWidget);
      delayed.complete(
        fixture.reply({
          'child_id': 'wrong-old-child',
          'exams': [],
          'sources': [],
        }),
      );
      await tester.pumpAndSettle();
      expect(find.text('Aktueller gespeicherter Plan'), findsOneWidget);
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'review shows the actual work title and subject before its photo controls',
    (tester) async {
      final value = fixture.Fixture();
      value.report = {...value.report, 'tasks': []};
      await value.mount(tester, selected: 'exam', tab: 'review');
      expect(find.text('Bruchtest vorbereiten'), findsOneWidget);
      expect(find.text('Mathematik · Klassenarbeit (KA)'), findsOneWidget);
      expect(find.text('Termin noch offen'), findsNothing);
      expect(find.text('Termin offen'), findsNothing);
      expect(
        tester.getTopLeft(find.text('Bruchtest vorbereiten')).dy,
        lessThan(tester.getTopLeft(find.text('Arbeit fotografieren')).dy),
      );
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'a written exam shows its date without suggesting an open appointment',
    (tester) async {
      final value = fixture.Fixture();
      value.details = {...value.details, 'exam_date': '2026-11-28'};
      value.report = {...value.report, 'tasks': []};
      await value.mount(tester, selected: 'exam', tab: 'review');
      expect(find.text('Geschrieben am 28.11.2026'), findsOneWidget);
      expect(find.text('Termin noch offen'), findsNothing);
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('the review list labels an existing date as a writing date', (
    tester,
  ) async {
    final value = fixture.Fixture();
    value.listOverride = {
      'child_id': 'child',
      'can_manage': true,
      'exams': [
        {...fixture.exam(purpose: 'review'), 'exam_date': '2026-11-28'},
      ],
      'sources': [],
      'has_more': false,
    };
    await value.mount(tester, tab: 'review');
    expect(find.text('Geschrieben am 28.11.2026'), findsOneWidget);
    expect(find.text('Termin offen'), findsNothing);
    expect(value.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'the review list does not call an omitted writing date an open appointment',
    (tester) async {
      final value = fixture.Fixture();
      await value.mount(tester, tab: 'review');
      expect(find.text('Geschriebene Beispielarbeit'), findsOneWidget);
      expect(find.text('Termin offen'), findsNothing);
      expect(value.writes, isEmpty);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('an exam being prepared still shows its missing appointment', (
    tester,
  ) async {
    final value = fixture.Fixture();
    await value.mount(tester, tab: 'prepare');
    expect(find.text('Bruchtest vorbereiten'), findsOneWidget);
    expect(find.text('Termin offen'), findsOneWidget);
    expect(value.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });
}
