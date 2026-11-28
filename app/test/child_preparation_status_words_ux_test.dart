import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as fixture;

void main() {
  for (final (kind, status, heading, detail) in [
    (
      'decision',
      'queued',
      'Dein Lernplan wartet.',
      'Du kannst später zurückkommen.',
    ),
    (
      'decision',
      'running',
      'Dein Lernplan entsteht …',
      'Deine Lernhilfe plant den nächsten Schritt. Du kannst später zurückkommen.',
    ),
    ('unit', 'queued', 'Deine Runde wartet.', 'Du kannst später zurückkommen.'),
    (
      'unit',
      'running',
      'Deine Runde entsteht …',
      'Deine Lernhilfe bereitet passende Aufgaben vor. Du kannst später zurückkommen.',
    ),
  ]) {
    for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
      testWidgets('$kind $status uses accurate wording at $width / $scale×', (
        tester,
      ) async {
        final calls = <http.Request>[];
        final state = fixture.account((request) async {
          calls.add(request);
          return fixture.reply({'kind': kind, 'status': status});
        });
        tester.view.physicalSize = Size(width, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final router = GoRouter(
          routes: [
            GoRoute(
              path: '/',
              builder: (_, _) => LearningPreparationScreen(
                state,
                childId: 'child',
                jobId: 'job',
              ),
            ),
          ],
        );
        addTearDown(router.dispose);
        await tester.pumpWidget(
          MaterialApp.router(
            theme: appTheme(),
            routerConfig: router,
            builder: (ctx, child) => MediaQuery(
              data: MediaQuery.of(ctx)
                  .copyWith(textScaler: TextScaler.linear(scale)),
              child: child!,
            ),
          ),
        );
        await tester.pump();
        await tester.pump();
        expect(find.text(heading), findsOneWidget);
        expect(find.text(detail), findsOneWidget);
        expect(find.text('Zur Startseite'), findsOneWidget);
        if (kind == 'decision') {
          expect(
            find.text(
              'Deine Lernhilfe bereitet passende Aufgaben vor. Du kannst später zurückkommen.',
            ),
            findsNothing,
          );
        }
        await tester.pump(const Duration(seconds: 4));
        await tester.pump();
        expect(calls.length, greaterThanOrEqualTo(2));
        expect(calls.every((r) => r.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox.shrink());
        state.dispose();
      });
    }
  }

  for (final login in [true, false]) {
    testWidgets(
      'Late preparation status cannot cross ${login ? 'a sign-in' : 'account replacement'}',
      (tester) async {
        final pending = Completer<http.Response>();
        final calls = <http.Request>[];
        final state = fixture.account((request) {
          calls.add(request);
          return pending.future;
        });
        final router = GoRouter(
          routes: [
            GoRoute(
              path: '/',
              builder: (_, _) => LearningPreparationScreen(
                state,
                childId: 'child',
                jobId: 'job',
              ),
            ),
          ],
        );
        addTearDown(router.dispose);
        await tester.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: router),
        );
        await tester.pump();
        if (login) {
          state.beginAuthentication();
        } else {
          state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
        }
        pending.complete(
          fixture.reply({'kind': 'decision', 'status': 'running'}),
        );
        await tester.pump();
        await tester.pump(const Duration(seconds: 4));
        expect(find.text('Dein Lernplan entsteht …'), findsNothing);
        expect(calls.every((r) => r.method == 'GET'), isTrue);
        expect(calls, hasLength(1));
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox.shrink());
        state.dispose();
      },
    );
  }
}
