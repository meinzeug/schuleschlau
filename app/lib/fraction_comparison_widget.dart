import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'api.dart';
import 'learning_graphic_frame.dart';
import 'learning_graphic_scope.dart';
import 'learning_tool_scope.dart';
import 'ui.dart';

/// A previously disclosed, server-checked comparison. Changing the view is
/// only an inspection action; it never writes an answer or learning evidence.
class FractionComparisonWidget extends StatelessWidget {
  final Json step;
  final AppState? state;
  const FractionComparisonWidget({super.key, required this.step, this.state});

  static List<List<int>>? values(Json step) {
    final reference = step['reference'], presentation = step['presentation'];
    if (reference is! Map ||
        reference['id'] != 'math.fraction.comparison' ||
        reference['version'] is! int ||
        reference['version'] != 1 ||
        step['disclosure'] != 'solution' ||
        presentation is! Map ||
        presentation['version'] is! int ||
        presentation['version'] != 1 ||
        presentation['evidence_kind'] != 'knowledge') {
      return null;
    }
    final blocks = presentation['blocks'];
    if (blocks is! List || blocks.length != 4) return null;
    final result = <List<int>>[];
    for (final block in blocks) {
      if (block is! Map ||
          block['kind'] != 'fraction' ||
          block['disclosure'] != 'solution') {
        return null;
      }
      for (final key in ['labels', 'connections', 'marks']) {
        if (block[key] is! List || (block[key] as List).isNotEmpty) return null;
      }
      if ((block['variant'] ?? '') != '' ||
          (block['unit'] ?? '') != '' ||
          block['scene'] != null ||
          block['text_probe'] != null ||
          block['lab'] != null) {
        return null;
      }
      final numbers = block['numbers'];
      if (numbers is! List ||
          numbers.length != 2 ||
          numbers.any(
            (value) =>
                value is! num ||
                !value.isFinite ||
                value != value.roundToDouble(),
          )) {
        return null;
      }
      final numerator = (numbers[0] as num).toInt(),
          denominator = (numbers[1] as num).toInt();
      if (denominator < 1 ||
          denominator > 24 ||
          numerator < 1 ||
          numerator >= denominator) {
        return null;
      }
      result.add([numerator, denominator]);
    }
    final left = result[0],
        right = result[1],
        expandedLeft = result[2],
        expandedRight = result[3];
    final common = left[1] ~/ left[1].gcd(right[1]) * right[1];
    if (left[1] == right[1] ||
        left[0] * right[1] == right[0] * left[1] ||
        expandedLeft[1] != common ||
        expandedRight[1] != common ||
        left[0] * common != expandedLeft[0] * left[1] ||
        right[0] * common != expandedRight[0] * right[1]) {
      return null;
    }
    return result;
  }

  static bool supports(Json step) => values(step) != null;

  @override
  Widget build(BuildContext context) {
    final checked = values(step);
    if (checked == null) return const SizedBox.shrink();
    return LearningToolScope(
      state: state,
      sourceKey: jsonEncode(step),
      builder: (_) => _ComparisonView(values: checked),
    );
  }
}

class _ComparisonView extends StatefulWidget {
  final List<List<int>> values;
  const _ComparisonView({required this.values});
  @override
  State<_ComparisonView> createState() => _ComparisonViewState();
}

class _ComparisonViewState extends State<_ComparisonView> {
  bool common = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final phase = LearningGraphicScope.maybeOf(context)?.phase;
    if (phase == 'comparison-original' || phase == 'comparison-common') {
      common = phase == 'comparison-common';
    }
  }

  void choose(bool value) {
    if (ModalRoute.of(context)?.isCurrent == false) return;
    setState(() => common = value);
    LearningGraphicScope.report(
      context,
      value ? 'comparison-common' : 'comparison-original',
    );
  }

  @override
  Widget build(BuildContext context) {
    final shown = common
        ? widget.values.sublist(2)
        : widget.values.sublist(0, 2);
    return LearningGraphicFrame(
      title: 'Brüche vergleichen',
      child: Column(
        key: const ValueKey('fraction-comparison'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ChoiceChip(
                label: const Text('Brüche'),
                selected: !common,
                onSelected: (_) => choose(false),
              ),
              ChoiceChip(
                label: const Text('Gleicher Nenner'),
                selected: common,
                onSelected: (_) => choose(true),
              ),
            ],
          ),
          const SizedBox(height: 12),
          for (final fraction in shown) ...[
            Text(
              '${fraction[0]} / ${fraction[1]}',
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Semantics(
              image: true,
              label:
                  '${fraction[0]} von ${fraction[1]} gleich großen Teilen sind markiert.',
              child: ExcludeSemantics(
                child: SizedBox(
                  height: 32,
                  child: CustomPaint(
                    painter: _ComparisonBar(
                      fraction[0],
                      fraction[1],
                      context.palette,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
          ],
          Text(
            common
                ? 'Jetzt kannst du die Zähler vergleichen.'
                : 'Beide Balken zeigen ein gleich großes Ganzes.',
          ),
        ],
      ),
    );
  }
}

class _ComparisonBar extends CustomPainter {
  final int numerator, denominator;
  final AppPalette palette;
  _ComparisonBar(this.numerator, this.denominator, this.palette);

  @override
  void paint(Canvas canvas, Size size) {
    final cell = size.width / denominator;
    final gap = math.min(1.0, cell / 5);
    final fill = Paint()..style = PaintingStyle.fill;
    final edge = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1
      ..color = palette.ink;
    for (var index = 0; index < denominator; index++) {
      fill.color = index < numerator ? palette.actionBlue : palette.surfaceHigh;
      final rect = Rect.fromLTWH(
        index * cell + gap,
        1,
        math.max(0.0, cell - 2 * gap),
        size.height - 2,
      );
      canvas.drawRect(rect, fill);
      canvas.drawRect(rect, edge);
    }
  }

  @override
  bool shouldRepaint(covariant _ComparisonBar old) =>
      numerator != old.numerator ||
      denominator != old.denominator ||
      palette.isDark != old.palette.isDark;
}
