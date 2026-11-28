import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';

import 'collection_screen_test.dart' as collection;
import 'notebook_test.dart' as notebook;
import 'page_tools_test_helpers.dart' as page_tools;

void main() {
  testWidgets('subject shelf does not load during login', (tester) async {
    late int intent;
    final (state, _, requests) = await notebook.open(
      tester,
      shelf: true,
      photos: false,
      beforeMount: (state) => intent = state.beginAuthentication(),
    );
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    expect(find.text('Öffne deine Hefte erneut.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('old shelf and photo actions stay inert after login starts', (
    tester,
  ) async {
    final (state, router, requests) = await notebook.open(
      tester,
      shelf: true,
      photos: false,
    );
    expect(find.text('Mathematik'), findsWidgets);
    final photo = tester
        .widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Seiten hinzufügen').first,
        )
        .onPressed!;
    final before = requests.length;
    final intent = state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Mathematik'), findsNothing);
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Seiten hinzufügen').first,
          )
          .onPressed,
      isNull,
    );
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    photo();
    await tester.pumpAndSettle();
    expect(requests.length, before);
    expect(router.routeInformationProvider.value.uri.path, '/library/child');
    expect(find.text('Öffne deine Hefte erneut.'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  for (final learning in [false, true]) {
    testWidgets(
      'paged collection starts no read during login (learning: $learning)',
      (tester) async {
        final requests = <http.Request>[];
        final state =
            AppState(
                api: Api(
                  base: 'https://example.invalid/api',
                  client: MockClient((request) async {
                    requests.add(request);
                    return collection.reply(
                      collection.listing(total: 1, learning: learning),
                    );
                  }),
                ),
              )
              ..user = {
                'id': 'synthetic-child',
                'role': 'child',
                'child_id': 'child',
              };
        final intent = state.beginAuthentication();
        await collection.open(
          tester,
          (_) async => throw StateError('unexpected'),
          existing: state,
          learning: learning,
        );
        expect(requests, isEmpty);
        expect(find.text('Anmeldung läuft …'), findsOneWidget);
        state.cancelAuthentication(intent);
        await tester.pumpAndSettle();
        expect(requests, isEmpty);
        expect(find.text('Öffne die Seite erneut.'), findsOneWidget);
        await tester.pumpWidget(const SizedBox());
        state.dispose();
      },
    );
  }
  testWidgets(
    'login closes collection filters and invalidates old dialog actions',
    (tester) async {
      final requests = <http.Request>[];
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient((request) async {
            requests.add(request);
            return collection.reply(collection.listing(total: 1));
          }),
        ),
      )..user = {'id': 'synthetic-child', 'role': 'child', 'child_id': 'child'};
      await collection.open(
        tester,
        (_) async => throw StateError('unexpected'),
        existing: state,
      );
      await page_tools.openPageTools(tester, 'learning-tools');
      await collection.tap(tester, find.byTooltip('Filter und Sortierung'));
      final oldApply = tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Anwenden'))
          .onPressed!;
      final oldCancel = tester
          .widget<TextButton>(find.widgetWithText(TextButton, 'Abbrechen'))
          .onPressed!;
      final oldSelect = tester
          .widget<DropdownButtonFormField<String>>(
            find.byType(DropdownButtonFormField<String>).last,
          )
          .onChanged!;
      final before = requests.length;
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Ansicht anpassen'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      oldApply();
      oldCancel();
      oldSelect('newest');
      await tester.pump();
      expect(tester.takeException(), isNull);
      expect(requests.length, before);
      expect(find.text('Öffne die Seite erneut.'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );
}
