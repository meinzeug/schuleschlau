import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_start_illustration.dart';

import 'vocabulary_test.dart' as fixture;

void main() {
  for (final empty in [true, false]) {
    testWidgets('word review stays compact and read-only, empty=$empty', (
      tester,
    ) async {
      final calls = <http.Request>[];
      final data = fixture.listing();
      if (empty) {
        data['items'] = [];
        data['pagination'] = {...data['pagination'], 'total': 0};
        data['summary'] = {
          ...data['summary'],
          'confirmed_words': 0,
          'new_words': 0,
          'due_words': 0,
        };
      }
      await fixture.open(
        tester,
        calls,
        width: 390,
        openTools: false,
        cards: false,
        wordListing: data,
      );
      expect(find.byTooltip('Wörter hinzufügen'), findsOneWidget);
      expect(
        find.byType(LearningStartIllustration),
        empty ? findsOneWidget : findsNothing,
      );
      await fixture.tap(tester, find.text('Prüfen'));
      expect(find.byType(LearningStartIllustration), findsNothing);
      expect(find.byTooltip('Wörter hinzufügen'), findsNothing);
      expect(find.text('Wörter prüfen'), findsOneWidget);
      await fixture.tap(tester, find.text('Zum Wortschatz'));
      expect(find.byTooltip('Wörter hinzufügen'), findsOneWidget);
      expect(calls.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    });
  }
}
