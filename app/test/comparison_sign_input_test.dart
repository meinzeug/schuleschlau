import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/math_content.dart';
import 'package:schulpilot/scientific_notation.dart';

import 'learning_room_test.dart' as room;
import 'render_fonts.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(loadFormulaFonts);
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  const prompt =
      r'Ergänze ein Vergleichszeichen: \(\frac{3}{5}\;\text{___}\;\frac{1}{2}\). Wähle <, > oder =.';

  test('Only an explicit sign choice changes the answer control', () {
    expect(expectsComparisonSign({'type': 'short', 'prompt': prompt}), isTrue);
    expect(expectsFraction({'type': 'short', 'prompt': prompt}), isFalse);
    expect(
      expectsComparisonSign({'type': 'choice', 'prompt': prompt}),
      isFalse,
    );
    expect(
      expectsComparisonSign({
        'type': 'short',
        'prompt': 'Welcher Bruch ist größer: 1/2 oder 3/4?',
      }),
      isFalse,
    );
    expect(
      expectsFraction({
        'type': 'short',
        'prompt': 'Welcher Bruch ist größer: 1/2 oder 3/4?',
      }),
      isTrue,
    );
  });

  for (final scale in [1.0, 2.0]) {
    testWidgets('A sign answer can be selected and submitted at $scale', (
      t,
    ) async {
      final question = room.question('cmp', type: 'short')
        ..['prompt'] = prompt
        ..['options'] = <String>[];
      final server = room.SavedRound(questions: [question]);
      server.expected['cmp'] = '>';
      final harness = await room.openRound(t, server, textScale: scale);
      expect(find.byType(ComparisonSignAnswerInput), findsOneWidget);
      expect(find.byType(FractionAnswerInput), findsNothing);
      for (final sign in ['<', '=', '>']) {
        final chip = find.widgetWithText(ChoiceChip, sign);
        expect(t.getSize(chip).shortestSide, greaterThanOrEqualTo(48));
      }
      expect(find.byTooltip('Formel als Text'), findsNothing);
      expect(
        spokenFormula(r'\frac{3}{5}\;\text{___}\;\frac{1}{2}'),
        contains('Lücke'),
      );
      expect(
        spokenFormula(r'\frac{3}{5}\;\text{___}\;\frac{1}{2}'),
        isNot(contains('Index')),
      );
      await room.tapText(t, '>');
      await room.tapText(t, 'Antwort prüfen');
      expect(server.answers, 1);
      expect(find.text('Richtig!'), findsOneWidget);
      expect(t.takeException(), isNull);
      await harness.close();
    });
  }
}
