import 'package:flutter/material.dart';

import 'api.dart';

/// An explicit, parent-only metadata read. Opening it never starts a job.
class ProcessingTracePanel extends StatefulWidget {
  final AppState state;
  final String jobId;
  const ProcessingTracePanel({
    super.key,
    required this.state,
    required this.jobId,
  });

  @override
  State<ProcessingTracePanel> createState() => _ProcessingTracePanelState();
}

class _ProcessingTracePanelState extends State<ProcessingTracePanel> {
  late final owner = widget.state.user;
  late final family = widget.state.familyId;
  late final identity = widget.state.api.requestIdentity();
  bool expanded = false, loading = false, failed = false;
  Json? trace;
  int epoch = 0;

  bool get current =>
      mounted &&
      widget.state.isParent &&
      identical(owner, widget.state.user) &&
      family == widget.state.familyId &&
      widget.state.api.ownsRequest(identity);

  @override
  void initState() {
    super.initState();
    widget.state.addListener(accountChanged);
  }

  void accountChanged() {
    if (current) return;
    epoch++;
    if (mounted) {
      setState(() {
        trace = null;
        loading = false;
        failed = false;
      });
    }
  }

  @override
  void dispose() {
    epoch++;
    widget.state.removeListener(accountChanged);
    super.dispose();
  }

  Future<void> load() async {
    final route = ModalRoute.of(context);
    if (!current || !expanded || loading || route?.isCurrent == false) {
      return;
    }
    final request = ++epoch;
    setState(() {
      loading = true;
      failed = false;
    });
    try {
      final value = await widget.state.api.get(
        '/jobs/${Uri.encodeComponent(widget.jobId)}/trace',
      );
      if (!current ||
          !expanded ||
          request != epoch ||
          route?.isCurrent == false) {
        return;
      }
      if (value['job_id'] != widget.jobId ||
          value['status'] is! String ||
          value['phase'] is! String) {
        throw const FormatException('invalid trace');
      }
      setState(() => trace = value);
    } catch (_) {
      if (current &&
          expanded &&
          request == epoch &&
          route?.isCurrent != false) {
        setState(() {
          trace = null;
          failed = true;
        });
      }
    } finally {
      if (mounted && request == epoch) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!current || !RegExp(r'^[a-f0-9]{32}$').hasMatch(widget.jobId)) {
      return const SizedBox.shrink();
    }
    final value = trace;
    final model = value?['model'];
    final sources = value?['sources'];
    final units = value?['units'];
    return ExpansionTile(
      title: const Text('Verarbeitung ansehen'),
      subtitle: const Text('Technische Informationen für Eltern'),
      onExpansionChanged: (open) {
        setState(() {
          expanded = open;
          trace = null;
          failed = false;
        });
        if (open) {
          load();
        } else {
          epoch++;
          loading = false;
        }
      },
      children: [
        if (loading)
          const Padding(
            padding: EdgeInsets.all(12),
            child: CircularProgressIndicator(),
          )
        else if (failed)
          TextButton(onPressed: load, child: const Text('Details erneut laden'))
        else if (value != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Schritt: ${switch (value['phase']) {
                    'recognition' => 'Erkennung',
                    'countercheck' => 'Gegenprüfung',
                    'generation' => 'Lernrunde',
                    'feedback' => 'Lernrückblick',
                    'decision' => 'Nächster Lernschritt',
                    'visual' => 'Grafik',
                    'visual_review' => 'Grafikprüfung',
                    'exam_review' => 'Klassenarbeit',
                    'vocabulary' => 'Wortschatzimport',
                    'language' => 'Sprachübung',
                    'tutor' => 'Lernhilfe',
                    'parent_review' => 'Elternüberblick',
                    _ => 'Verarbeitung',
                  }}',
                ),
                Text(
                  'Status: ${switch (value['status']) {
                    'completed' => 'abgeschlossen',
                    'failed' => 'fehlgeschlagen',
                    'queued' => 'wartet',
                    'running' => 'läuft',
                    _ => 'nicht bekannt',
                  }}',
                ),
                if (value['error_code'] is String)
                  Text('Fehlerklasse: ${value['error_code']}'),
                if (switch (value['failure_detail']) {
                      'output_length' => 'Die KI hat ihr Ausgabelimit erreicht. Das Ergebnis wurde verworfen.',
                      'question_fraction_ambiguous' =>
                        'Eine Bruchaufgabe war nicht eindeutig gestellt.',
                      'question_fraction_result' || 'question_fraction_form' =>
                        'Eine Bruchlösung passte nicht zur Aufgabenstellung.',
                      _ => null,
                    }
                    case final String explanation)
                  Text(explanation),
                if (model is Map && model['model'] is String)
                  Text('Modell: ${model['model']}'),
                if (model is Map && model['config_revision'] is int)
                  Text('Konfigurationsstand: ${model['config_revision']}'),
                if (value['model_ambiguous'] == true)
                  const Text('Der Modellbeleg ist nicht eindeutig.'),
                if (sources is List)
                  Text(
                    'Quellen: ${sources.length}${value['sources_truncated'] == true ? ' (Auswahl)' : ''}',
                  ),
                if (sources is List)
                  for (final source in sources.take(5))
                    if (source is Map &&
                        source['revision'] is int &&
                        source['current_revision'] is int)
                      Text(
                        'Quellenfassung: ${source['revision']} · aktuell ${source['current_revision']}',
                      ),
                if (sources is List && sources.length > 5)
                  const Text('Weitere Quellen sind im Beleg enthalten.'),
                if (value['source_snapshot'] is Map &&
                    value['source_snapshot']['revision'] is int)
                  Text(
                    'Erkannte Quellenfassung: ${value['source_snapshot']['revision']}',
                  ),
                if (units is List)
                  for (final unit in units)
                    if (unit is Map && unit['references'] is List) ...[
                      Text(
                        'Grafikvorlagen: ${(unit['references'] as List).length}${unit['references_truncated'] == true ? ' (Auswahl)' : ''}',
                      ),
                      for (final reference in (unit['references'] as List).take(
                        5,
                      ))
                        if (reference is Map &&
                            reference['id'] is String &&
                            reference['version'] is int)
                          Text(
                            '${reference['id']} · Version ${reference['version']}',
                          ),
                      if ((unit['references'] as List).length > 5)
                        const Text('Weitere Vorlagen sind im Beleg enthalten.'),
                    ],
              ],
            ),
          ),
      ],
    );
  }
}
