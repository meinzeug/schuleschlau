import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/curriculum_topics_dialog.dart';

import 'curriculum_profile_110_test.dart' as f;

Map<String, dynamic> row(
  String id,
  String title, {
  String phase = 'Schuljahrgänge 7/8',
}) => {
  'id': id,
  'title': title,
  'state_code': 'DE-BW',
  'school_form_id': 'bw_example',
  'subject_id': 'fr',
  'grade_kind': 'phase',
  'grades': null,
  'phase_label': phase,
  'source': {'page': 12},
};

f.Fixture prepare() {
  final fixture = f.Fixture()..stored = f.profile(configured: true);
  fixture.currentCatalog = {
    ...f.catalog(),
    'subjects': [
      {'id': 'fr', 'title': 'Französisch'},
    ],
  };
  fixture.topicsHandler = (_) async => f.response({
    'items': [row('one', 'Französisch: Alltag verstehen')],
    'next_cursor': null,
  });
  return fixture;
}

Future<void> openTopics(WidgetTester tester, f.Fixture fixture) async {
  await fixture.mount(tester);
  await f.tap(tester, find.byKey(const ValueKey('curriculum-open-topics')));
}

void main() {
  for (final width in [320.0, 390.0]) {
    testWidgets(
      'parents choose a subject explicitly without changing courses at $width',
      (tester) async {
        final fixture = prepare();
        await fixture.mount(tester, width: width, scale: width == 320 ? 2 : 1);
        final initial = fixture.calls.length;
        await f.tap(
          tester,
          find.byKey(const ValueKey('curriculum-open-topics')),
        );
        expect(
          fixture.calls
              .skip(initial)
              .every((request) => request.method == 'GET'),
          isTrue,
        );
        expect(
          fixture.calls.where(
            (request) => request.url.path.endsWith('/topics'),
          ),
          isEmpty,
        );
        expect(
          find.text('Baden-Württemberg · Künstlicher Schulweg A'),
          findsOneWidget,
        );
        await f.pick(
          tester,
          find.byKey(const ValueKey('curriculum-topic-subject')),
          'Französisch',
        );
        expect(find.text('Alltag verstehen'), findsOneWidget);
        expect(find.text('Französisch: Alltag verstehen'), findsNothing);
        expect(find.textContaining('Schuljahrgänge 7/8'), findsOneWidget);
        final sent = fixture.calls.singleWhere(
          (request) => request.url.path.endsWith('/topics'),
        );
        expect(sent.url.queryParameters['state_code'], 'DE-BW');
        expect(sent.url.queryParameters['school_form_id'], 'bw_example');
        expect(sent.url.queryParameters['subject_id'], 'fr');
        expect(sent.url.queryParameters.containsKey('grade'), isFalse);
        expect(sent.url.queryParameters.containsKey('phase'), isFalse);
        expect(fixture.puts, isEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('old topics are hidden if login starts during a delayed read', (
    tester,
  ) async {
    final fixture = prepare();
    final delayed = Completer<http.Response>();
    fixture.topicsHandler = (_) => delayed.future;
    await openTopics(tester, fixture);
    await f.tap(tester, find.byKey(const ValueKey('curriculum-topic-subject')));
    await tester.tap(find.text('Französisch').last);
    await tester.pump();
    final intent = fixture.state.beginAuthentication();
    await tester.pump();
    delayed.complete(
      f.response({
        'items': [row('old', 'Alte Themen')],
        'next_cursor': null,
      }),
    );
    await tester.pumpAndSettle();
    fixture.state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(find.text('Alte Themen'), findsNothing);
    expect(find.byType(AlertDialog), findsOneWidget);
    expect(find.text('Lehrplanauswahl pausiert'), findsOneWidget);
    expect(fixture.puts, isEmpty);
  });

  testWidgets(
    'duplicate cursor response is rejected without repeating entries',
    (tester) async {
      final fixture = prepare();
      fixture.topicsHandler = (request) async => f.response({
        'items': [row('one', 'Alltag verstehen')],
        'next_cursor': 'one',
      });
      await openTopics(tester, fixture);
      await f.pick(
        tester,
        find.byKey(const ValueKey('curriculum-topic-subject')),
        'Französisch',
      );
      expect(find.text('Alltag verstehen'), findsOneWidget);
      await f.tap(tester, find.text('Weitere Themen'));
      expect(find.text('Alltag verstehen'), findsOneWidget);
      expect(
        find.text('Die Themen konnten nicht geladen werden.'),
        findsOneWidget,
      );
      expect(fixture.puts, isEmpty);
    },
  );
  testWidgets('opening topics preserves an unsaved school profile draft', (
    tester,
  ) async {
    final fixture = prepare();
    await fixture.mount(tester);
    await f.pick(tester, f.gradeField(), 'Klasse 8');
    await f.tap(tester, find.byKey(const ValueKey('curriculum-open-topics')));
    await f.tap(
      tester,
      find.descendant(
        of: find.byType(CurriculumTopicsDialog),
        matching: find.text('Schließen'),
      ),
    );
    expect(f.gradeValue(tester), 8);
    expect(fixture.puts, isEmpty);
  });

  testWidgets('topics for a different school form are not displayed', (
    tester,
  ) async {
    final fixture = prepare();
    fixture.topicsHandler = (_) async => f.response({
      'items': [
        {...row('foreign', 'Anderer Schulweg'), 'school_form_id': 'other'},
      ],
      'next_cursor': null,
    });
    await openTopics(tester, fixture);
    await f.pick(
      tester,
      find.byKey(const ValueKey('curriculum-topic-subject')),
      'Französisch',
    );
    expect(find.text('Anderer Schulweg'), findsNothing);
    expect(
      find.text('Die Themen konnten nicht geladen werden.'),
      findsOneWidget,
    );
    expect(fixture.puts, isEmpty);
  });

  testWidgets('old pagination action cannot load a newly selected subject', (
    tester,
  ) async {
    final fixture = prepare();
    fixture.currentCatalog = {
      ...f.catalog(),
      'subjects': [
        {'id': 'fr', 'title': 'Französisch'},
        {'id': 'math', 'title': 'Mathematik'},
      ],
    };
    fixture.topicsHandler = (request) async {
      if (request.url.queryParameters['subject_id'] == 'fr') {
        return f.response({
          'items': [row('one', 'Alltag verstehen')],
          'next_cursor': 'one',
        });
      }
      return f.response({
        'items': [
          {...row('two', 'Mathethema'), 'subject_id': 'math'},
        ],
        'next_cursor': null,
      });
    };
    await openTopics(tester, fixture);
    await f.pick(
      tester,
      find.byKey(const ValueKey('curriculum-topic-subject')),
      'Französisch',
    );
    final oldMore = tester
        .widget<TextButton>(find.widgetWithText(TextButton, 'Weitere Themen'))
        .onPressed!;
    await f.pick(
      tester,
      find.byKey(const ValueKey('curriculum-topic-subject')),
      'Mathematik',
    );
    final count = fixture.calls.length;
    oldMore();
    await tester.pump();
    expect(fixture.calls.length, count);
    expect(find.text('Mathethema'), findsOneWidget);
    expect(find.text('Alltag verstehen'), findsNothing);
  });
}
