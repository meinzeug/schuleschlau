import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/fraction_explorer.dart';
import 'package:schulpilot/learning_content.dart';
import 'package:schulpilot/learning_explanation.dart';
import 'package:schulpilot/ui.dart';

void main() {
  final fixture = jsonDecode(
    File('test/fixtures/demo_visual_steps.json').readAsStringSync(),
  ) as List<dynamic>;
  for (var variant = 0; variant < fixture.length; variant++) {
    testWidgets(
      'demo variant $variant renders full intro and each task explanation',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final unit = Map<String, dynamic>.from(fixture[variant] as Map);
        final cases = <Map<String, dynamic>>[
          {
            'text': unit['explanation'],
            'steps': unit['explanation_steps'],
            'intro': true,
          },
          for (final value in unit['questions'] as List<dynamic>)
            {
              'text': value['explanation'],
              'steps': value['explanation_steps'],
              'question': value,
            },
        ];
        for (final entry in cases) {
          final step = Map<String, dynamic>.from(
            (entry['steps'] as List<dynamic>).single as Map,
          );
          final text = step['text'] as String;
          await tester.pumpWidget(const SizedBox());
          await tester.pumpWidget(
            MaterialApp(
              theme: appTheme(),
              home: Scaffold(
                body: SingleChildScrollView(
                  child: LearningExplanation(
                    text: entry['text'] as String,
                    steps: [step],
                  ),
                ),
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(
            tester.widget<LearningReader>(find.byType(LearningReader)).text,
            text,
          );
          final figure = tester.widget<FractionExplorer>(
            find.byType(FractionExplorer),
          );
          expect((figure.numerator, figure.denominator), (2, 4));
          expect(text, contains('Beispiel 2/4 aus dem Demoheft'));
          if (entry['intro'] == true) {
            expect(
              text,
              contains('Bei gleichem Nenner addierst du die Zähler'),
            );
            expect(
              text,
              contains(
                'Beim Kürzen teilst du oben und unten durch dieselbe Zahl',
              ),
            );
          } else {
            final question = entry['question'] as Map<String, dynamic>;
            final saved = question['explanation'] as String;
            expect(text, contains(saved.split('.').first));
            if (question['id'] == 'sum' || question['id'] == 'reduce') {
              final answer = (question['answer'] as String).split('/');
              expect(
                text,
                contains('Zähler ${answer[0]} und Nenner ${answer[1]}'),
              );
            }
          }
        }
      },
    );
  }
}
