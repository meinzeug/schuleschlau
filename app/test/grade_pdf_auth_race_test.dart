import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/grade_import_screen.dart';
import 'package:schulpilot/ui.dart';

import 'grade_pdf_test.dart' as fixtures;

class SyntheticXFile extends XFile {
  static final data = Uint8List.fromList(utf8.encode('%PDF-synthetic'));
  SyntheticXFile() : super.fromData(data, name: 'synthetic.pdf');
  @override
  Future<int> length() async => data.length;
  @override
  Future<Uint8List> readAsBytes() async => data;
}

void main() {
  testWidgets('an old PDF confirmation cannot run after reauthorization', (
    tester,
  ) async {
    final requests = <http.Request>[];
    Json sample() {
      final data = fixtures.preview();
      data['items'] = [(data['items'] as List).first];
      data['counts'] = {'new': 1, 'existing': 0, 'possible_match': 0};
      return data;
    }

    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) async {
          requests.add(request);
          if (request.url.path.endsWith('/auth/me')) {
            return fixtures.response({
              'id': 'parent',
              'role': 'parent',
              'session_assertion': 'a' * 64,
            });
          }
          if (request.url.path.endsWith('/grades')) {
            return fixtures.response({'child_id': 'child', 'can_manage': true});
          }
          return fixtures.response(
            sample(),
            request.method == 'POST' ? 201 : 200,
          );
        }),
      ),
    )..user = {'id': 'parent', 'role': 'parent', 'session_assertion': 'a' * 64};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: GradePdfImport(
            state,
            childId: 'child',
            childName: 'Beispielkind',
            pickPdf: () async => SyntheticXFile(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('PDF auswählen'));
    await tester.pumpAndSettle();
    final oldConfirm = tester
        .widget<FilledButton>(
          find.widgetWithText(FilledButton, 'Auswahl übernehmen'),
        )
        .onPressed!;
    final intent = state.beginAuthentication();
    await tester.pumpAndSettle();
    state.cancelAuthentication(intent);
    await tester.pump();
    await tester.tap(find.text('Zugang prüfen'));
    await tester.pumpAndSettle();
    oldConfirm();
    await tester.pumpAndSettle();
    expect(requests.where((r) => r.url.path.endsWith('/confirm')), isEmpty);
  });

  testWidgets(
    'system back does not discard a blocked PDF preview without asking',
    (tester) async {
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (request) async => fixtures.response(fixtures.preview(), 201),
          ),
        ),
      )..user = {'id': 'parent', 'role': 'parent'};
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: Builder(
              builder: (context) => TextButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) => GradePdfImport(
                    state,
                    childId: 'child',
                    childName: 'Beispielkind',
                    pickPdf: () async => SyntheticXFile(),
                  ),
                ),
                child: const Text('Öffnen'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Öffnen'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('PDF auswählen'));
      await tester.pumpAndSettle();
      state.beginAuthentication();
      await tester.pumpAndSettle();
      await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();
      expect(find.text('Änderungen verwerfen?'), findsOneWidget);
      await tester.tap(find.text('Weiterbearbeiten'));
      await tester.pumpAndSettle();
      expect(find.text('Anmeldung geändert'), findsOneWidget);
    },
  );

  testWidgets(
    'PDF preview stays hidden until the same session and access are checked',
    (tester) async {
      final requests = <http.Request>[];
      var allow = true;
      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((request) async {
                  requests.add(request);
                  if (request.url.path.endsWith('/auth/me')) {
                    return fixtures.response({
                      'id': 'parent',
                      'role': 'parent',
                      'session_assertion': 'a' * 64,
                    });
                  }
                  if (request.url.path.endsWith('/grades')) {
                    return fixtures.response({
                      'child_id': 'child',
                      'can_manage': allow,
                    });
                  }
                  return fixtures.response(
                    fixtures.preview(),
                    request.method == 'POST' ? 201 : 200,
                  );
                }),
              ),
            )
            ..user = {
              'id': 'parent',
              'role': 'parent',
              'session_assertion': 'a' * 64,
            };
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: GradePdfImport(
              state,
              childId: 'child',
              childName: 'Beispielkind',
              pickPdf: () async => SyntheticXFile(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('PDF auswählen'));
      await tester.pumpAndSettle();
      expect(find.text('Schuljahr 2026/2027'), findsWidgets);
      final auth = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Schuljahr 2026/2027'), findsNothing);
      expect(find.text('Anmeldung geändert'), findsOneWidget);
      state.cancelAuthentication(auth);
      allow = false;
      await tester.pump();
      await tester.tap(find.text('Zugang prüfen'));
      await tester.pumpAndSettle();
      expect(find.text('Schuljahr 2026/2027'), findsNothing);
      allow = true;
      await tester.tap(find.text('Zugang prüfen'));
      await tester.pumpAndSettle();
      expect(find.text('Schuljahr 2026/2027'), findsWidgets);
      expect(requests.where((r) => r.method == 'POST'), hasLength(1));
      expect(
        requests.where(
          (r) =>
              r.method == 'GET' && r.url.path.endsWith('/grade-imports/import'),
        ),
        hasLength(1),
      );
    },
  );

  testWidgets('an old PDF upload response cannot restore a blocked preview', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((request) => pending.future),
      ),
    )..user = {'id': 'parent', 'role': 'parent'};
    addTearDown(state.dispose);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: GradePdfImport(
            state,
            childId: 'child',
            childName: 'Beispielkind',
            pickPdf: () async => SyntheticXFile(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('PDF auswählen'));
    await tester.pump();
    state.beginAuthentication();
    await tester.pumpAndSettle();
    pending.complete(fixtures.response(fixtures.preview(), 201));
    await tester.pumpAndSettle();
    expect(find.text('Schuljahr 2026/2027'), findsNothing);
    expect(find.text('Anmeldung geändert'), findsOneWidget);
  });
  testWidgets(
    'a pending confirmation is reconciled before the PDF preview reopens',
    (tester) async {
      final pending = Completer<http.Response>();
      final requests = <http.Request>[];
      Json sample() {
        final data = fixtures.preview();
        data['items'] = [(data['items'] as List).first];
        data['counts'] = {'new': 1, 'existing': 0, 'possible_match': 0};
        return data;
      }

      final state =
          AppState(
              api: Api(
                base: 'https://example.invalid/api',
                client: MockClient((request) async {
                  requests.add(request);
                  if (request.url.path.endsWith('/confirm')) {
                    return pending.future;
                  }
                  if (request.url.path.endsWith('/auth/me')) {
                    return fixtures.response({
                      'id': 'parent',
                      'role': 'parent',
                      'session_assertion': 'a' * 64,
                    });
                  }
                  if (request.url.path.endsWith('/grades')) {
                    return fixtures.response({
                      'child_id': 'child',
                      'can_manage': true,
                    });
                  }
                  final data = sample();
                  if (request.method == 'GET') {
                    data['status'] = 'applied';
                    data['result'] = {
                      'added': 1,
                      'linked': 0,
                      'updated': 0,
                      'unchanged': 0,
                      'skipped': 0,
                    };
                  }
                  return fixtures.response(
                    data,
                    request.method == 'POST' ? 201 : 200,
                  );
                }),
              ),
            )
            ..user = {
              'id': 'parent',
              'role': 'parent',
              'session_assertion': 'a' * 64,
            };
      addTearDown(state.dispose);
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme(),
          home: Scaffold(
            body: GradePdfImport(
              state,
              childId: 'child',
              childName: 'Beispielkind',
              pickPdf: () async => SyntheticXFile(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('PDF auswählen'));
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Auswahl übernehmen'));
      await tester.tap(find.text('Auswahl übernehmen'));
      await tester.pump();
      expect(
        requests.where((r) => r.url.path.endsWith('/confirm')),
        hasLength(1),
      );
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(
        find.textContaining('kann bereits gespeichert sein'),
        findsOneWidget,
      );
      state.cancelAuthentication(intent);
      await tester.pump();
      await tester.tap(find.text('Zugang prüfen'));
      await tester.pumpAndSettle();
      expect(find.textContaining('1 neue Noten'), findsOneWidget);
      pending.complete(
        fixtures.response({
          'added': 9,
          'linked': 0,
          'updated': 0,
          'unchanged': 0,
          'skipped': 0,
        }),
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('1 neue Noten'), findsOneWidget);
      expect(find.textContaining('9 neue Noten'), findsNothing);
      expect(
        requests.where((r) => r.url.path.endsWith('/confirm')),
        hasLength(1),
      );
    },
  );
}
