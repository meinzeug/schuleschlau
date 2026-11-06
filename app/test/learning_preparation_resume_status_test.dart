import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_preparation_screen.dart';
import 'package:schulpilot/ui.dart';

import 'learning_continuation_test.dart' as fixture;

void main() {
  testWidgets('resume waits for the old status before the next read', (
    tester,
  ) async {
    final oldRead = Completer<http.Response>();
    final newRead = Completer<http.Response>();
    var reads = 0;
    final state = fixture.stateFor((request) async {
      expect(request.method, 'GET');
      reads++;
      return reads == 1 ? oldRead.future : newRead.future;
    });
    final router = fixture.routerFor(
      state,
      LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
    );
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.dispose();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    await tester.pump();
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(reads, 1);
    oldRead.complete(fixture.response({'kind': 'unit', 'status': 'running'}));
    await tester.pump();
    await tester.pump();
    expect(reads, 2);
    newRead.complete(
      fixture.response({
        'kind': 'unit',
        'status': 'completed',
        'result': {'unit_id': 'ready'},
      }),
    );
    await tester.pumpAndSettle();
    expect(reads, 2);
    expect(find.text('Deine Runde ist bereit.'), findsOneWidget);
    expect(find.text('Status neu laden'), findsNothing);
  });

  testWidgets(
    'old status after login intent cannot overwrite explicit refresh',
    (tester) async {
      final oldRead = Completer<http.Response>();
      var reads = 0;
      final state = fixture.stateFor((request) async {
        expect(request.method, 'GET');
        reads++;
        if (reads == 1) return oldRead.future;
        return fixture.response({
          'kind': 'unit',
          'status': 'completed',
          'result': {'unit_id': 'ready'},
        });
      });
      final router = fixture.routerFor(
        state,
        LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
      );
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
        tester.binding.handleAppLifecycleStateChanged(
          AppLifecycleState.resumed,
        );
      });
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      state.beginAuthentication();
      expect(reads, 1);
      oldRead.complete(fixture.response({'kind': 'unit', 'status': 'running'}));
      await tester.pump();
      await tester.pump();
      expect(reads, 1);
      expect(find.text('Status neu laden'), findsOneWidget);
      await tester.tap(find.text('Status neu laden'));
      await tester.pumpAndSettle();
      expect(reads, 2);
      expect(find.text('Deine Runde ist bereit.'), findsOneWidget);
      expect(find.text('Status neu laden'), findsNothing);
    },
  );

  for (final responseAfterResume in [false, true]) {
    testWidgets(
      'preparation refreshes after resuming around an unavailable status $responseAfterResume',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final delayed = Completer<http.Response>();
        final methods = <String>[];
        var reads = 0;
        final state = fixture.stateFor((request) async {
          methods.add(request.method);
          reads++;
          if (reads == 1) {
            if (responseAfterResume) return delayed.future;
            return fixture.response({'detail': 'Offline'}, 503);
          }
          return fixture.response({
            'kind': 'unit',
            'status': 'completed',
            'result': {'unit_id': 'ready'},
          });
        });
        final router = fixture.routerFor(
          state,
          LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
        );
        addTearDown(() async {
          await tester.pumpWidget(const SizedBox());
          router.dispose();
          state.dispose();
          tester.binding.handleAppLifecycleStateChanged(
            AppLifecycleState.resumed,
          );
        });
        await tester.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: router),
        );
        await tester.pump();
        await tester.pump();
        expect(reads, 1);
        if (!responseAfterResume) {
          expect(find.text('Status neu laden'), findsOneWidget);
        }
        tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
        await tester.pump();
        tester.binding.handleAppLifecycleStateChanged(
          AppLifecycleState.resumed,
        );
        await tester.pump();
        if (responseAfterResume) {
          delayed.complete(fixture.response({'detail': 'Offline'}, 503));
        }
        await tester.pumpAndSettle();
        expect(reads, 2);
        expect(methods, ['GET', 'GET']);
        expect(find.text('Deine Runde ist bereit.'), findsOneWidget);
        expect(find.text('Los geht’s'), findsOneWidget);
      },
    );

    testWidgets('rate limit is not bypassed on resume $responseAfterResume', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final delayed = Completer<http.Response>();
      var reads = 0;
      final state = fixture.stateFor((request) async {
        expect(request.method, 'GET');
        reads++;
        if (responseAfterResume) return delayed.future;
        return fixture.response({'detail': 'Später erneut versuchen'}, 429);
      });
      final router = fixture.routerFor(
        state,
        LearningPreparationScreen(state, childId: 'child', jobId: 'job'),
      );
      addTearDown(() async {
        await tester.pumpWidget(const SizedBox());
        router.dispose();
        state.dispose();
        tester.binding.handleAppLifecycleStateChanged(
          AppLifecycleState.resumed,
        );
      });
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pump();
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      await tester.pump();
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump();
      if (responseAfterResume) {
        delayed.complete(
          fixture.response({'detail': 'Später erneut versuchen'}, 429),
        );
      }
      await tester.pumpAndSettle();
      expect(reads, 1);
      expect(find.text('Status neu laden'), findsOneWidget);
    });
  }
}
