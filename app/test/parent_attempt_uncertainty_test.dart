import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/math_content.dart';
import 'package:schulpilot/ui.dart';
import 'package:schulpilot/unit_screen.dart';

import 'unit_learning_time_test.dart' as fixture;

Finder answerWith(String phrase) => find.byWidgetPredicate(
  (w) =>
      w is MathText &&
      (w.data?.contains('Antwort: Katze') ?? false) &&
      (w.data?.contains(phrase) ?? false),
);

Future<void> mount(WidgetTester tester, List<Json> attempts) async {
  final data = fixture.unit(status: 'active');
  data['questions'][0]['hints'] = <String>[];
  data['questions'][0]['explanation'] = 'Künstliche Erklärung.';
  data['questions'][0]['attempts'] = attempts;
  final state = AppState(
    api: Api(
      base: 'https://example.invalid/api',
      client: MockClient(
        (_) async => http.Response(
          jsonEncode(data),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        ),
      ),
    ),
  )..user = {'id': 'synthetic-parent', 'role': 'parent'};
  final router = GoRouter(
    initialLocation: '/unit/unit',
    routes: [
      GoRoute(
        path: '/unit/:id',
        builder: (_, _) => UnitScreen(state, unitId: 'unit'),
      ),
    ],
  );
  addTearDown(() async {
    await tester.pumpWidget(const SizedBox());
    router.dispose();
    state.dispose();
  });
  await tester.pumpWidget(
    MaterialApp.router(theme: appTheme(), routerConfig: router),
  );
  await tester.pumpAndSettle();
}

Json attempt({
  required bool assisted,
  required bool uncertain,
  Object? created = 1700000000,
}) => {
  'id': 'synthetic-attempt',
  'answer': 'Katze',
  'outcome': 'correct',
  'assisted': assisted,
  'created': created,
  'evaluation': {'independence_uncertain': uncertain},
  'assessment_history': <Json>[],
};

Future<void> choose(WidgetTester tester, String text) async {
  await tester.ensureVisible(find.text(text));
  await tester.tap(find.text(text));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'uncertainty is not shown or filtered as independent or supported',
    (tester) async {
      await mount(tester, [attempt(assisted: false, uncertain: true)]);
      expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
      expect(answerWith('selbstständig'), findsNothing);
      await choose(tester, 'Selbstständig im ersten Versuch');
      expect(answerWith('Katze'), findsNothing);
      await choose(tester, 'Mit Hilfe oder erneut richtig');
      expect(answerWith('Katze'), findsNothing);
      await choose(tester, 'Bewertung offen');
      expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets(
    'documented help remains visible and categorized when the marker is set',
    (tester) async {
      await mount(tester, [attempt(assisted: true, uncertain: true)]);
      expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
      expect(answerWith('selbstständig'), findsNothing);
      await choose(tester, 'Mit Hilfe oder erneut richtig');
      expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('documented help remains visible with an unknown timestamp', (
    tester,
  ) async {
    await mount(tester, [
      attempt(assisted: true, uncertain: true, created: null),
    ]);
    expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
    await choose(tester, 'Mit Hilfe oder erneut richtig');
    expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
  });
  testWidgets('unknown retry order is not filtered as a secure verdict', (
    tester,
  ) async {
    final first = attempt(assisted: true, uncertain: false, created: null);
    final second = {
      ...attempt(assisted: false, uncertain: false),
      'id': 'retry',
    };
    await mount(tester, [first, second]);
    expect(
      find.text('Die Reihenfolge der Versuche ist nicht sicher bekannt.'),
      findsOneWidget,
    );
    expect(find.textContaining('Versuch 1'), findsNothing);
    expect(find.textContaining('Gespeicherter Versuch'), findsNWidgets(2));
    expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
    expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
    await choose(tester, 'Bewertung offen');
    expect(answerWith('mit Unterstützung oder erneut'), findsOneWidget);
    expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
  });
  testWidgets('unknown time does not get shown as an independent success', (
    tester,
  ) async {
    await mount(tester, [
      attempt(assisted: false, uncertain: false, created: null),
    ]);
    expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
    await choose(tester, 'Bewertung offen');
    expect(answerWith('Selbstständigkeit offen'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets(
    'a recorded unassisted first answer stays independent when not uncertain',
    (tester) async {
      await mount(tester, [attempt(assisted: false, uncertain: false)]);
      expect(answerWith('selbstständig'), findsOneWidget);
      await choose(tester, 'Selbstständig im ersten Versuch');
      expect(answerWith('selbstständig'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}
