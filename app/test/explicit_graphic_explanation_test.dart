import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/learning_content.dart';
import 'package:schulpilot/learning_explanation.dart';
import 'package:schulpilot/lesson_voice.dart';
import 'package:schulpilot/ui.dart';

import 'saved_visual_explanation_107_test.dart' as saved;

// Saved, artificial result from the isolated real-provider browser run. The
// graphic step explains only 1/4; the separately saved text teaches addition.
const fullText =
    'Die Grafik zeigt 1 von 4 gleich großen Teilen. Bei Brüchen mit gleichem '
    'Nenner addierst du die Zähler; der Nenner bleibt gleich. Beispiel: Bei '
    '1/4 + 2/4 rechnest du oben 1 + 2 und behältst unten die 4. Merke: '
    'Nur die Zähler werden addiert.';

Future<void> mount(
  WidgetTester tester,
  Widget body, {
  double width = 390,
  double scale = 1,
}) async {
  tester.view.physicalSize = Size(width, 844);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(),
      home: MediaQuery(
        data: MediaQueryData(
          size: Size(width, 844),
          textScaler: TextScaler.linear(scale),
        ),
        child: Scaffold(body: SingleChildScrollView(child: body)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Iterable<String> texts(WidgetTester tester) => tester
    .widgetList<LearningReader>(find.byType(LearningReader))
    .map((reader) => reader.text);

bool hasText(WidgetTester tester, String value) =>
    texts(tester).any((text) => text.contains(value));

void main() {
  for (final configuration in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'Explicit graphic explanation retains its full text at $configuration',
      (tester) async {
        final step = saved.explanationStep('one', 1, 4)
          ..['text'] =
              'Der Bruch 1 durch 4 beschreibt 1 von 4 gleich großen '
              'Teilen eines Ganzen.';
        await mount(
          tester,
          LearningExplanation(
            text: fullText,
            steps: [step],
            showFullTextAfterSteps: true,
          ),
          width: configuration.$1,
          scale: configuration.$2,
        );
        expect(hasText(tester, fullText), isTrue);
        expect(find.byType(LearningReader), findsOneWidget);
        expect(find.byType(ReadAloudButton), findsNWidgets(2));
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets(
    'An automatic introduction never reveals the separate full text',
    (tester) async {
      final step = saved.explanationStep('one', 1, 4);
      await mount(tester, LearningExplanation(text: fullText, steps: [step]));
      expect(hasText(tester, fullText), isFalse);
    },
  );

  testWidgets('Full text follows the last graphic step only', (tester) async {
    await mount(
      tester,
      LearningExplanation(
        text: fullText,
        steps: [
          saved.explanationStep('one', 1, 4),
          saved.explanationStep('two', 2, 4),
        ],
        showFullTextAfterSteps: true,
      ),
    );
    expect(hasText(tester, fullText), isFalse);
    await tester.ensureVisible(find.text('Nächster Schritt'));
    await tester.tap(find.text('Nächster Schritt'));
    await tester.pumpAndSettle();
    expect(hasText(tester, fullText), isTrue);
    expect(find.byType(LearningReader), findsOneWidget);
  });

  testWidgets('Do not duplicate text already shown as a graphic step', (
    tester,
  ) async {
    final step = saved.explanationStep('one', 1, 4)..['text'] = fullText;
    await mount(
      tester,
      LearningExplanation(
        text: fullText,
        steps: [step],
        showFullTextAfterSteps: true,
      ),
    );
    expect(texts(tester).where((text) => text == fullText), hasLength(1));
    expect(find.byType(LearningReader), findsOneWidget);
  });

  testWidgets('An explicitly opened solution may show its saved answer text', (
    tester,
  ) async {
    const answer = 'Zwei Siebtel plus drei Siebtel ergibt 5/7.';
    await mount(
      tester,
      LearningExplanation(
        text: answer,
        prompt: 'Wie viel ist 2/7 + 3/7?',
        steps: [saved.explanationStep('given', 2, 7)],
        showFullTextAfterSteps: true,
      ),
    );
    expect(hasText(tester, answer), isTrue);
  });
}
