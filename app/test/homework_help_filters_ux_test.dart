import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'child_local_tools_ux88_test.dart' as local;
import 'homework_screen_test.dart' as homework;

Map<String, dynamic> help(String action) {
  final result = homework.modelTurn();
  result['id'] = action;
  result['question'] = 'Künstliche Hilfe: $action';
  result['homework']['action'] = action;
  result['reply']['action'] = action;
  return result;
}

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets('One help type needs no filter at $width px and $scale×', (
      tester,
    ) async {
      final requests = <http.Request>[];
      final data = homework.fixture(
        turns: [homework.analysisTurn(), help('explain')],
      );
      final state = homework.account(
        MockClient((r) async {
          requests.add(r);
          return homework.reply(data);
        }),
      );
      await homework.open(tester, state, width: width, scale: scale);
      expect(find.text('Künstliche Hilfe: explain'), findsOneWidget);
      expect(find.widgetWithText(FilterChip, 'Alle Hilfearten'), findsNothing);
      expect(find.text('Geladene Lernhilfen nach Anfrageart'), findsNothing);
      expect(requests.every((r) => r.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Different help types remain filterable without a new request', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final data = homework.fixture(
      turns: [homework.analysisTurn(), help('explain'), help('hint')],
    );
    final state = homework.account(
      MockClient((r) async {
        requests.add(r);
        return homework.reply(data);
      }),
    );
    await homework.open(tester, state, width: 320, scale: 2);
    expect(find.text('Deine Hilfen'), findsOneWidget);
    await local.tap(tester, find.widgetWithText(FilterChip, 'Hinweis'));
    expect(find.text('Künstliche Hilfe: hint'), findsOneWidget);
    expect(find.text('Künstliche Hilfe: explain'), findsNothing);
    await local.tap(tester, find.widgetWithText(FilterChip, 'Alle Hilfearten'));
    await homework.tap(tester, 'Bisherige Lernhilfen (1)');
    expect(find.text('Künstliche Hilfe: explain'), findsOneWidget);
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('An active filter remains resettable if all help disappears', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final data = homework.fixture(
      turns: [homework.analysisTurn(), help('explain'), help('hint')],
    );
    final state = homework.account(
      MockClient((r) async {
        requests.add(r);
        return homework.reply(data);
      }),
    );
    await homework.open(tester, state);
    await local.tap(tester, find.widgetWithText(FilterChip, 'Hinweis'));
    data['turns'] = [homework.analysisTurn()];
    await homework.tap(tester, 'Aktualisieren');
    expect(
      find.text(
        'In den geladenen Hilfen ist diese Anfrageart nicht vorhanden.',
      ),
      findsOneWidget,
    );
    expect(find.widgetWithText(FilterChip, 'Alle Hilfearten'), findsOneWidget);
    await local.tap(tester, find.widgetWithText(FilterChip, 'Alle Hilfearten'));
    expect(find.text('Deine Hilfen'), findsNothing);
    expect(requests.every((r) => r.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  for (final login in [true, false]) {
    testWidgets(
      'Old help filter is inert after ${login ? 'sign-in intent' : 'account replacement'}',
      (tester) async {
        final requests = <http.Request>[];
        final data = homework.fixture(
          turns: [homework.analysisTurn(), help('explain'), help('hint')],
        );
        final state = homework.account(
          MockClient((r) async {
            requests.add(r);
            return homework.reply(data);
          }),
        );
        await homework.open(tester, state);
        final oldAction = tester
            .widget<FilterChip>(find.widgetWithText(FilterChip, 'Hinweis'))
            .onSelected!;
        final dynamic body = tester.state(
          find.byWidgetPredicate(
            (widget) => widget.runtimeType.toString() == '_HomeworkDetailBody',
          ),
        );
        expect(body.helpKind, 'all');
        final before = requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          oldAction(true);
          state.cancelAuthentication(intent);
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        oldAction(true);
        expect(body.helpKind, 'all');
        await tester.pumpAndSettle();
        expect(requests, hasLength(before));
        expect(tester.takeException(), isNull);
      },
    );
  }
}
