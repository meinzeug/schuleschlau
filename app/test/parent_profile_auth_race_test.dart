import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'parent_profile_ux90_test.dart' as profile;
import 'parent_workflows_ux90_test.dart' show field, tap;
import 'parent_hierarchy_test_tools.dart';

void main() {
  testWidgets('profile cannot be opened during authentication', (tester) async {
    final f = profile.Fixture();
    f.state.beginAuthentication();
    await f.open(tester);
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(f.requests, isEmpty);
  });

  testWidgets('a new authentication intent removes a private profile draft', (
    tester,
  ) async {
    final f = profile.Fixture();
    await f.open(tester);
    await tester.enterText(
      field('Anzeigename'),
      'Privater künstlicher Entwurf',
    );
    final intent = f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(find.text('Privater künstlicher Entwurf'), findsNothing);
    expect(f.requests, isEmpty);
    f.state.cancelAuthentication(intent);
    await tester.pumpAndSettle();
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    await tap(tester, find.text('Öffnen'));
    expect(
      tester.widget<TextField>(field('Anzeigename')).controller!.text,
      f.child['display_name'],
    );
  });

  testWidgets('login closes profile and discard dialog without writing', (
    tester,
  ) async {
    final f = profile.Fixture();
    await f.open(tester);
    await tester.enterText(
      field('Anzeigename'),
      'Privater künstlicher Entwurf',
    );
    await tap(tester, find.text('Abbrechen'));
    expect(find.text('Weiterbearbeiten'), findsOneWidget);
    f.state.beginAuthentication();
    await tester.pumpAndSettle();
    expect(find.text('Weiterbearbeiten'), findsNothing);
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(f.requests, isEmpty);
  });

  testWidgets('late profile comparison is discarded after login starts', (
    tester,
  ) async {
    final f = profile.Fixture();
    final late = Completer<http.Response>();
    f.respond = (_) => late.future;
    await f.open(tester);
    await openParentDetails103(tester, 'Entwurf & gespeicherter Stand');
    await tester.ensureVisible(find.text('Gespeicherten Stand vergleichen'));
    await tester.tap(find.text('Gespeicherten Stand vergleichen'));
    await tester.pump();
    f.state.beginAuthentication();
    await tester.pump();
    late.complete(
      f.response({
        'children': [
          {...f.child, 'display_name': 'Späte private Daten'},
        ],
      }),
    );
    await tester.pumpAndSettle();
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(find.textContaining('Späte private Daten'), findsNothing);
    expect(f.requests.where((r) => r.method != 'GET'), isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('late save does not report success into a new login', (
    tester,
  ) async {
    final f = profile.Fixture();
    final late = Completer<http.Response>();
    f.respond = (_) => late.future;
    await f.open(tester);
    await tester.enterText(
      field('Anzeigename'),
      'Privater künstlicher Entwurf',
    );
    await tester.ensureVisible(find.text('Speichern'));
    await tester.tap(find.text('Speichern'));
    await tester.pump();
    expect(f.requests.where((r) => r.method == 'PUT').length, 1);
    f.state.beginAuthentication();
    await tester.pump();
    late.complete(f.response({}));
    await tester.pumpAndSettle();
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(find.text('Lernangaben gespeichert.'), findsNothing);
    expect(f.requests.length, 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('replacing bearer token closes the previous session draft', (
    tester,
  ) async {
    final f = profile.Fixture();
    f.state.api.token = 'synthetic-old-session';
    await f.open(tester);
    await tester.enterText(
      field('Anzeigename'),
      'Privater künstlicher Entwurf',
    );
    f.state.api.token = 'synthetic-new-session';
    f.state.refreshState();
    await tester.pumpAndSettle();
    expect(find.text('Notwendige Lernangaben'), findsNothing);
    expect(find.text('Privater künstlicher Entwurf'), findsNothing);
    expect(f.requests, isEmpty);
  });
}
