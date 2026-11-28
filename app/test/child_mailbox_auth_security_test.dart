import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/child_messages.dart';

import 'child_local_tools_ux88_test.dart' as f;
import 'page_tools_test_helpers.dart' as page_tools;

void main() {
  testWidgets(
    'a new sign-in clears private search and does not restore it on reopen',
    (tester) async {
      final state = f.account((_) async => f.reply({}));
      await f.show(tester, f.mailbox(state, f.mailData()));
      await page_tools.togglePageTools(tester);
      await tester.enterText(f.input('Nachrichten durchsuchen'), 'Brüche');
      await tester.pumpAndSettle();
      expect(state.collectionViews['child_mailbox:child']?['q'], 'Brüche');
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(state.collectionViews.containsKey('child_mailbox:child'), isFalse);
      state.cancelAuthentication(intent);
      await tester.pumpWidget(const SizedBox());
      await f.show(tester, f.mailbox(state, f.mailData()));
      await page_tools.togglePageTools(tester);
      expect(
        tester
            .widget<TextField>(f.input('Nachrichten durchsuchen'))
            .controller!
            .text,
        '',
      );
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );

  testWidgets(
    'authentication intent closes the reader and permanently invalidates old actions',
    (tester) async {
      final state = f.account((_) async => f.reply({}));
      state.familyId = 'family';
      final data = f.mailData();
      data['messages'][0]['body'] = 'Künstliche private Nachricht. ' * 25;
      var writes = 0;
      await f.show(
        tester,
        ChildMessagesHub(
          state,
          data: data,
          onCompose: (_, _) async {},
          onWriteMessage: () async {
            writes++;
          },
        ),
      );
      final oldWrite = tester
          .widget<OutlinedButton>(
            find.widgetWithText(OutlinedButton, 'Frage schreiben'),
          )
          .onPressed!;
      await f.tap(tester, find.text('Nachricht in Ruhe lesen'));
      expect(find.byType(AlertDialog), findsOneWidget);
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.textContaining('Künstliche private Nachricht'), findsNothing);
      oldWrite();
      state.cancelAuthentication(intent);
      oldWrite();
      await tester.pumpAndSettle();
      expect(writes, 0);
      expect(find.textContaining('Künstliche private Nachricht'), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );

  for (final changed in ['token', 'family']) {
    testWidgets('changing $changed hides the previous private mailbox', (
      tester,
    ) async {
      final state = f.account((_) async => f.reply({}));
      state.familyId = 'family-a';
      await f.show(tester, f.mailbox(state, f.mailData()));
      expect(find.text('Bitte Brüche weiter üben.'), findsOneWidget);
      if (changed == 'token') {
        state.api.token = 'a-new-token';
      } else {
        state.familyId = 'family-b';
      }
      state.refreshState();
      await tester.pumpAndSettle();
      expect(find.text('Bitte Brüche weiter üben.'), findsNothing);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    });
  }

  testWidgets('late compose error is not shown after authentication changes', (
    tester,
  ) async {
    final state = f.account((_) async => f.reply({}));
    final pending = Completer<void>();
    await f.show(
      tester,
      ChildMessagesHub(
        state,
        data: f.mailData(),
        onCompose: (_, _) async {},
        onWriteMessage: () => pending.future,
      ),
    );
    await f.tap(tester, find.text('Frage schreiben'));
    state.beginAuthentication();
    pending.completeError(Exception('Alter privater Fehler'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Alter privater Fehler'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });
}
