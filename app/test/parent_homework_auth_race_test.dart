import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/ui.dart';

import 'parent_cards_ux88_test.dart' as cards;

void main() {
  testWidgets('parent overview opened during login waits for explicit reload', (
    tester,
  ) async {
    final f = cards.Fixture();
    final revision = f.state.beginAuthentication();
    await f.mount(tester, '/parent-homework/child');
    expect(f.requests, isEmpty);
    final button = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Hausaufgaben erneut laden'),
    );
    expect(button.onPressed, isNull);
    f.state.cancelAuthentication(revision);
    await tester.pump();
    expect(f.requests, isEmpty);
    await tester.tap(find.text('Hausaufgaben erneut laden'));
    await tester.pumpAndSettle();
    expect(f.requests, hasLength(1));
    expect(f.requests.single.method, 'GET');
    expect(find.text('Mathematik · Flächen'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('a queued parent photo tap cannot navigate after login starts', (
    tester,
  ) async {
    final f = cards.Fixture();
    final router = await f.mount(tester, '/parent-homework/child');
    final panel = find.ancestor(
      of: find.text('Mathematik · Flächen'),
      matching: find.byType(ActionPanel),
    );
    final oldTap = tester.widget<ActionPanel>(panel).onPressed!;
    final location = router.routeInformationProvider.value.uri;
    final count = f.requests.length;
    final revision = f.state.beginAuthentication();
    oldTap();
    await tester.pumpAndSettle();
    expect(router.routeInformationProvider.value.uri, location);
    expect(f.requests.length, count);
    expect(find.text('Hausaufgaben erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
  });

  testWidgets('login intent immediately hides the parent homework overview', (
    tester,
  ) async {
    final f = cards.Fixture();
    await f.mount(tester, '/parent-homework/child');
    expect(find.text('Mathematik · Flächen'), findsOneWidget);
    final count = f.requests.length;
    final revision = f.state.beginAuthentication();
    await tester.pump();
    expect(find.text('Mathematik · Flächen'), findsNothing);
    expect(find.text('Hausaufgaben erneut laden'), findsOneWidget);
    expect(f.requests.length, count);
    f.state.cancelAuthentication(revision);
    await tester.pump();
    expect(f.requests.length, count);
    await tester.tap(find.text('Hausaufgaben erneut laden'));
    await tester.pumpAndSettle();
    expect(f.requests.length, count + 1);
    expect(find.text('Mathematik · Flächen'), findsOneWidget);
    expect(f.requests.every((r) => r.method == 'GET'), isTrue);
  });

  testWidgets('a late parent overview response remains hidden after login', (
    tester,
  ) async {
    final f = cards.Fixture();
    final old = Completer<http.Response>();
    var reads = 0;
    f.respond = (request) async {
      if (request.url.path.endsWith('/homework-review') && ++reads == 2) {
        return old.future;
      }
      return null;
    };
    await f.mount(tester, '/parent-homework/child');
    final refresh = find.byTooltip('Aktualisieren');
    await tester.ensureVisible(refresh.first);
    await tester.tap(refresh.first);
    await tester.pump();
    expect(reads, 2);
    final revision = f.state.beginAuthentication();
    old.complete(cards.response(f.homework));
    await tester.pumpAndSettle();
    expect(find.text('Mathematik · Flächen'), findsNothing);
    expect(find.text('Hausaufgaben erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.pump();
    expect(reads, 2);
    await tester.tap(find.text('Hausaufgaben erneut laden'));
    await tester.pumpAndSettle();
    expect(reads, 3);
    expect(find.text('Mathematik · Flächen'), findsOneWidget);
  });
}
