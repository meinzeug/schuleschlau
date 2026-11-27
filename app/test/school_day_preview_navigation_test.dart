import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:schulpilot/exams_screen.dart';
import 'package:schulpilot/homework_screen.dart';
import 'package:schulpilot/school_day_screen.dart';
import 'package:schulpilot/vocabulary_screen.dart';

import 'fixtures/school_day_preview.dart' as preview;

void main() {
  testWidgets(
    'synthetic preview navigation uses the routes of real child pages',
    (tester) async {
      tester.view.physicalSize = const Size(1100, 900);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      preview.main();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 600));
      final router = GoRouter.of(tester.element(find.byType(SchoolDayScreen)));
      for (final (path, expected) in [
        ('/vocabulary/example-child', VocabularyScreen),
        ('/homework/example-child', HomeworkScreen),
        ('/exams/example-child', ExamsScreen),
        ('/app', SchoolDayScreen),
      ]) {
        router.go(path);
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 600));
        expect(find.byType(expected), findsOneWidget, reason: path);
        expect(find.text('Page Not Found'), findsNothing, reason: path);
        expect(tester.takeException(), isNull, reason: path);
      }
      await tester.pumpWidget(const SizedBox());
    },
  );
}
