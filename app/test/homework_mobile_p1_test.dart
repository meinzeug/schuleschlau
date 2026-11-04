import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';

import 'homework_screen_test.dart' as homework;

void main() {
  for (final width in [320.0, 390.0]) {
    testWidgets('homework entry stays legible at $width and 200 percent text', (
      tester,
    ) async {
      final state = homework.account(
        MockClient(
          (request) async =>
              homework.reply({'photos': [], 'next_cursor': null}),
        ),
      );
      await homework.open(
        tester,
        state,
        overview: true,
        openTools: false,
        width: width,
        scale: 2,
      );
      final button = find.widgetWithText(
        FilledButton,
        'Hausaufgaben fotografieren',
      );
      await tester.ensureVisible(button);
      expect(button.hitTestable(), findsOneWidget);
      expect(tester.getSize(button).height, greaterThanOrEqualTo(48));
      expect(tester.takeException(), isNull);
    });
  }
  for (final width in [320.0, 390.0]) {
    testWidgets('saved homework labels identify the next action at $width', (
      tester,
    ) async {
      final methods = <String>[];
      final state = homework.account(
        MockClient((request) async {
          methods.add(request.method);
          if (!request.url.path.endsWith('/homework')) {
            return homework.reply(homework.fixture());
          }
          return homework.reply({
            'photos': [
              {
                'id': 'confirmed',
                'topic': 'Aufgabe A',
                'subject': '',
                'confirmed': true,
                'marked_done': 0,
              },
              {
                'id': 'reading',
                'topic': 'Aufgabe B',
                'subject': '',
                'confirmed': false,
                'status': 'uploaded',
              },
              {
                'id': 'review',
                'topic': 'Aufgabe C',
                'subject': '',
                'confirmed': false,
                'status': 'review',
              },
              {
                'id': 'photo',
                'topic': 'Aufgabe D',
                'subject': '',
                'confirmed': false,
                'status': 'unreadable',
              },
            ],
            'next_cursor': null,
          });
        }),
      );
      final router = await homework.open(
        tester,
        state,
        overview: true,
        openTools: false,
        width: width,
        scale: 2,
      );
      expect(find.text('Aufgabe öffnen'), findsOneWidget);
      expect(find.text('Foto öffnen'), findsOneWidget);
      expect(find.text('Foto und Text prüfen'), findsOneWidget);
      expect(find.text('Text unleserlich · Foto öffnen'), findsOneWidget);
      expect(find.text(' · 0 selbst abgehakt'), findsNothing);
      await tester.ensureVisible(find.text('Aufgabe D'));
      await tester.pumpAndSettle();
      expect(find.text('Aufgabe D').hitTestable(), findsOneWidget);
      await tester.tap(find.text('Aufgabe D'));
      await tester.pumpAndSettle();
      expect(
        router.routeInformationProvider.value.uri.path,
        '/homework/child/photo',
      );
      expect(methods.every((method) => method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    });
  }
}
