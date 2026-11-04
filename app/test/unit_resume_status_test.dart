import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/unit_screen.dart';

import 'learning_room_test.dart' as room;
import 'unit_learning_time_test.dart' as time;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final status in [403, 404]) {
    testWidgets('a $status response removes the previously loaded round', (
      tester,
    ) async {
      final server = room.SavedRound();
      var reads = 0;
      final h = await room.openRound(
        tester,
        server,
        handle: (request) async {
          if (request.method == 'GET' &&
              request.url.path == '/api/units/unit') {
            reads++;
            return reads == 1
                ? room.jsonReply(server.value)
                : room.jsonReply({
                    'detail': 'Diese Runde ist nicht mehr verfügbar.',
                  }, status);
          }
          return server.handle(request);
        },
      );
      await h.state.learningDrafts.save('own-child', 'unit', {
        'answer': 'Ein gespeicherter Entwurf',
        'source_signature': 'source',
      });
      time.background(tester);
      await tester.pump();
      time.resume(tester);
      await tester.pumpAndSettle();
      final dynamic visibleState = tester.state(find.byType(UnitScreen));
      expect(visibleState.unit, isNull);
      expect(
        find.text('Diese Runde ist nicht mehr verfügbar.'),
        findsOneWidget,
      );
      expect(reads, 2);
      expect(server.answers, 0);
      expect(
        (await h.state.learningDrafts.get('own-child', 'unit'))?['answer'],
        'Ein gespeicherter Entwurf',
      );
      await h.close();
    });
  }
  for (final rateLimited in [false, true]) {
    testWidgets(
      'resume while reading a round ${rateLimited ? 'respects the rate limit' : 'loads the current state once'}',
      (tester) async {
        final server = room.SavedRound(
          questions: [room.question('cat', type: 'short')],
        );
        final pending = Completer<http.Response>();
        var reads = 0;
        final h = await room.openRound(
          tester,
          server,
          handle: (request) async {
            if (request.method == 'GET' &&
                request.url.path == '/api/units/unit') {
              reads++;
              if (reads == 2) return pending.future;
              return room.jsonReply(server.value);
            }
            return server.handle(request);
          },
        );
        addTearDown(() {
          if (!pending.isCompleted) {
            pending.complete(room.jsonReply(server.value));
          }
          time.resume(tester);
        });
        expect(reads, 1);
        await tester.enterText(find.byType(TextField).first, 'Meine Antwort');
        await tester.pump();
        time.background(tester);
        await tester.pump();
        time.resume(tester);
        await tester.pump();
        expect(reads, 2);
        time.background(tester);
        await tester.pump();
        time.resume(tester);
        await tester.pump();
        final old = Map<String, dynamic>.from(server.value);
        server.value['status'] = 'paused';
        pending.complete(
          rateLimited
              ? room.jsonReply({
                  'detail': 'Bitte später erneut versuchen.',
                }, 429)
              : room.jsonReply(old),
        );
        await tester.pumpAndSettle();
        await tester.pump(const Duration(milliseconds: 50));
        await tester.pumpAndSettle();
        expect(reads, rateLimited ? 2 : 3);
        if (rateLimited) {
          expect(find.text('Bitte später erneut versuchen.'), findsOneWidget);
          time.background(tester);
          await tester.pump();
          time.resume(tester);
          await tester.pump(const Duration(seconds: 4));
          expect(reads, 2);
          await tester.tap(find.text('Erneut versuchen'));
          await tester.pumpAndSettle();
          expect(reads, 3);
        } else {
          final dynamic visibleState = tester.state(find.byType(UnitScreen));
          expect(visibleState.unit['status'], 'paused');
        }
        final dynamic roundState = tester.state(find.byType(UnitScreen));
        expect(roundState.text.text, 'Meine Antwort');
        expect(server.answers, 0);
        expect(server.calls.where((v) => v.contains('/answer')), isEmpty);
        await h.close();
      },
    );
  }

  testWidgets('a replaced session discards a delayed response', (tester) async {
    final server = room.SavedRound();
    final pending = Completer<http.Response>();
    var reads = 0;
    final h = await room.openRound(
      tester,
      server,
      handle: (request) async {
        if (request.method == 'GET' &&
            request.url.path == '/api/units/unit' &&
            ++reads == 2) {
          return pending.future;
        }
        return server.handle(request);
      },
    );
    addTearDown(() {
      if (!pending.isCompleted) pending.complete(room.jsonReply(server.value));
      time.resume(tester);
    });
    time.background(tester);
    await tester.pump();
    time.resume(tester);
    await tester.pump();
    h.state.api.token = 'new-session';
    unawaited(h.state.setAppearance(false));
    await tester.pump();
    pending.complete(room.jsonReply(server.value));
    await tester.pumpAndSettle();
    expect(find.text('Bitte melde dich erneut an.'), findsOneWidget);
    expect(find.text('Was bedeutet cat?'), findsNothing);
    expect(server.answers, 0);
    await h.close();
  });
}
