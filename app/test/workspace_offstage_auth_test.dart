import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets(
    'a hidden workspace cannot open a keyboard tool and login closes an old one',
    (tester) async {
      final hidden = ValueNotifier(false);
      final state = AppState(
        api: Api(
          base: 'https://example.invalid/api',
          client: MockClient(
            (_) async => http.Response(jsonEncode({'available': false}), 200),
          ),
        ),
      )..user = {'id': 'synthetic', 'role': 'parent', 'families': []};
      final router = GoRouter(
        initialLocation: '/app',
        routes: [
          GoRoute(
            path: '/app',
            builder: (_, _) => ValueListenableBuilder<bool>(
              valueListenable: hidden,
              builder: (_, value, _) => Offstage(
                offstage: value,
                child: WorkspaceShell(
                  state: state,
                  title: 'Noten',
                  browser: true,
                  child: const Text('Künstlicher Inhalt'),
                ),
              ),
            ),
          ),
        ],
      );
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      await tester.sendKeyEvent(LogicalKeyboardKey.f1);
      await tester.pumpAndSettle();
      expect(find.text('Tastatur & Bedienung'), findsOneWidget);
      final revision = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      state.cancelAuthentication(revision);
      hidden.value = true;
      await tester.pumpAndSettle();
      await tester.sendKeyEvent(LogicalKeyboardKey.f1);
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      hidden.value = false;
      await tester.pumpAndSettle();
      await tester.sendKeyEvent(LogicalKeyboardKey.f1);
      await tester.pumpAndSettle();
      expect(find.text('Tastatur & Bedienung'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      router.dispose();
      state.inbox.dispose();
      state.dispose();
      hidden.dispose();
    },
  );
}
