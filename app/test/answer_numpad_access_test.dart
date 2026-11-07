import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/answer_number_keys.dart';

import 'learning_room_test.dart' as round;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets('numpad selects the visible answer but never checks it', (
    t,
  ) async {
    final server = round.SavedRound();
    await round.openRound(t, server);
    await t.sendKeyEvent(LogicalKeyboardKey.numpad2);
    await t.pump();
    expect(
      t.widget<RadioGroup<String>>(find.byType(RadioGroup<String>)).groupValue,
      'Hund',
    );
    expect(server.answers, 0);
    expect(server.hints, 0);
  });
  testWidgets('numpad does not steal text editing or modifier shortcuts', (
    t,
  ) async {
    final input = FocusNode(), numbers = FocusNode();
    addTearDown(input.dispose);
    addTearDown(numbers.dispose);
    final chosen = <int>[];
    var current = true;
    final bubbled = <LogicalKeyboardKey>[];
    await t.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Focus(
            onKeyEvent: (_, event) {
              if (event is KeyDownEvent) bubbled.add(event.logicalKey);
              return KeyEventResult.ignored;
            },
            child: AnswerNumberKeys(
              focusNode: numbers,
              isCurrent: () => current,
              optionCount: 2,
              onSelect: chosen.add,
              child: TextField(focusNode: input),
            ),
          ),
        ),
      ),
    );
    await t.pumpAndSettle();
    input.requestFocus();
    await t.pump();
    await t.sendKeyEvent(LogicalKeyboardKey.numpad2);
    expect(chosen, isEmpty);
    expect(bubbled, contains(LogicalKeyboardKey.numpad2));
    numbers.requestFocus();
    await t.pump();
    await t.sendKeyDownEvent(LogicalKeyboardKey.controlLeft);
    await t.sendKeyEvent(LogicalKeyboardKey.numpad1);
    await t.sendKeyUpEvent(LogicalKeyboardKey.controlLeft);
    await t.sendKeyEvent(LogicalKeyboardKey.numpad9);
    expect(chosen, isEmpty);
    expect(bubbled, contains(LogicalKeyboardKey.numpad1));
    expect(bubbled, contains(LogicalKeyboardKey.numpad9));
    await t.sendKeyEvent(LogicalKeyboardKey.numpad2);
    expect(chosen, [1]);
    current = false;
    await t.sendKeyEvent(LogicalKeyboardKey.numpad1);
    expect(chosen, [1]);
    expect(bubbled, contains(LogicalKeyboardKey.numpad1));
  });
}
