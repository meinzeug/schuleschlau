import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';

import 'homework_screen_test.dart' as homework;
import 'page_tools_test_helpers.dart' as tools;

void main() {
  testWidgets('Leere Fotoübersicht bleibt einfach und kann aktualisieren', (
    tester,
  ) async {
    var requests = 0;
    final methods = <String>[];
    final state = homework.account(
      MockClient((request) async {
        methods.add(request.method);
        if (request.url.path == '/api/app-release') {
          return homework.reply({'available': false});
        }
        requests++;
        return homework.reply({
          'photos': requests == 2
              ? [
                  {'id': 'one', 'topic': 'Rechteck', 'confirmed': false},
                ]
              : [],
          'next_cursor': null,
        });
      }),
    );
    await homework.open(
      tester,
      state,
      overview: true,
      openTools: false,
      width: 320,
      scale: 2,
    );
    expect(find.text('Noch keine Aufgabenfotos.'), findsOneWidget);
    expect(find.text('0 von 0 geladenen Fotos'), findsNothing);
    expect(find.text('Erstes Hausaufgabenfoto aufnehmen'), findsNothing);
    expect(
      find.widgetWithText(FilledButton, 'Hausaufgaben fotografieren'),
      findsOneWidget,
    );
    await tools.openPageTools(tester, 'homework-photo-tools');
    expect(find.text('Foto suchen'), findsNothing);
    await homework.tap(tester, 'Aufgabenfotos aktualisieren');
    expect(find.text('Rechteck'), findsOneWidget);
    await tools.openPageTools(tester, 'homework-photo-tools');
    await homework.tap(tester, 'Foto noch prüfen');
    await homework.tap(tester, 'Aufgabenfotos aktualisieren');
    expect(find.text('Alle geladenen Fotos zeigen'), findsOneWidget);
    expect(find.text('Foto noch prüfen'), findsWidgets);
    await homework.tap(tester, 'Alle geladenen Fotos zeigen');
    expect(find.text('Noch keine Aufgabenfotos.'), findsOneWidget);
    expect(methods.every((method) => method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });
}
