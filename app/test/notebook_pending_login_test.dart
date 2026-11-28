import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'notebook_test.dart' as fixture;

void main() {
  testWidgets(
    'opening a notebook during login does not load photos or subjects',
    (tester) async {
      late int intent;
      final (state, _, requests) = await fixture.open(
        tester,
        photos: false,
        beforeMount: (state) => intent = state.beginAuthentication(),
      );
      expect(requests, isEmpty);
      expect(find.text('Anmeldung läuft …'), findsOneWidget);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      expect(requests, isEmpty);
      expect(find.text('Öffne deinen Hefter erneut.'), findsOneWidget);
      expect(find.text('Zu meinen Heften'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );

  testWidgets('a late subject response cannot load pages after login starts', (
    tester,
  ) async {
    final delayed = Completer<http.Response>();
    final (state, _, requests) = await fixture.open(
      tester,
      photos: false,
      settle: false,
      respond: (request) => delayed.future,
    );
    expect(requests, hasLength(1));
    final intent = state.beginAuthentication();
    await tester.pump();
    delayed.complete(fixture.jsonReply(fixture.subjects()));
    await tester.pump();
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(requests, hasLength(1));
    expect(find.text('Mathematik'), findsNothing);
    expect(find.text('Öffne deinen Hefter erneut.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets(
    'login closes notebook filters and old controls cannot apply them',
    (tester) async {
      final (state, _, requests) = await fixture.open(tester, photos: false);
      await fixture.openNotebookFilters(tester);
      final action = tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Anzeigen'))
          .onPressed!;
      final prior = requests.length;
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Seitenstatus'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      action();
      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(requests.length, prior);
      expect(find.text('Öffne deinen Hefter erneut.'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );
}
