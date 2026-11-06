import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'parent_cards_ux88_test.dart' as cards;
import 'parent_hierarchy_test_tools.dart';

void main() {
  testWidgets('a stale confirmation closes without changing an assignment', (
    tester,
  ) async {
    final f = cards.Fixture();
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    await openParentDetails103(tester, 'Auftrag verwalten');
    final complete = find.text('Als erledigt markieren');
    await tester.ensureVisible(complete.first);
    await tester.tap(complete.first);
    await tester.pumpAndSettle();
    final revision = f.state.beginAuthentication();
    await tester.tap(find.text('Bestätigen').last);
    await tester.pumpAndSettle();
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    expect(find.text('Thema als erledigt markieren?'), findsNothing);
    f.state.cancelAuthentication(revision);
  });

  testWidgets('a late refresh is discarded and can be retried after login', (
    tester,
  ) async {
    final f = cards.Fixture();
    final pending = Completer<http.Response>();
    var reads = 0;
    f.respond = (request) async {
      if (request.url.path.endsWith('/learning-plan')) {
        reads++;
        if (reads == 2) return pending.future;
      }
      return null;
    };
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final refresh = find.byTooltip('Aktualisieren');
    await tester.ensureVisible(refresh.first);
    await tester.tap(refresh.first);
    await tester.pump();
    expect(reads, 2);
    final revision = f.state.beginAuthentication();
    final stale = Map<String, dynamic>.from(f.plan);
    stale['topics'] = [
      {
        ...Map<String, dynamic>.from((f.plan['topics'] as List).first),
        'topic': 'Veralteter Lernstoff',
      },
    ];
    pending.complete(cards.response(stale));
    await tester.pumpAndSettle();
    expect(find.textContaining('Veralteter Lernstoff'), findsNothing);
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    expect(find.textContaining('Bruchaddition'), findsNothing);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(reads, 3);
    expect(find.textContaining('Bruchaddition'), findsWidgets);
  });

  testWidgets('late completion requires a read-only refresh after login', (
    tester,
  ) async {
    final f = cards.Fixture();
    final pending = Completer<http.Response>();
    f.respond = (request) async {
      if (request.method == 'POST' && request.url.path.endsWith('/complete')) {
        return pending.future;
      }
      return null;
    };
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    await openParentDetails103(tester, 'Auftrag verwalten');
    await tester.tap(find.text('Als erledigt markieren').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bestätigen').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump();
    expect(f.requests.where((r) => r.method == 'POST').length, 1);
    final revision = f.state.beginAuthentication();
    pending.complete(cards.response({}));
    await tester.pumpAndSettle();
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    expect(find.textContaining('Bruchaddition'), findsNothing);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(f.requests.where((r) => r.method == 'POST').length, 1);
    expect(find.textContaining('Bruchaddition'), findsWidgets);
  });

  testWidgets('late preparation cannot navigate after a new login intent', (
    tester,
  ) async {
    final f = cards.Fixture();
    final pending = Completer<http.Response>();
    var attempts = 0;
    f.respond = (request) async {
      if (request.method == 'POST' && request.url.path.endsWith('/prepare')) {
        attempts++;
        if (attempts == 1) return pending.future;
        return cards.response({'kind': 'unit', 'id': 'fresh'});
      }
      return null;
    };
    final router = await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final prepare = find.widgetWithText(FilledButton, 'KI-Runde vorbereiten');
    await tester.ensureVisible(prepare);
    await tester.pumpAndSettle();
    await tester.tap(prepare);
    await tester.pump();
    expect(attempts, 1);
    final revision = f.state.beginAuthentication();
    pending.complete(cards.response({'kind': 'unit', 'id': 'old'}));
    await tester.pumpAndSettle();
    expect(
      router.routeInformationProvider.value.uri.path,
      '/parent-plan/child',
    );
    expect(find.text('Ziel /unit/old'), findsNothing);
    f.state.cancelAuthentication(revision);
    final retry = find.widgetWithText(FilledButton, 'Anfrage abgleichen');
    expect(retry, findsOneWidget);
    await tester.ensureVisible(retry);
    await tester.tap(retry);
    await tester.pumpAndSettle();
    expect(attempts, 2);
    expect(find.text('Ziel /unit/fresh'), findsOneWidget);
    final posts = f.requests.where((r) => r.method == 'POST').toList();
    expect(
      posts.first.headers['Idempotency-Key'],
      posts.last.headers['Idempotency-Key'],
    );
  });
}
