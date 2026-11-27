import 'dart:ui' show SemanticsAction, Tristate;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_local_tools_ux88_test.dart' as local;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets('day details retain an accessible state on resize', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    final calls = <String>[];
    final day = {
      'id': 'day',
      'child_id': 'child',
      'date': '2026-11-28',
      'stage': 'collecting',
      'revision': 1,
      'read_only': false,
      'allow_uploads': true,
      'max_pages': 24,
      'pages': <Object>[],
      'confirmed_count': 0,
      'synthetic': true,
      'active_job': null,
      'last_error': null,
      'preparation': {'status': 'idle'},
      'units': <Object>[],
      'plan': {
        'groups': <Object>[],
        'notices': <Object>[],
        'estimated_minutes': 8,
      },
    };
    final state = local.account((request) async {
      calls.add(request.method);
      if (request.url.path.endsWith('/school-day/today')) {
        return local.reply({'day': day});
      }
      if (request.url.path.endsWith('/school-days/day')) {
        return local.reply(day);
      }
      return local.reply({
        'items': <Object>[],
        'unread_count': 0,
        'available': false,
      });
    });
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(320, 844);
    final router = GoRouter(
      initialLocation: '/after-school/child',
      routes: [
        GoRoute(
          path: '/after-school/:id',
          builder: (_, route) =>
              SchoolDayScreen(state, childId: route.pathParameters['id']!),
        ),
      ],
    );
    try {
      await tester.pumpWidget(
        MaterialApp.router(theme: appTheme(), routerConfig: router),
      );
      await tester.pumpAndSettle();
      final control = find.text('Mehr zu diesem Tag');
      await tester.ensureVisible(control);
      var data = tester.getSemantics(control).getSemanticsData();
      expect(data.flagsCollection.isExpanded, Tristate.isFalse);
      expect(data.hasAction(SemanticsAction.tap), isTrue);
      await tester.tap(control);
      await tester.pumpAndSettle();
      expect(
        tester
            .getSemantics(control)
            .getSemanticsData()
            .flagsCollection
            .isExpanded,
        Tristate.isTrue,
      );
      tester.view.physicalSize = const Size(390, 844);
      await tester.pumpAndSettle();
      expect(
        tester
            .getSemantics(control)
            .getSemanticsData()
            .flagsCollection
            .isExpanded,
        Tristate.isTrue,
      );
      await tester.ensureVisible(control);
      await tester.tap(control);
      await tester.pumpAndSettle();
      expect(
        tester
            .getSemantics(control)
            .getSemanticsData()
            .flagsCollection
            .isExpanded,
        Tristate.isFalse,
      );
      expect(calls.every((method) => method == 'GET'), isTrue);
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.inbox.dispose();
      state.dispose();
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
      semantics.dispose();
    }
  });
}
