import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/school_day_history.dart';
import 'package:schulpilot/ui.dart';

import 'child_history_ux90_test.dart' as history;
import 'child_local_tools_ux88_test.dart' as helpers;
import 'page_tools_test_helpers.dart' as page_tools;

void main() {
  for (final failure in [false, true]) {
    testWidgets(
      'Late history ${failure ? 'failure' : 'response'} is discarded after login intent',
      (t) async {
        final pending = Completer<http.Response>();
        var calls = 0;
        final state = helpers.account((_) {
          calls++;
          if (calls == 1) return pending.future;
          return Future.value(
            helpers.reply({
              'days': [history.day('new', '2026-10-21', 'Biologie')],
              'next_before': null,
            }),
          );
        });
        final router = GoRouter(
          routes: [
            GoRoute(
              path: '/',
              builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
            ),
          ],
        );
        addTearDown(() async {
          await t.pumpWidget(const SizedBox.shrink());
          router.dispose();
          state.dispose();
        });
        await t.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: router),
        );
        await t.pump();
        expect(calls, 1);
        final intent = state.beginAuthentication();
        if (failure) {
          pending.complete(http.Response('private old error', 500));
        } else {
          pending.complete(
            helpers.reply({
              'days': [history.day('old', '2026-10-20', 'Mathematik')],
              'next_before': null,
            }),
          );
        }
        await t.pumpAndSettle();
        expect(find.textContaining('Mathematik'), findsNothing);
        expect(find.textContaining('private old error'), findsNothing);
        expect(
          find.text('Bitte lade deine Tagespakete erneut.'),
          findsOneWidget,
        );
        expect(calls, 1);
        state.cancelAuthentication(intent);
        await t.pumpAndSettle();
        await helpers.tap(t, find.text('Erneut laden'));
        expect(find.text('Tagespaket vom 21.10.2026 öffnen'), findsOneWidget);
        expect(calls, 2);
        expect(t.takeException(), isNull);
      },
    );
  }
  testWidgets(
    'An older history response cannot overwrite an explicit later reload',
    (t) async {
      final old = Completer<http.Response>();
      var calls = 0;
      final state = helpers.account((_) {
        calls++;
        return calls == 1
            ? old.future
            : Future.value(
                helpers.reply({
                  'days': [history.day('new', '2026-10-21', 'Biologie')],
                  'next_before': null,
                }),
              );
      });
      final router = GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
          ),
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox.shrink());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pump();
      final intent = state.beginAuthentication();
      state.cancelAuthentication(intent);
      await t.pumpAndSettle();
      await helpers.tap(t, find.text('Erneut laden'));
      expect(find.text('Tagespaket vom 21.10.2026 öffnen'), findsOneWidget);
      old.complete(
        helpers.reply({
          'days': [history.day('old', '2026-10-20', 'Mathematik')],
          'next_before': null,
        }),
      );
      await t.pumpAndSettle();
      expect(find.text('Tagespaket vom 21.10.2026 öffnen'), findsOneWidget);
      expect(find.textContaining('Mathematik'), findsNothing);
      expect(calls, 2);
    },
  );

  testWidgets(
    'A previously rendered day action cannot navigate after login intent',
    (t) async {
      final state = helpers.account(
        (_) async => helpers.reply({
          'days': [history.day('old', '2026-10-20', 'Mathematik')],
          'next_before': null,
        }),
      );
      VoidCallback? earlyAction;
      state.authenticationChanges.addListener(() => earlyAction?.call());
      final router = GoRouter(
        routes: [
          GoRoute(
            path: '/',
            builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
          ),
          GoRoute(
            path: '/after-school/:id',
            builder: (_, _) => const Scaffold(body: Text('Altes Ziel')),
          ),
        ],
      );
      addTearDown(() async {
        await t.pumpWidget(const SizedBox.shrink());
        router.dispose();
        state.dispose();
      });
      await t.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await t.pumpAndSettle();
      final panel = t.widget<ActionPanel>(
        find.byWidgetPredicate(
          (w) =>
              w is ActionPanel &&
              w.actionLabel == 'Tagespaket vom 20.10.2026 öffnen',
        ),
      );
      earlyAction = () => panel.onPressed!();
      state.beginAuthentication();
      await t.pumpAndSettle();
      expect(find.text('Altes Ziel'), findsNothing);
      expect(find.textContaining('Mathematik'), findsNothing);
    },
  );
  testWidgets('retry stays disabled until login is canceled', (t) async {
    var calls = 0;
    final state = helpers.account((_) async {
      calls++;
      return helpers.reply({
        'days': [history.day('old', '2026-10-20', 'Mathematik')],
        'next_before': null,
      });
    });
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    final revision = state.beginAuthentication();
    await t.pumpAndSettle();
    final retry = t.widget<ActionButton>(
      find.widgetWithText(ActionButton, 'Erneut laden'),
    );
    expect(retry.enabled, isFalse);
    await retry.onPressed();
    await t.pump();
    expect(calls, 1);
    expect(find.textContaining('Mathematik'), findsNothing);
    state.cancelAuthentication(revision);
    await t.pumpAndSettle();
    await helpers.tap(t, find.text('Erneut laden'));
    expect(calls, 2);
    expect(find.text('Tagespaket vom 20.10.2026 öffnen'), findsOneWidget);
    expect(t.takeException(), isNull);
  });

  testWidgets('history opened during login reads no private data', (t) async {
    var calls = 0;
    final state = helpers.account((_) async {
      calls++;
      return helpers.reply({'days': [], 'next_before': null});
    });
    state.collectionViews['school_history:child'] = {
      'account': state.user,
      'family': state.familyId,
      'q': 'privater Suchtext',
    };
    final revision = state.beginAuthentication();
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    expect(calls, 0);
    expect(find.text('privater Suchtext'), findsNothing);
    expect(
      t
          .widget<ActionButton>(
            find.widgetWithText(ActionButton, 'Erneut laden'),
          )
          .enabled,
      isFalse,
    );
    state.cancelAuthentication(revision);
    await t.pumpAndSettle();
    expect(calls, 0);
    await helpers.tap(t, find.text('Erneut laden'));
    expect(calls, 1);
    expect(t.takeException(), isNull);
  });

  testWidgets('An open date picker closes after a new login intent', (t) async {
    final state = helpers.account(
      (_) async => helpers.reply({
        'days': [history.day('old', '2026-10-20', 'Mathematik')],
        'next_before': null,
      }),
    );
    final router = GoRouter(
      routes: [
        GoRoute(
          path: '/',
          builder: (_, _) => SchoolDayHistory(state, childId: 'child'),
        ),
      ],
    );
    addTearDown(() async {
      await t.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await t.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await t.pumpAndSettle();
    await page_tools.openPageTools(t);
    await helpers.tap(t, find.text('Zu einem Datum'));
    expect(find.text('Tage anzeigen'), findsOneWidget);
    state.beginAuthentication();
    await t.pumpAndSettle();
    expect(find.text('Tage anzeigen'), findsNothing);
    expect(find.textContaining('Mathematik'), findsNothing);
    expect(t.takeException(), isNull);
  });
}
