// Local UI review with generated data only; never connects to the application server.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/exams_screen.dart';
import 'package:schulpilot/homework_screen.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/ui.dart';
import 'package:schulpilot/vocabulary_screen.dart';

void main() {
  final page = {
    'id': 'example-page',
    'child_id': 'example-child',
    'page_number': 1,
    'subject': 'Mathematik',
    'topic': 'Brüche',
    'confirmed': true,
    'status': 'confirmed',
    'synthetic': true,
    'homework': <String>[],
  };
  final day = {
    'id': 'example-day',
    'child_id': 'example-child',
    'date': '2026-11-26',
    'stage': 'ready',
    'revision': 1,
    'allow_uploads': true,
    'max_pages': 24,
    'pages': [page],
    'confirmed_count': 1,
    // The ready-path branch is normally for real packages. This flag only
    // selects that branch here; every item in this standalone preview is fake.
    'synthetic': false,
    'units': <Object>[],
    'plan': {
      'groups': <Object>[],
      'notices': <Object>[],
      'estimated_minutes': 8,
    },
    'preparation': {'status': 'completed'},
  };
  final path = {
    'available': true,
    'blocks': [
      {
        'id': 'a',
        'title': 'Brüche vergleichen',
        'phase': 'understand',
        'label': 'Erste Runde',
        'status': 'completed',
        'question_count': 2,
        'unit_id': 'example-a',
      },
      {
        'id': 'b',
        'title': 'Brüche verstehen und erweitern',
        'phase': 'understand',
        'label': 'Erste Runde',
        'status': 'ready',
        'question_count': 2,
        'unit_id': 'example-b',
      },
      {
        'id': 'c',
        'title': 'Brüche auf dem Zahlenstrahl',
        'phase': 'apply',
        'label': 'Anwenden',
        'status': 'planned',
        'question_count': 2,
      },
    ],
    'total_questions': 6,
    'completed_questions': 2,
    'ready_questions': 2,
    'next_block_id': 'b',
    'can_continue': true,
  };
  final state =
      AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) async {
              final Object result;
              if (request.method == 'GET' &&
                  request.url.path.endsWith('/study-path')) {
                result = path;
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/children/example-child/exams')) {
                result = {
                  'child_id': 'example-child',
                  'can_manage': true,
                  'exams': <Object>[],
                  'sources': <Object>[],
                  'has_more': false,
                };
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith(
                    '/children/example-child/subjects',
                  )) {
                result = {
                  'items': [
                    {'id': 'example-math', 'title': 'Mathematik'},
                  ],
                };
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/homework')) {
                result = {'photos': <Object>[], 'next_cursor': null};
              } else if (request.method == 'POST' &&
                  request.url.path.endsWith('/vocabulary/imports')) {
                final body = Json.from(jsonDecode(request.body));
                result = {
                  'id': 'example-import',
                  'target_locale': body['target_locale'],
                  'title': body['title'],
                  'status': 'review',
                  'supports_deferred_pairs': true,
                  'pairs': [
                    for (final pair in body['pairs'] as List)
                      {
                        ...Json.from(pair),
                        'context': '',
                        'part_of_speech': '',
                        'variants': <Object>[],
                        'meaning_variants': <Object>[],
                        'uncertainty': '',
                      },
                  ],
                };
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/vocabulary/imports')) {
                result = {'imports': <Object>[]};
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/vocabulary')) {
                result = {
                  'items': <Object>[],
                  'pagination': {'page': 1, 'page_size': 15, 'total': 0},
                  'collections': <Object>[],
                  'open_rounds': <Object>[],
                  'supports_collections': true,
                  'summary': {
                    'confirmed_words': 0,
                    'due_words': 0,
                    'new_words': 0,
                    'skills': <Object>[],
                  },
                };
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/school-days/example-day')) {
                result = day;
              } else if (request.method == 'GET' &&
                  request.url.path.endsWith('/school-days/photo-day')) {
                result = {
                  ...day,
                  'id': 'photo-day',
                  'stage': 'collecting',
                  'pages': <Object>[],
                  'confirmed_count': 0,
                  'preparation': {'status': 'idle'},
                };
              } else if (request.method == 'GET' &&
                  (request.url.path.endsWith('/school-days/review-day') ||
                      request.url.path.endsWith(
                        '/school-days/review-multi-day',
                      ))) {
                final multi = request.url.path.endsWith('/review-multi-day');
                result = {
                  ...day,
                  'id': multi ? 'review-multi-day' : 'review-day',
                  'stage': 'review',
                  'pages': [
                    for (var index = 1; index <= (multi ? 3 : 1); index++)
                      {
                        ...page,
                        'id': 'example-page-$index',
                        'page_number': index,
                        'confirmed': false,
                        'status': 'review',
                        'content': 'Beispieltext zu Brüchen.',
                        'uncertainties': ['Eine Stelle ist unklar.'],
                      },
                  ],
                  'confirmed_count': 0,
                  'preparation': {'status': 'needs_review'},
                };
              } else {
                return http.Response('Preview route not implemented', 404);
              }
              return http.Response(
                jsonEncode(result),
                200,
                headers: {'content-type': 'application/json'},
              );
            }),
          ),
        )
        ..user = {
          'id': 'example-user',
          'role': 'child',
          'child_id': 'example-child',
          'synthetic': true,
        };
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => SchoolDayScreen(
          state,
          childId: 'example-child',
          dayId: 'example-day',
        ),
      ),
      GoRoute(
        path: '/capture',
        builder: (_, _) => SchoolDayScreen(
          state,
          childId: 'example-child',
          dayId: 'photo-day',
        ),
      ),
      GoRoute(
        path: '/review',
        builder: (_, _) => SchoolDayScreen(
          state,
          childId: 'example-child',
          dayId: 'review-day',
        ),
      ),
      GoRoute(
        path: '/review-multi',
        builder: (_, _) => SchoolDayScreen(
          state,
          childId: 'example-child',
          dayId: 'review-multi-day',
        ),
      ),
      GoRoute(
        path: '/vocabulary',
        builder: (_, _) => VocabularyScreen(state, childId: 'example-child'),
      ),
      GoRoute(
        path: '/vocabulary/:id',
        builder: (_, route) =>
            VocabularyScreen(state, childId: route.pathParameters['id']!),
      ),
      GoRoute(
        path: '/homework',
        builder: (_, _) => HomeworkScreen(state, childId: 'example-child'),
      ),
      GoRoute(
        path: '/homework/:childId',
        builder: (_, route) =>
            HomeworkScreen(state, childId: route.pathParameters['childId']!),
      ),
      GoRoute(
        path: '/exams',
        builder: (_, _) => ExamsScreen(state, childId: 'example-child'),
      ),
      GoRoute(
        path: '/exams/:childId',
        builder: (_, route) =>
            ExamsScreen(state, childId: route.pathParameters['childId']!),
      ),
      GoRoute(
        path: '/app',
        builder: (_, _) => SchoolDayScreen(
          state,
          childId: 'example-child',
          dayId: 'example-day',
        ),
      ),
      GoRoute(
        path: '/unit/:id',
        builder: (_, _) => const Scaffold(
          body: Center(child: Text('Beispielrunde – keine echten Daten')),
        ),
      ),
    ],
  );
  runApp(
    MaterialApp.router(
      theme: appTheme(brightness: Brightness.dark),
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      builder: (_, child) => Banner(
        message: 'BEISPIELDATEN',
        location: BannerLocation.topEnd,
        child: child!,
      ),
    ),
  );
}
