import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/language_workshop.dart';

import 'child_context_forms_ux_test.dart' as f;

void main() {
  testWidgets('opening workshop during login sends no private reads', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) async {
        requests.add(r);
        return f.reply({'items': [], 'projects': [], 'has_more': false});
      }),
    );
    final intent = state.beginAuthentication();
    await tester.pumpWidget(f.home(LanguageWorkshop(state, childId: 'child')));
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(requests, isEmpty);
    expect(
      find.text('Öffne die Sprachwerkstatt bitte erneut.'),
      findsOneWidget,
    );
  });

  testWidgets('login hides workshop and preserves unsaved goal for reopening', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final state = f.account(
      MockClient((r) async {
        requests.add(r);
        return f.reply(
          r.url.path.endsWith('/vocabulary')
              ? {
                  'items': [f.word('one', 'school')],
                }
              : r.url.path.endsWith('/materials')
              ? {'items': []}
              : {'projects': [], 'has_more': false},
        );
      }),
    );
    await tester.pumpWidget(f.home(LanguageWorkshop(state, childId: 'child')));
    await tester.pumpAndSettle();
    await f.tap(tester, find.text('Neue Sprachübung'));
    await f.tap(tester, find.text('school'));
    await tester.enterText(
      f.field('Dein konkretes Lernziel'),
      'Mein eigener Entwurf',
    );
    await tester.pump();
    final create = tester.widget<FilledButton>(
      find.ancestor(
        of: find.text('Mein Lernprojekt vorbereiten'),
        matching: find.byType(FilledButton),
      ),
    );
    expect(create.onPressed, isNotNull);
    final oldGoal = tester
        .widget<TextField>(f.field('Dein konkretes Lernziel'))
        .controller!;
    final count = requests.length;
    final intent = state.beginAuthentication();
    oldGoal.text = 'Überholte Eingabe';
    create.onPressed!();
    await tester.pumpAndSettle();
    expect(find.text('Mein eigener Entwurf'), findsNothing);
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(requests, hasLength(count));
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpWidget(f.home(LanguageWorkshop(state, childId: 'child')));
    await tester.pumpAndSettle();
    await f.tap(tester, find.text('Neue Sprachübung'));
    final goal = tester.widget<TextField>(f.field('Dein konkretes Lernziel'));
    expect(goal.controller?.text, 'Mein eigener Entwurf');
    expect(requests.where((r) => r.method != 'GET'), isEmpty);
  });

  testWidgets('an old vocabulary link is inert while login is pending', (
    tester,
  ) async {
    final state = f.account(
      MockClient(
        (r) async => f.reply({'items': [], 'projects': [], 'has_more': false}),
      ),
    );
    await tester.pumpWidget(f.home(LanguageWorkshop(state, childId: 'child')));
    await tester.pumpAndSettle();
    await f.tap(tester, find.text('Neue Sprachübung'));
    final link = tester.widget<TextButton>(
      find.widgetWithText(TextButton, 'Zuerst Schulwörter bestätigen'),
    );
    state.beginAuthentication();
    link.onPressed!();
    await tester.pumpAndSettle();
    expect(find.text('Anmeldung läuft …'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
