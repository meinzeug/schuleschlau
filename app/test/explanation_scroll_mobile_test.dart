import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'entry_help_139_test.dart' as entry;
import 'learning_room_test.dart' as room;
import 'saved_visual_explanation_107_test.dart' as visual;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final scale in [1.0, 2.0]) {
    testWidgets(
      'long explanation has a visible scroll affordance at 320px/$scale',
      (tester) async {
        final server = room.SavedRound();
        entry.probe(server, 'source_probe');
        final step = visual.explanationStep('e1', 1, 2)
          ..['text'] = List.filled(
            10,
            'Ein Bruch zeigt gleich große Teile eines Ganzen.',
          ).join(' ');
        await room.openRound(
          tester,
          server,
          textScale: scale,
          handle: (request) async {
            if (request.url.path.endsWith('/visual-position')) {
              return room.jsonReply({
                'source_signature': 'a' * 64,
                'revision': 0,
                'position': null,
              });
            }
            if (request.url.path.endsWith('/explanation')) {
              await server.handle(request);
              return room.jsonReply({
                'explanation': step['text'],
                'question_id': null,
                'explanation_steps': [step],
                'explanation_visual_status': 'ready',
              });
            }
            return server.handle(request);
          },
        );
        await entry.tap(tester, 'Erst die Erklärung ansehen');
        final scrollFinder = find.byKey(const ValueKey('explanation-scroll'));
        final scroll = tester.widget<SingleChildScrollView>(scrollFinder);
        final bar = tester.widget<Scrollbar>(
          find
              .ancestor(of: scrollFinder, matching: find.byType(Scrollbar))
              .first,
        );
        expect(bar.controller, same(scroll.controller));
        expect(bar.thumbVisibility, isTrue);
        expect(scroll.controller!.position.maxScrollExtent, greaterThan(0));
        expect(
          tester.getBottomLeft(scrollFinder).dy,
          lessThanOrEqualTo(tester.getTopLeft(find.text('Weiter üben')).dy),
        );
        await tester.drag(scrollFinder, const Offset(0, -500));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 400));
        expect(scroll.controller!.position.pixels, greaterThan(0));
        expect(server.answers, 0);
        expect(tester.takeException(), isNull);
        await tester.tap(find.text('Weiter üben'));
        await tester.pumpAndSettle();
        expect(find.text('Kurz erklärt'), findsNothing);
      },
    );
  }
}
