import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:schulpilot/child_question_text.dart';
import 'package:schulpilot/learning_content.dart';

import 'learning_room_test.dart' as room;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test(
    'shortens only the known generated label, retaining the task and hint',
    () {
      expect(
        childQuestionText(
          'Wie lautet der Zähler des Bruchs 6/12? Neues Übungsbeispiel zum Verstehen: Achte auf die Position der gesuchten Zahl.',
        ),
        'Wie lautet der Zähler des Bruchs 6/12? Achte auf die Position der gesuchten Zahl.',
      );
      expect(
        childQuestionText(
          'Wie lautet der Nenner des Bruchs 3/8? Neues Übungsbeispiel zum Anwenden: Nenne die Zahl.',
        ),
        'Wie lautet der Nenner des Bruchs 3/8? Nenne die Zahl.',
      );
    },
  );

  test('leaves unrelated questions and unrecognized text intact', () {
    for (final prompt in [
      'Neues Übungsbeispiel zum Verstehen: Welche Zahl fehlt?',
      'Wie lautet der Zähler des Bruchs 6/12? Neues Übungsbeispiel zum Vertiefen: Achte auf die Position.',
      'Wie lautet der Zähler des Bruchs 6/12? Achte auf die Position.',
    ]) {
      expect(childQuestionText(prompt), prompt);
    }
  });

  testWidgets(
    'the learning room shortens the display without changing the saved task',
    (tester) async {
      const original =
          'Wie lautet der Zähler des Bruchs 6/12? Neues Übungsbeispiel zum Verstehen: Achte auf die Position der gesuchten Zahl.';
      final question = room.question('cat', type: 'short')
        ..['prompt'] = original;
      final server = room.SavedRound(questions: [question]);
      await room.openRound(tester, server);

      final shown = tester.widgetList<LearningContent>(
        find.byType(LearningContent),
      );
      expect(
        shown.map((content) => content.text),
        contains(
          'Wie lautet der Zähler des Bruchs 6/12? Achte auf die Position der gesuchten Zahl.',
        ),
      );
      expect(question['prompt'], original);
      expect(server.answers, 0);
    },
  );
}
