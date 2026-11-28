import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/learning_plan_ui.dart';
import 'package:schulpilot/study_path_panel.dart';

import 'child_local_tools_ux88_test.dart' as f;

Json block(String id, String status) => {
  'id': id,
  'title': 'Thema $id',
  'phase': 'understand',
  'label': 'Verstehen',
  'status': status,
  'question_count': 4,
  if (status != 'planned') 'unit_id': 'unit-$id',
};
Json path(List<Json> blocks) => {
  'available': true,
  'blocks': blocks,
  'total_questions': blocks.length * 4,
  'completed_questions':
      blocks.where((b) => b['status'] == 'completed').length * 4,
  'ready_questions': blocks.where((b) => b['status'] == 'ready').length * 4,
  'can_continue': true,
  'next_block_id': blocks
      .where((b) => b['status'] != 'completed')
      .firstOrNull?['id'],
};
Future<void> open(WidgetTester tester, AppState state) =>
    f.show(tester, StudyPathPanel(state, 'child', 'day'));
void main() {
  testWidgets('Lernfortschritt ist ohne zusätzliche Prozentzahl verständlich',
      (tester) async {
    final semantics = tester.ensureSemantics();
    try {
      final requests = <http.Request>[];
      final state = f.account((request) async {
        requests.add(request);
        return f.reply(path([block('A', 'completed'), block('B', 'ready')]));
      });
      await open(tester, state);
      expect(find.text('4 von 8 Aufgaben bearbeitet'), findsOneWidget);
      expect(
        tester.getSemantics(find.text('4 von 8 Aufgaben bearbeitet')).label,
        '4 von 8 Aufgaben bearbeitet',
      );
      final root = tester.getSemantics(find.text('4 von 8 Aufgaben bearbeitet'))
          .owner!.rootSemanticsNode!;
      final values = <String>[];
      void collect(SemanticsNode node) {
        values.add(node.getSemanticsData().value);
        node.visitChildren((child) {
          collect(child);
          return true;
        });
      }
      collect(root);
      expect(values, isNot(contains('50')));
      expect(requests.every((request) => request.method == 'GET'), isTrue);
    } finally {
      semantics.dispose();
    }
  });
  for (final size in [const Size(320, 600), const Size(390, 844)]) {
    for (final scale in [1.0, 2.0]) {
      testWidgets(
        'Der nächste Lernschritt ist bei $size und Schrift $scale direkt verständlich',
        (tester) async {
          final requests = <http.Request>[];
          final done = block('A', 'completed');
          final ready = block('B', 'ready')..['label'] = 'Erste Runde';
          final state = f.account((request) async {
            requests.add(request);
            return f.reply(path([done, ready]));
          });
          await f.show(
            tester,
            StudyPathPanel(state, 'child', 'day'),
            size: size,
            scale: scale,
          );
          expect(find.text('Weiterlernen').hitTestable(), findsOneWidget);
          expect(
            find.widgetWithText(FilledButton, 'Weiterlernen'),
            findsOneWidget,
          );
          expect(find.text('Erste Runde'), findsNothing);
          expect(find.textContaining('bereit · verteilt'), findsNothing);
          expect(find.text('Suchen und filtern'), findsNothing);
          expect(find.byType(ChoiceChip), findsNothing);
          await f.tap(tester, find.text('Alle Lernschritte'));
          expect(find.text('Suchen und filtern'), findsOneWidget);
          expect(find.byType(ChoiceChip), findsNothing);
          expect(find.text('Bearbeitet'), findsOneWidget);
          expect(find.text('Bereit'), findsOneWidget);
          expect(requests.every((request) => request.method == 'GET'), isTrue);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
  for (final count in [3, 4]) {
    testWidgets(
      'Bei $count Lernschritten steht die Suche passend zur Listenlänge',
      (tester) async {
        final requests = <http.Request>[];
        final state = f.account((request) async {
          requests.add(request);
          return f.reply(path([
            for (var i = 0; i < count; i++) block('$i', 'planned'),
          ]));
        });
        await f.show(
          tester,
          StudyPathPanel(state, 'child', 'day'),
          size: const Size(390, 844),
        );
        await f.tap(tester, find.text('Alle Lernschritte'));
        final filter = find.text('Suchen und filtern');
        final first = find.widgetWithText(PlanRow, 'Thema 0');
        expect(filter, findsOneWidget);
        expect(first, findsOneWidget);
        final filterY = tester.getTopLeft(filter).dy;
        final firstY = tester.getTopLeft(first).dy;
        expect(count <= 3 ? filterY > firstY : filterY < firstY, isTrue);
        await f.tap(tester, filter);
        await tester.enterText(f.input('Lernschritte suchen'), 'Thema 1');
        await tester.pump();
        expect(find.widgetWithText(PlanRow, 'Thema 1'), findsOneWidget);
        expect(first, findsNothing);
        expect(requests.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets(
    'CK033 planned stage opens useful stored details without preparing a round',
    (tester) async {
      final requests = <http.Request>[];
      final state = f.account((r) async {
        requests.add(r);
        return f.reply(path([block('Brüche', 'planned')]));
      });
      await open(tester, state);
      await f.tap(tester, find.text('Alle Lernschritte'));
      await f.tap(tester, find.widgetWithText(PlanRow, 'Thema Brüche'));
      expect(
        find.text('Diesen Schritt kannst du später bearbeiten.'),
        findsOneWidget,
      );
      expect(find.text('4 geplante Aufgaben'), findsNothing);
      expect(
        find.textContaining('Hier werden noch keine Aufgaben erstellt.'),
        findsNothing,
      );
      expect(requests.every((r) => r.method == 'GET'), isTrue);
    },
  );
  testWidgets(
    'CK034 stage search finds an actual title and resets an empty view',
    (tester) async {
      final state = f.account(
        (r) async => f.reply(
          path([block('Brüche', 'planned'), block('Flächen', 'ready')]),
        ),
      );
      await open(tester, state);
      await f.tap(tester, find.text('Alle Lernschritte'));
      await f.tap(tester, find.text('Suchen und filtern'));
      await tester.enterText(f.input('Lernschritte suchen'), 'Flächen');
      await tester.pump();
      expect(find.widgetWithText(PlanRow, 'Thema Flächen'), findsOneWidget);
      expect(find.widgetWithText(PlanRow, 'Thema Brüche'), findsNothing);
      await tester.enterText(f.input('Lernschritte suchen'), 'Leer');
      await tester.pump();
      await f.tap(tester, find.text('Alle Lernschritte zeigen'));
      expect(tester.testTextInput.isVisible, isFalse);
      expect(find.widgetWithText(PlanRow, 'Thema Brüche'), findsOneWidget);
      expect(find.widgetWithText(PlanRow, 'Thema Flächen'), findsOneWidget);
    },
  );
  testWidgets(
    'CK035 stage state filter exposes only actually prepared or completed work',
    (tester) async {
      final requests = <http.Request>[];
      final state = f.account((r) async {
        requests.add(r);
        return f.reply(
          path([
            block('A', 'planned'),
            block('B', 'ready'),
            block('C', 'completed'),
          ]),
        );
      });
      await open(tester, state);
      await f.tap(tester, find.text('Alle Lernschritte'));
      await f.tap(tester, find.text('Suchen und filtern'));
      await f.tap(tester, find.widgetWithText(ChoiceChip, 'Bereit'));
      expect(find.widgetWithText(PlanRow, 'Thema B'), findsOneWidget);
      expect(find.widgetWithText(PlanRow, 'Thema A'), findsNothing);
      await f.tap(tester, find.widgetWithText(ChoiceChip, 'Bearbeitet'));
      expect(find.widgetWithText(PlanRow, 'Thema C'), findsOneWidget);
      expect(requests.every((r) => r.method == 'GET'), isTrue);
    },
  );
  testWidgets(
    'CK036 server-confirmed ready stage clears only the obsolete preparation error',
    (tester) async {
      var ready = false, posts = 0;
      final state = f.account((r) async {
        if (r.method == 'POST') {
          posts++;
          return http.Response(
            jsonEncode({'detail': 'Unklare Übertragung'}),
            503,
            headers: {'content-type': 'application/json'},
          );
        }
        return f.reply(path([block('A', ready ? 'ready' : 'planned')]));
      });
      await open(tester, state);
      await f.tap(tester, find.text('Runde vorbereiten'));
      expect(find.text('Unklare Übertragung'), findsOneWidget);
      ready = true;
      await f.tap(tester, find.text('Stand prüfen'));
      expect(find.text('Unklare Übertragung'), findsNothing);
      expect(find.text('Weiterlernen'), findsOneWidget);
      expect(posts, 1);
    },
  );
  testWidgets(
    'CK037 persisted stage failure remains understandable on a fresh GET',
    (tester) async {
      final requests = <http.Request>[];
      final failed = block('A', 'planned')
        ..['error'] = 'Die Quelle war nicht gut lesbar.';
      final state = f.account((r) async {
        requests.add(r);
        return f.reply(path([failed]));
      });
      await open(tester, state);
      expect(find.text('Die Quelle war nicht gut lesbar.'), findsOneWidget);
      expect(requests.every((r) => r.method == 'GET'), isTrue);
    },
  );
  testWidgets(
    'CK038 planned prepared and completed quantities are distinguished using stored facts',
    (tester) async {
      final state = f.account(
        (r) async => f.reply(
          path([
            block('A', 'planned'),
            block('B', 'ready'),
            block('C', 'completed'),
          ]),
        ),
      );
      await open(tester, state);
      expect(find.text('4 von 12 Aufgaben bearbeitet'), findsOneWidget);
      expect(
        find.text('4 bereit · verteilt auf mehrere Lerntage'),
        findsNothing,
      );
      expect(find.textContaining('Insgesamt geplant:'), findsNothing);
      await f.tap(tester, find.text('Alle Lernschritte'));
      await f.tap(tester, find.text('Suchen und filtern'));
      expect(
        find.text('4 bearbeitet · 4 Aufgaben bereit · 12 insgesamt'),
        findsOneWidget,
      );
    },
  );
}
