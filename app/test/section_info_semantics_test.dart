import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/admin_workspace_ui.dart';
import 'package:schulpilot/child_section_ui.dart';
import 'package:schulpilot/page_tools.dart';
import 'package:schulpilot/parent_workspace_ui.dart';
import 'package:schulpilot/ui.dart';

void main() {
  final headers = <String, Widget>{
    'child': const ChildSectionHero(
      eyebrow: 'Hausaufgaben',
      title: 'Deine Aufgaben',
      description: 'Ein kurzer Hinweis.',
      icon: Icons.book,
    ),
    'parent': const ParentWorkspaceHero(
      eyebrow: 'Überblick',
      title: 'Lernplan',
      subtitle: 'Ein kurzer Hinweis.',
    ),
    'admin': const AdminWorkspaceHeader(
      title: 'Betrieb',
      subtitle: 'Ein kurzer Hinweis.',
      currentPath: '/admin',
    ),
  };
  for (final entry in headers.entries) {
    testWidgets('${entry.key} section info has one accessible action', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      try {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        await tester.pumpWidget(
          MaterialApp(
            theme: appTheme(),
            home: Scaffold(body: entry.value),
          ),
        );
        final button = find.byType(SectionInfoButton);
        expect(tester.getSize(button).shortestSide, greaterThanOrEqualTo(48));
        expect(
          tester.getSemantics(find.bySemanticsLabel('Über diesen Bereich')),
          matchesSemantics(
            label: 'Über diesen Bereich',
            isButton: true,
            isFocusable: true,
            hasFocusAction: true,
            hasEnabledState: true,
            isEnabled: true,
            hasTapAction: true,
            hasExpandedState: true,
          ),
        );
        await tester.tap(find.byTooltip('Über diesen Bereich'));
        await tester.pumpAndSettle();
        expect(
          tester.getSemantics(find.bySemanticsLabel('Bereichsinfo schließen')),
          matchesSemantics(
            label: 'Bereichsinfo schließen',
            isButton: true,
            isFocusable: true,
            hasFocusAction: true,
            hasEnabledState: true,
            isEnabled: true,
            hasTapAction: true,
            hasExpandedState: true,
            isExpanded: true,
          ),
        );
        await tester.sendKeyEvent(LogicalKeyboardKey.tab);
        await tester.sendKeyEvent(LogicalKeyboardKey.enter);
        await tester.pumpAndSettle();
        expect(find.byTooltip('Über diesen Bereich'), findsOneWidget);
        expect(tester.takeException(), isNull);
      } finally {
        semantics.dispose();
      }
    });
  }
}
