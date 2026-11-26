import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/learning_scene_player.dart';

import 'learning_scene_player_test.dart' as fixture;

void main() {
  for (final viewport in [(390.0, 1.0), (320.0, 2.0)]) {
    testWidgets('Vielfachenreihe bleibt mobil lesbar und steuerbar $viewport', (
      tester,
    ) async {
      fixture.size(tester, Size(viewport.$1, 844));
      final calls = <http.Request>[];
      final block = <String, dynamic>{
        'kind': 'scene',
        'title': 'Vielfache entdecken',
        'labels': ['4', '8', '12', '16'],
        'scene': {
          'version': 1,
          'layout': 'row',
          'transition_ms': 400,
          'objects': [
            for (var i = 0; i < 4; i++)
              {
                'id': 'o$i',
                'label': ['4', '8', '12', '16'][i],
                'shape': 'box',
                'tone': 'accent',
              },
          ],
          'steps': [
            for (var phase = 0; phase < 2; phase++)
              {
                'caption': phase == 0
                    ? 'Starte bei 4.'
                    : 'Gehe immer 4 weiter.',
                'placements': [
                  for (var i = 0; i < 4; i++) {'object_id': 'o$i', 'slot': i},
                ],
                'highlight': [phase == 0 ? 'o0' : 'o3'],
                'edges': [],
              },
          ],
        },
      };
      final snapshot = fixture.copy(block);
      await tester.pumpWidget(
        fixture.host(
          LearningScenePlayer(block, state: fixture.actor(calls)),
          size: Size(viewport.$1, 844),
          scale: viewport.$2,
          reduced: true,
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Starte bei 4.'), findsWidgets);
      await fixture.tapVisible(
        tester,
        find.byKey(const ValueKey('scene-direct-step-1')),
      );
      expect(find.text('Gehe immer 4 weiter.'), findsWidgets);
      expect(tester.takeException(), isNull);
      expect(calls, isEmpty);
      expect(block, snapshot);
      await tester.pumpWidget(const SizedBox());
    });
  }
}
