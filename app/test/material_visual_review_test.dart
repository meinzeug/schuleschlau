import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/material_visual_review.dart';

void main() {
  late AppState state;
  late List<http.Request> requests;
  late Map<String, dynamic> data;
  late Future<http.Response> Function(http.Request) respond;
  setUp(() {
    requests = [];
    data = {
      'id': 'page',
      'revision': 7,
      'image_digest': 'image',
      'visual_observations_digest': 'source',
      'visual_observations': [
        {
          'description': 'Drei blaue Felder',
          'image_region': null,
          'uncertainty': '',
        },
        {
          'description': 'Eine Linie',
          'image_region': null,
          'uncertainty': 'unscharf',
        },
      ],
      'visual_observation_reviews': [],
    };
    respond = (_) async => http.Response(
      jsonEncode(data),
      200,
      headers: {'content-type': 'application/json'},
    );
    state =
        AppState(
            api: Api(
              base: 'https://example.invalid/api',
              client: MockClient((request) {
                requests.add(request);
                return respond(request);
              }),
            )..token = 'token',
          )
          ..familyId = 'family'
          ..user = {'id': 'child', 'role': 'child', 'child_id': 'child'};
  });
  Future<void> mount(WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: MaterialVisualReview(
              state: state,
              data: data,
              onRefresh: () {},
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('Öffnen schreibt nichts; ein Klick bestätigt nur einen Befund', (
    tester,
  ) async {
    await mount(tester);
    expect(requests, isEmpty);
    await tester.tap(find.text('Stimmt').first);
    await tester.pumpAndSettle();
    expect(requests, hasLength(1));
    expect(
      requests.single.url.path,
      '/api/materials/page/visual-observations/0/review',
    );
    final body = jsonDecode(requests.single.body) as Map;
    expect(body['decision'], 'confirmed');
    expect(body['revision'], 7);
    expect(body['review_version'], 0);
    expect(body['observations_digest'], 'source');
    expect(body['observation']['description'], 'Drei blaue Felder');
  });
  testWidgets('Konflikt erhält den Korrekturentwurf', (tester) async {
    respond = (_) async => http.Response(
      '{"detail":"conflict"}',
      409,
      headers: {'content-type': 'application/json'},
    );
    await mount(tester);
    await tester.tap(find.text('Ändern').first);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Vier blaue Felder');
    await tester.tap(find.text('Korrektur speichern'));
    await tester.pumpAndSettle();
    expect(find.text('Vier blaue Felder'), findsOneWidget);
    expect(find.textContaining('Dein Text bleibt hier'), findsOneWidget);
    expect(jsonDecode(requests.single.body)['decision'], 'corrected');
  });
  testWidgets('Antwort nach Kontowechsel zeigt keine fremden Befunde', (
    tester,
  ) async {
    final completion = Completer<http.Response>();
    respond = (_) => completion.future;
    await mount(tester);
    await tester.tap(find.text('Stimmt').first);
    await tester.pump();
    state.user = {'id': 'other', 'role': 'child', 'child_id': 'other'};
    state.notifyListeners();
    await tester.pump();
    completion.complete(
      http.Response(
        jsonEncode(data),
        200,
        headers: {'content-type': 'application/json'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Drei blaue Felder'), findsNothing);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Seitenwechsel verwirft gespeicherte Prüfstände', (tester) async {
    final oldObservation = data['visual_observations'][0];
    respond = (_) async => http.Response(
      jsonEncode({
        ...data,
        'visual_observation_reviews': [
          {
            'index': 0,
            'decision': 'confirmed',
            'observation': oldObservation,
            'review_version': 1,
          },
        ],
      }),
      200,
      headers: {'content-type': 'application/json'},
    );
    await mount(tester);
    await tester.tap(find.text('Stimmt').first);
    await tester.pumpAndSettle();
    expect(find.text('Geprüft · keine Lernquelle'), findsOneWidget);
    data = {
      ...data,
      'id': 'page-b',
      'revision': 8,
      'visual_observations_digest': 'other',
      'visual_observations': [
        {
          'description': 'Neuer Bildbefund',
          'image_region': null,
          'uncertainty': '',
        },
      ],
    };
    await mount(tester);
    expect(find.text('Neuer Bildbefund'), findsOneWidget);
    expect(find.text('Geprüft · keine Lernquelle'), findsNothing);
    expect(find.text('Noch nicht geprüft'), findsOneWidget);
  });

  testWidgets('Verspätete Antwort der vorherigen Seite wird verworfen', (
    tester,
  ) async {
    final completion = Completer<http.Response>();
    respond = (_) => completion.future;
    await mount(tester);
    await tester.tap(find.text('Stimmt').first);
    await tester.pump();
    final oldPage = data;
    data = {
      ...data,
      'id': 'page-b',
      'revision': 8,
      'visual_observations_digest': 'other',
      'visual_observations': [
        {
          'description': 'Neuer Bildbefund',
          'image_region': null,
          'uncertainty': '',
        },
      ],
    };
    await mount(tester);
    completion.complete(
      http.Response(
        jsonEncode({
          ...oldPage,
          'visual_observation_reviews': [
            {
              'index': 0,
              'decision': 'confirmed',
              'observation': oldPage['visual_observations'][0],
              'review_version': 1,
            },
          ],
        }),
        200,
        headers: {'content-type': 'application/json'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Neuer Bildbefund'), findsOneWidget);
    expect(find.text('Drei blaue Felder'), findsNothing);
    expect(find.text('Geprüft · keine Lernquelle'), findsNothing);
    expect(find.text('Noch nicht geprüft'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Überlaufwarnung bleibt auch ohne sichtbare Befunde sichtbar', (
    tester,
  ) async {
    data['visual_observations'] = [];
    data['quality_warnings'] = [
      'Nicht alle Bildbefunde werden angezeigt. Schau dir das Foto an.',
      'Anderer Qualitätshinweis',
    ];
    await mount(tester);
    expect(find.text('Bilder auf der Seite'), findsOneWidget);
    expect(
      find.text(
        'Nicht alle Bildbefunde werden angezeigt. Schau dir das Foto an.',
      ),
      findsOneWidget,
    );
    expect(find.text('Anderer Qualitätshinweis'), findsNothing);
    expect(requests, isEmpty);
  });
}
