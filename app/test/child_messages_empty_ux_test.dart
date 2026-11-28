import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/child_messages.dart';
import 'package:schulpilot/page_tools.dart';

import 'child_local_tools_ux88_test.dart' as fixture;
import 'page_tools_test_helpers.dart' as tools;

void main() {
  for (final scale in [1.0, 2.0]) {
    testWidgets('Empty family inbox stays simple at $scale×', (tester) async {
      final state = fixture.account(
        (_) async => throw StateError('no network'),
      );
      var written = 0;
      await fixture.show(
        tester,
        ChildMessagesHub(
          state,
          data: {
            'child': {'id': 'child'},
            'messages': [],
          },
          onCompose: (_, _) async {},
          onWriteMessage: () async => written++,
        ),
        size: const Size(320, 844),
        scale: scale,
      );
      expect(find.byType(PageToolsGroup), findsNothing);
      expect(find.textContaining('Noch keine Nachrichten.'), findsOneWidget);
      await fixture.tap(tester, find.text('Frage schreiben'));
      expect(written, 1);
      await fixture.tap(tester, find.text('Meine Wünsche'));
      expect(find.byType(PageToolsGroup), findsNothing);
      expect(find.text('Deine Ideen erscheinen hier.'), findsOneWidget);
      await fixture.tap(tester, find.text('Besprochen'));
      expect(find.byType(PageToolsGroup), findsNothing);
      expect(find.text('Besprochene Wünsche erscheinen hier.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox.shrink());
      state.dispose();
    });
  }

  testWidgets('An active search remains available when it finds no messages', (
    tester,
  ) async {
    final state = fixture.account((_) async => throw StateError('no network'));
    await fixture.show(tester, fixture.mailbox(state, fixture.mailData()));
    await tools.openPageTools(tester, 'child-message-tools');
    await tester.enterText(
      fixture.input('Nachrichten durchsuchen'),
      'unbekannt',
    );
    await tester.pumpAndSettle();
    expect(find.byType(PageToolsGroup), findsOneWidget);
    await fixture.tap(tester, find.text('Suche und Absender zurücksetzen'));
    expect(find.text('Bitte Brüche weiter üben.'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    state.dispose();
  });
}
