import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'progress_grades_test.dart' as fixtures;
import 'parent_workflows_ux90_test.dart' as workflows;

void main() {
  testWidgets(
    'changing the selected child does not reopen grades during a pending login',
    (tester) async {
      final requests = <http.Request>[];
      final f = await fixtures.mount(tester, (request) async {
        requests.add(request);
        return fixtures.reply(fixtures.grades());
      }, gradePage: true);
      final intent = f.state.beginAuthentication();
      await tester.pumpAndSettle();
      final before = requests.length;
      f.router.go('/grades/kid2');
      await tester.pumpAndSettle();
      expect(requests, hasLength(before));
      expect(
        tester
            .widget<FilledButton>(
              find.widgetWithText(FilledButton, 'Noten erneut laden'),
            )
            .onPressed,
        isNull,
      );
      f.state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Noten erneut laden'));
      await tester.pumpAndSettle();
      expect(
        requests.any((r) => r.url.path == '/api/children/kid2/grades'),
        isTrue,
      );
    },
  );

  testWidgets('a grade draft cannot resume while login is still pending', (
    tester,
  ) async {
    final requests = <http.Request>[];
    final f = await fixtures.mount(tester, (request) async {
      requests.add(request);
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    final intent = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    final count = requests.length;
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Zugang prüfen'),
          )
          .onPressed,
      isNull,
    );
    expect(requests, hasLength(count));
    f.state.cancelAuthentication(intent);
    await tester.pump();
    expect(
      tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Zugang prüfen'),
          )
          .onPressed,
      isNotNull,
    );
  });

  testWidgets(
    'an old save button cannot submit after the draft is reauthorized',
    (tester) async {
      final posts = <http.Request>[];
      final f = await fixtures.mount(tester, (request) async {
        if (request.method == 'POST') {
          posts.add(request);
          return fixtures.reply({});
        }
        if (request.url.path.endsWith('/auth/me')) {
          return fixtures.reply({
            'id': 'owned-user',
            'role': 'parent',
            'session_assertion': 'a' * 64,
          });
        }
        return fixtures.reply(fixtures.grades());
      }, gradePage: true);
      f.state.user!['session_assertion'] = 'a' * 64;
      await tester.ensureVisible(find.text('Note eintragen'));
      await tester.tap(find.text('Note eintragen'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
      await tester.enterText(find.byType(TextFormField).at(2), '3');
      await tester.pumpAndSettle();
      final oldSave = tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Speichern'))
          .onPressed!;
      final intent = f.state.beginAuthentication();
      await tester.pumpAndSettle();
      f.state.cancelAuthentication(intent);
      await tester.pump();
      await tester.tap(find.text('Zugang prüfen'));
      await tester.pumpAndSettle();
      oldSave();
      await tester.pumpAndSettle();
      expect(posts, isEmpty);
      expect(find.text('Speichern'), findsOneWidget);
    },
  );

  testWidgets(
    'an older discard confirmation cannot discard a draft after another login intent',
    (tester) async {
      final f = await fixtures.mount(tester, (request) async {
        if (request.url.path.endsWith('/auth/me')) {
          return fixtures.reply({
            'id': 'owned-user',
            'role': 'parent',
            'session_assertion': 'a' * 64,
          });
        }
        return fixtures.reply(fixtures.grades());
      }, gradePage: true);
      f.state.user!['session_assertion'] = 'a' * 64;
      await tester.ensureVisible(find.text('Note eintragen'));
      await tester.tap(find.text('Note eintragen'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
      f.state.beginAuthentication();
      await tester.pumpAndSettle();
      await tester.tap(find.text('Schließen').last);
      await tester.pumpAndSettle();
      final oldDiscard = tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Änderungen verwerfen'),
          )
          .onPressed!;
      final intent = f.state.beginAuthentication();
      oldDiscard();
      await tester.pumpAndSettle();
      expect(find.text('Anmeldung geändert'), findsOneWidget);
      f.state.cancelAuthentication(intent);
      await tester.pump();
      await tester.tap(find.text('Zugang prüfen'));
      await tester.pumpAndSettle();
      expect(find.text('Mathematik'), findsWidgets);
    },
  );

  testWidgets(
    'a grade goal dialog closes and its old action is inert on login intent',
    (tester) async {
      final f = workflows.collection();
      f.gradeData['can_manage'] = true;
      f.gradeData['items'][0]['revision'] = 7;
      await f.mount(tester, '/grades/child');
      await workflows.tap(tester, find.text('Passendes Lernziel anlegen'));
      final oldAction = tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Lernziel anlegen'),
          )
          .onPressed!;
      f.state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Passendes Lernziel anlegen?'), findsNothing);
      oldAction();
      await tester.pumpAndSettle();
      expect(f.requests.where((r) => r.method == 'POST'), isEmpty);
    },
  );

  testWidgets('system back asks before discarding a blocked grade draft', (
    tester,
  ) async {
    final f = await fixtures.mount(
      tester,
      (request) async => fixtures.reply(fixtures.grades()),
      gradePage: true,
    );
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.text('Änderungen verwerfen?'), findsOneWidget);
    await tester.tap(find.text('Weiterbearbeiten'));
    await tester.pumpAndSettle();
    expect(find.text('Anmeldung geändert'), findsOneWidget);
    expect(find.byType(TextFormField), findsNothing);
  });

  testWidgets('an old save cannot finish a newer grade retry', (tester) async {
    final first = Completer<http.Response>(),
        second = Completer<http.Response>();
    final posts = <http.Request>[];
    final f = await fixtures.mount(tester, (request) async {
      if (request.method == 'POST') {
        posts.add(request);
        return posts.length == 1 ? first.future : second.future;
      }
      if (request.url.path.endsWith('/auth/me')) {
        return fixtures.reply({
          'id': 'owned-user',
          'role': 'parent',
          'session_assertion': 'a' * 64,
        });
      }
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    f.state.user!['session_assertion'] = 'a' * 64;
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    await tester.enterText(find.byType(TextFormField).at(2), '3');
    await tester.tap(find.text('Speichern'));
    await tester.pump();
    expect(posts, hasLength(1));
    final revision = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    f.state.cancelAuthentication(revision);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Speichern'));
    await tester.pump();
    expect(posts, hasLength(2));
    first.complete(fixtures.reply({'id': 'first'}));
    await tester.pump();
    expect(
      tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'Speichern'))
          .onPressed,
      isNull,
    );
    second.complete(fixtures.reply({'id': 'second'}));
    await tester.pumpAndSettle();
    expect(find.text('Noten erneut laden'), findsOneWidget);
    expect(
      posts.first.headers['Idempotency-Key'],
      posts.last.headers['Idempotency-Key'],
    );
  });

  testWidgets('revoked child grade access keeps the draft hidden', (
    tester,
  ) async {
    var gradeReads = 0;
    final f = await fixtures.mount(tester, (request) async {
      expect(request.method, 'GET');
      if (request.url.path.endsWith('/auth/me')) {
        return fixtures.reply({
          'id': 'owned-user',
          'role': 'parent',
          'session_assertion': 'a' * 64,
        });
      }
      gradeReads++;
      return fixtures.reply(fixtures.grades(manage: gradeReads == 1));
    }, gradePage: true);
    f.state.user!['session_assertion'] = 'a' * 64;
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    final revision = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    f.state.cancelAuthentication(revision);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsNothing);
    expect(
      find.textContaining('Der Zugang konnte nicht geprüft'),
      findsOneWidget,
    );
  });

  testWidgets('a different account closes the blocked grade draft', (
    tester,
  ) async {
    final f = await fixtures.mount(tester, (request) async {
      expect(request.method, 'GET');
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Anmeldung geändert'), findsOneWidget);
    f.state.user = {'id': 'other', 'role': 'parent'};
    f.state.notifyListeners();
    await tester.pumpAndSettle();
    expect(find.text('Anmeldung geändert'), findsNothing);
    expect(find.byType(TextFormField), findsNothing);
  });

  testWidgets('an unverifiable browser session cannot reopen the draft', (
    tester,
  ) async {
    final f = await fixtures.mount(tester, (request) async {
      expect(request.method, 'GET');
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    final revision = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    f.state.cancelAuthentication(revision);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsNothing);
    expect(find.textContaining('nicht sicher wieder öffnen'), findsOneWidget);
  });

  testWidgets('an uncertain grade save keeps its original key and draft', (
    tester,
  ) async {
    final receipt = Completer<http.Response>();
    final posts = <http.Request>[];
    final f = await fixtures.mount(tester, (request) async {
      if (request.method == 'POST') {
        posts.add(request);
        if (posts.length == 1) return receipt.future;
        return fixtures.reply({'id': 'new-grade'});
      }
      if (request.url.path.endsWith('/auth/me')) {
        return fixtures.reply({
          'id': 'owned-user',
          'role': 'parent',
          'session_assertion': 'a' * 64,
        });
      }
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    f.state.user!['session_assertion'] = 'a' * 64;
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    await tester.enterText(find.byType(TextFormField).at(2), '3');
    await tester.tap(find.text('Speichern'));
    await tester.pump();
    expect(posts, hasLength(1));
    final revision = f.state.beginAuthentication();
    receipt.complete(fixtures.reply({'id': 'new-grade'}));
    await tester.pumpAndSettle();
    expect(find.textContaining('kann bereits übernommen'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    expect(posts, hasLength(1));
    await tester.enterText(find.byType(TextFormField).at(2), '2');
    await tester.tap(find.text('Speichern'));
    await tester.pumpAndSettle();
    expect(posts, hasLength(1));
    expect(
      find.textContaining('vorherige Speicherversuch ist noch unklar'),
      findsOneWidget,
    );
    await tester.enterText(find.byType(TextFormField).at(2), '3');
    await tester.tap(find.text('Speichern'));
    await tester.pumpAndSettle();
    expect(posts, hasLength(2));
    expect(
      posts.first.headers['Idempotency-Key'],
      posts.last.headers['Idempotency-Key'],
    );
    expect(find.text('Noten erneut laden'), findsOneWidget);
  });

  testWidgets('an unsaved grade draft returns only after a deliberate reload', (
    tester,
  ) async {
    final methods = <String>[];
    final f = await fixtures.mount(tester, (request) async {
      methods.add(request.method);
      expect(request.method, 'GET');
      if (request.url.path.endsWith('/auth/me')) {
        return fixtures.reply({
          'id': 'owned-user',
          'role': 'parent',
          'session_assertion': 'a' * 64,
        });
      }
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    f.state.user!['session_assertion'] = 'a' * 64;
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    await tester.enterText(find.byType(TextFormField).at(2), '3');
    final revision = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Notenschnitt: 4,5'), findsNothing);
    expect(find.byType(TextFormField), findsNothing);
    f.state.notifyListeners();
    await tester.pumpAndSettle();
    expect(find.text('Anmeldung geändert'), findsOneWidget);
    f.state.cancelAuthentication(revision);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    expect(find.text('Mathematik'), findsWidgets);
    expect(
      tester
          .widget<TextFormField>(find.byType(TextFormField).at(2))
          .controller!
          .text,
      '3',
    );
    expect(methods.every((method) => method == 'GET'), isTrue);
  });

  testWidgets('a queued grade save cannot run after login starts', (
    tester,
  ) async {
    final methods = <String>[];
    final f = await fixtures.mount(tester, (request) async {
      methods.add(request.method);
      return fixtures.reply(
        request.method == 'GET' ? fixtures.grades() : {'id': 'synthetic-grade'},
      );
    }, gradePage: true);
    await tester.ensureVisible(find.text('Note eintragen'));
    await tester.tap(find.text('Note eintragen'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextFormField).at(0), 'Mathematik');
    await tester.enterText(find.byType(TextFormField).at(2), '3');
    final save = tester
        .widget<FilledButton>(find.widgetWithText(FilledButton, 'Speichern'))
        .onPressed!;
    final revision = f.state.beginAuthentication();
    save();
    await tester.pumpAndSettle();
    expect(methods.where((method) => method != 'GET'), isEmpty);
    f.state.cancelAuthentication(revision);
  });

  testWidgets('a new login immediately hides the previous grade overview', (
    tester,
  ) async {
    var reads = 0;
    final f = await fixtures.mount(tester, (request) async {
      expect(request.method, 'GET');
      reads++;
      return fixtures.reply(fixtures.grades());
    }, gradePage: true);
    expect(find.text('Notenschnitt: 4,5'), findsOneWidget);
    final before = reads;
    final revision = f.state.beginAuthentication();
    await tester.pump();
    expect(find.text('Notenschnitt: 4,5'), findsNothing);
    expect(find.text('Noten erneut laden'), findsOneWidget);
    expect(reads, before);
    f.state.cancelAuthentication(revision);
  });
}
