import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/text_probe_player.dart';
import 'package:schulpilot/ui.dart';

import 'exams_screen_test.dart' as exam;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('exam day details report their current state', (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      final fixture = exam.Fixture();
      await fixture.mount(tester, selected: 'exam');
      final control = find.widgetWithText(TextButton, 'Mehr zum Lerntag');
      await tester.ensureVisible(control);
      await tester.pumpAndSettle();
      expect(
        tester
            .getSemantics(control)
            .getSemanticsData()
            .flagsCollection
            .isExpanded,
        Tristate.isFalse,
      );
      await exam.tap(tester, control);
      final data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      expect(fixture.writes, isEmpty);
    } finally {
      semantics.dispose();
    }
  });

  testWidgets('text exploration reports its state without a request', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final calls = <http.Request>[];
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          calls.add(request);
          throw StateError('Exploration must remain local.');
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child'};
    final block = <String, dynamic>{
      'kind': 'text_probe',
      'title': 'Textgruppen',
      'disclosure': 'hint1',
      'labels': ['heute', 'lernt', 'Mika'],
      'numbers': [],
      'connections': [],
      'marks': [],
      'unit': '',
      'variant': '',
      'text_probe': {
        'version': 1,
        'segments': [
          {'id': 'time', 'text': 'heute'},
          {'id': 'verb', 'text': 'lernt'},
          {'id': 'person', 'text': 'Mika'},
        ],
        'variants': [
          {
            'id': 'first',
            'order': ['time', 'verb', 'person'],
          },
          {
            'id': 'second',
            'order': ['person', 'verb', 'time'],
          },
        ],
      },
    };
    try {
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: SingleChildScrollView(
              child: TextProbePlayer(block, state: state),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      final control = find.byKey(const ValueKey('text-probe-toggle'));
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.ensureVisible(control);
      await tester.tap(control);
      await tester.pumpAndSettle();
      data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isTrue);
      expect(calls, isEmpty);
    } finally {
      await tester.pumpWidget(const SizedBox());
      state.dispose();
      semantics.dispose();
    }
  });
}
