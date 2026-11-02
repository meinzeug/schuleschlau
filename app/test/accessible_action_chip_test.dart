import 'dart:ui' show CheckedState;

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets('action chip exposes a button and activates exactly once', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    var count = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AccessibleActionChip(
            semanticsLabel: 'Drei Aufgaben',
            label: const Text('3'),
            onPressed: () => count++,
          ),
        ),
      ),
    );
    final node = tester.getSemantics(find.byType(AccessibleActionChip));
    expect(node.getSemanticsData().flagsCollection.isButton, isTrue);
    expect(
      node.getSemanticsData().flagsCollection.isChecked,
      CheckedState.none,
    );
    expect(node.getSemanticsData().label, 'Drei Aufgaben');
    expect(node.getSemanticsData().hasAction(SemanticsAction.tap), isTrue);
    node.owner!.performAction(node.id, SemanticsAction.tap);
    expect(count, 1);
    await tester.tap(find.text('3'));
    expect(count, 2);
    semantics.dispose();
  });

  testWidgets(
    'disabled chip has no activation and keyboard activates enabled chip',
    (tester) async {
      final semantics = tester.ensureSemantics();
      var count = 0;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                AccessibleActionChip(
                  semanticsLabel: 'Nicht verfügbar',
                  label: const Text('Aus'),
                  onPressed: null,
                ),
                AccessibleActionChip(
                  semanticsLabel: 'Start',
                  label: const Text('Start'),
                  onPressed: () => count++,
                ),
              ],
            ),
          ),
        ),
      );
      final disabled = tester.getSemantics(
        find.byType(AccessibleActionChip).first,
      );
      expect(
        disabled.getSemanticsData().hasAction(SemanticsAction.tap),
        isFalse,
      );
      await tester.tap(find.text('Aus'));
      expect(count, 0);
      await tester.sendKeyEvent(LogicalKeyboardKey.tab);
      await tester.sendKeyEvent(LogicalKeyboardKey.enter);
      await tester.pump();
      expect(count, 1);
      semantics.dispose();
    },
  );
}
