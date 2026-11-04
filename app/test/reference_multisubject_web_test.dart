import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/learning_explanation.dart';
import 'package:schulpilot/subject_graphic.dart';

import 'saved_visual_explanation_107_test.dart' as visual;

// Public synthetic renderer fixtures. Backend selection and reference integrity
// are tested separately by test_reference_multisubject_path.py.
const fixture =
    r'''[{"subject":"Geographie","presentation":{"version":1,"evidence_kind":"knowledge","blocks":[{"kind":"scene","title":"Verdunstung","disclosure":"given","labels":["Verdunstung","Kondensation","Niederschlag"],"numbers":[],"connections":[],"marks":[],"unit":"","variant":"","scene":{"version":1,"layout":"cycle","objects":[{"id":"o0","label":"Verdunstung","shape":"circle","tone":"accent"},{"id":"o1","label":"Kondensation","shape":"box","tone":"neutral"},{"id":"o2","label":"Niederschlag","shape":"diamond","tone":"secondary"}],"steps":[{"caption":"Verdunstung","placements":[{"object_id":"o0","slot":0},{"object_id":"o1","slot":1},{"object_id":"o2","slot":2}],"highlight":["o0"],"edges":[{"start":"o0","end":"o1","label":""}]},{"caption":"Kondensation","placements":[{"object_id":"o0","slot":1},{"object_id":"o1","slot":2},{"object_id":"o2","slot":0}],"highlight":["o1"],"edges":[{"start":"o1","end":"o2","label":""}]},{"caption":"Niederschlag","placements":[{"object_id":"o0","slot":2},{"object_id":"o1","slot":0},{"object_id":"o2","slot":1}],"highlight":["o2"],"edges":[]}],"transition_ms":400}}]}},{"subject":"Geschichte","presentation":{"version":1,"evidence_kind":"knowledge","blocks":[{"kind":"scene","title":"Handel","disclosure":"given","labels":["Handel","Stadt","Markt"],"numbers":[],"connections":[],"marks":[],"unit":"","variant":"","scene":{"version":1,"layout":"row","objects":[{"id":"o0","label":"Handel","shape":"circle","tone":"accent"},{"id":"o1","label":"Stadt","shape":"box","tone":"neutral"},{"id":"o2","label":"Markt","shape":"diamond","tone":"secondary"}],"steps":[{"caption":"Handel","placements":[{"object_id":"o0","slot":0},{"object_id":"o1","slot":1},{"object_id":"o2","slot":2}],"highlight":["o0"],"edges":[{"start":"o0","end":"o1","label":""}]},{"caption":"Stadt","placements":[{"object_id":"o0","slot":1},{"object_id":"o1","slot":2},{"object_id":"o2","slot":0}],"highlight":["o1"],"edges":[{"start":"o1","end":"o2","label":""}]},{"caption":"Markt","placements":[{"object_id":"o0","slot":2},{"object_id":"o1","slot":0},{"object_id":"o2","slot":1}],"highlight":["o2"],"edges":[]}],"transition_ms":400}}]}},{"subject":"Deutsch","presentation":{"version":1,"evidence_kind":"knowledge","blocks":[{"kind":"sentence","title":"Zum Heftinhalt","disclosure":"given","labels":["Der Hund","bellt."],"numbers":[],"connections":[],"unit":"","variant":"","marks":[{"index":0,"role":"subject"}]}]}}]''';

void main() {
  final cases = (jsonDecode(fixture) as List).cast<Map<String, dynamic>>();
  for (final entry in cases) {
    for (final width in [390.0, 1024.0]) {
      testWidgets('visible saved ${entry['subject']} graphic at $width', (
        tester,
      ) async {
        final presentation = entry['presentation'] as Json;
        final labels =
            ((presentation['blocks'] as List).first['labels'] as List)
                .cast<String>();
        await visual.mount(
          tester,
          LearningExplanation(
            text: 'Künstlicher Erklärtext',
            sourceKey: entry['subject'],
            steps: [
              {
                'id': 'step',
                'text': 'Künstlicher Erklärtext',
                'disclosure': 'given',
                'reference': {'id': 'synthetic.fixture', 'version': 1},
                'presentation': presentation,
              },
            ],
          ),
          width: width,
        );
        expect(find.byType(SubjectGraphic), findsWidgets);
        expect(find.text(labels.first), findsWidgets);
        expect(tester.takeException(), isNull);
      });
    }
  }
}
