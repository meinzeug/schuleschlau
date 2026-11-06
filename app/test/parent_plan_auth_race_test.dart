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
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
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
  testWidgets('old topic action requires fresh read after login intent', (
    tester,
  ) async {
    final f = cards.Fixture();
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final old = find.widgetWithText(FilledButton, 'KI-Runde vorbereiten');
    await tester.ensureVisible(old);
    final revision = f.state.beginAuthentication();
    await tester.tap(old);
    await tester.pumpAndSettle();
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(find.text('KI-Runde vorbereiten'), findsOneWidget);
  });

  testWidgets('open assignment editor cannot save after login intent', (
    tester,
  ) async {
    final f = cards.Fixture();
    f.state.user!['families'] = [
      {'id': 'family', 'permission': 'owner'},
    ];
    f.state.familyId = 'family';
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final add = find.text('Eigenes Thema setzen');
    await tester.ensureVisible(add);
    await tester.tap(add);
    await tester.pumpAndSettle();
    expect(find.text('Ein Lernziel vorgeben'), findsOneWidget);
    final revision = f.state.beginAuthentication();
    final save = find.text('Speichern').last;
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    expect(find.text('Ein Lernziel vorgeben'), findsNothing);
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(find.text('Eigenes Thema setzen'), findsOneWidget);
  });

  testWidgets('old topic section cannot be switched after login intent', (
    tester,
  ) async {
    final f = cards.Fixture();
    await f.mount(tester, '/parent-plan/child?ansicht=topics', width: 1280);
    final revision = f.state.beginAuthentication();
    await tester.ensureVisible(find.text('Woche & Vorgaben').first);
    await tester.tap(find.text('Woche & Vorgaben').first);
    await tester.pumpAndSettle();
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Woche & Vorgaben').first);
    await tester.tap(find.text('Woche & Vorgaben').first);
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<ChoiceChip>(
            find.widgetWithText(ChoiceChip, 'Woche & Vorgaben'),
          )
          .selected,
      isTrue,
    );
  });
  testWidgets('late editor save closes and requires an explicit read', (
    tester,
  ) async {
    final f = cards.Fixture();
    f.state.user!['families'] = [
      {'id': 'family', 'permission': 'owner'},
    ];
    f.state.familyId = 'family';
    (f.plan['child'] as Map)['id'] = 'child';
    final pending = Completer<http.Response>();
    f.respond = (request) async {
      if (request.method == 'POST' &&
          request.url.path.endsWith('/assignments')) {
        return pending.future;
      }
      return null;
    };
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final add = find.text('Eigenes Thema setzen');
    await tester.ensureVisible(add);
    await tester.tap(add);
    await tester.pumpAndSettle();
    final fields = find.byType(TextFormField);
    await tester.enterText(fields.at(0), 'Mathematik');
    await tester.enterText(fields.at(1), 'Künstlicher Stoff');
    await tester.ensureVisible(find.text('Speichern').last);
    await tester.tap(find.text('Speichern').last);
    await tester.pump();
    expect(f.requests.where((r) => r.method == 'POST').length, 1);
    final revision = f.state.beginAuthentication();
    pending.complete(cards.response({}));
    await tester.pumpAndSettle();
    expect(find.text('Ein Lernziel vorgeben'), findsNothing);
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(f.requests.where((r) => r.method == 'POST').length, 1);
  });
  testWidgets('pagination cannot fetch old plan after a new login intent', (
    tester,
  ) async {
    final f = cards.Fixture();
    f.plan['pagination'] = {'page': 1, 'pages': 2};
    await f.mount(tester, '/parent-plan/child?ansicht=topics');
    final before = f.requests.length;
    final revision = f.state.beginAuthentication();
    final next = find.text('Nächste Themenseite');
    await tester.ensureVisible(next);
    await tester.tap(next);
    await tester.pumpAndSettle();
    expect(f.requests.length, before);
    expect(find.text('Lernplan erneut laden'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.tap(find.text('Lernplan erneut laden'));
    await tester.pumpAndSettle();
    expect(f.requests.length, before + 1);
  });
}
