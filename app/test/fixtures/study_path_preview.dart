// Standalone, synthetic visual review; no production account or provider.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/study_path_panel.dart';
import 'package:schulpilot/ui.dart';

void main() {
  final state =
      AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) async {
              final blocks = [
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
              ];
              return http.Response(
                jsonEncode({
                  'available': true,
                  'blocks': blocks,
                  'total_questions': 6,
                  'completed_questions': 2,
                  'ready_questions': 2,
                  'next_block_id': 'b',
                  'can_continue': true,
                }),
                200,
                headers: {'content-type': 'application/json'},
              );
            }),
          ),
        )
        ..user = {
          'id': 'example',
          'role': 'child',
          'child_id': 'child',
          'synthetic': true,
        };
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => Scaffold(
          appBar: AppBar(title: const Text('Beispiel · Nach der Schule')),
          body: SafeArea(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: StudyPathPanel(state, 'child', 'example-day'),
              ),
            ),
          ),
        ),
      ),
      GoRoute(
        path: '/unit/:id',
        builder: (_, route) => const Scaffold(
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
    ),
  );
}
