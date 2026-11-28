import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'child_notebook_actions_ux88_test.dart' as child;
import 'notebook_test.dart' as fixture;

Future<http.Response> response(
  http.Request request, {
  bool empty = false,
}) async {
  if (request.url.path.endsWith('/subjects')) {
    return fixture.jsonReply(fixture.subjects());
  }
  if (empty || request.url.queryParameters['q']?.isNotEmpty == true) {
    return fixture.jsonReply({'items': [], 'total': 0, 'page': 1, 'pages': 1});
  }
  return fixture.jsonReply(fixture.pages(request, photos: false));
}

Future<void> emptySearch(WidgetTester tester) async {
  await fixture.openNotebookSearch(tester);
  await tester.enterText(
    child.label('In diesem Hefter suchen'),
    'kein Treffer',
  );
  await tester.testTextInput.receiveAction(TextInputAction.search);
  await tester.pumpAndSettle();
}

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets('Empty search prioritizes saved pages at $width / $scale×', (
      tester,
    ) async {
      final (_, _, requests) = await fixture.open(
        tester,
        width: width,
        textScale: scale,
        photos: false,
        respond: (request) => response(request),
      );
      await emptySearch(tester);
      expect(find.text('Dazu gibt es gerade keine Seiten.'), findsOneWidget);
      final reset = find.widgetWithText(FilledButton, 'Alle Seiten zeigen');
      await tester.ensureVisible(reset);
      expect(reset.hitTestable(), findsOneWidget);
      expect(
        find.widgetWithText(FilledButton, 'Heftfoto hinzufügen'),
        findsNothing,
      );
      expect(find.byTooltip('Heftfoto hinzufügen'), findsOneWidget);
      await tester.tap(reset);
      await tester.pumpAndSettle();
      expect(requests.last.url.queryParameters['q'] ?? '', isEmpty);
      expect(find.text('Dazu gibt es gerade keine Seiten.'), findsNothing);
      expect(requests.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('A truly empty notebook still offers its first photo', (
    tester,
  ) async {
    final (_, _, requests) = await fixture.open(
      tester,
      photos: false,
      respond: (request) => response(request, empty: true),
    );
    expect(
      find.text('Hier sind noch keine Heftseiten vorhanden.'),
      findsOneWidget,
    );
    expect(
      find.widgetWithText(FilledButton, 'Erstes Heftfoto hinzufügen'),
      findsOneWidget,
    );
    expect(find.text('Alle Seiten zeigen'), findsNothing);
    expect(requests.every((request) => request.method == 'GET'), isTrue);
  });

  testWidgets('The first photo action stays reachable with large text', (
    tester,
  ) async {
    await fixture.open(
      tester,
      photos: false,
      width: 320,
      textScale: 2,
      respond: (request) => response(request, empty: true),
    );
    final add = find.widgetWithText(FilledButton, 'Erstes Heftfoto hinzufügen');
    await tester.ensureVisible(add);
    await tester.pumpAndSettle();
    expect(add.hitTestable(), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  for (final login in [true, false]) {
    testWidgets(
      'Old reset cannot change ${login ? 'a new session' : 'another account'}',
      (tester) async {
        final (state, _, requests) = await fixture.open(
          tester,
          photos: false,
          respond: (request) => response(request),
        );
        await emptySearch(tester);
        final reset = tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Alle Seiten zeigen'),
            )
            .onPressed!;
        final before = requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          reset();
          state.cancelAuthentication(intent);
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        reset();
        await tester.pumpAndSettle();
        expect(requests, hasLength(before));
        expect(requests.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }
}
