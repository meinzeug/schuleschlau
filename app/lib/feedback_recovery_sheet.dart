import 'package:flutter/material.dart';

import 'api.dart';
import 'math_content.dart';

/// Unread answers are paged in a stable order which is not a chronology.
class FeedbackRecoverySheet extends StatefulWidget {
  final Api api;
  final String unitId;
  final bool Function() isCurrent;
  final VoidCallback onChanged;
  final VoidCallback onClose;

  const FeedbackRecoverySheet({
    super.key,
    required this.api,
    required this.unitId,
    required this.isCurrent,
    required this.onChanged,
    required this.onClose,
  });

  @override
  State<FeedbackRecoverySheet> createState() => _FeedbackRecoverySheetState();
}

class _FeedbackRecoverySheetState extends State<FeedbackRecoverySheet> {
  List<Json> items = [];
  String? next;
  bool laterPage = false;
  String? error;
  bool busy = false;

  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load([String? after]) async {
    if (busy || !widget.isCurrent()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final query = after == null
          ? ''
          : '?after=${Uri.encodeQueryComponent(after)}';
      final data = await widget.api.get(
        '/units/${widget.unitId}/feedback/recovery$query',
      );
      if (!mounted || !widget.isCurrent()) return;
      setState(() {
        items = (data['items'] as List? ?? [])
            .whereType<Map>()
            .map((e) => Json.from(e))
            .toList();
        next = data['next_after']?.toString();
        laterPage = after != null;
      });
    } catch (e) {
      if (mounted && widget.isCurrent()) {
        setState(
          () => error = e is ApiError ? e.message : 'Bitte versuche es erneut.',
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> acknowledge(Json item) async {
    if (busy || !widget.isCurrent()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final id = item['attempt_id'] as String;
      await widget.api.post(
        '/units/${widget.unitId}/feedback/recovery/acknowledge',
        {'attempt_id': id},
      );
      if (!mounted || !widget.isCurrent()) return;
      widget.onChanged();
      setState(() => items.removeWhere((entry) => entry['attempt_id'] == id));
    } catch (e) {
      if (mounted && widget.isCurrent()) {
        setState(
          () => error = e is ApiError ? e.message : 'Bitte versuche es erneut.',
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => SafeArea(
    child: FractionallySizedBox(
      heightFactor: .85,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    'Deine Rückmeldungen',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                IconButton(
                  tooltip: 'Schließen',
                  onPressed: widget.onClose,
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20),
            child: Text(
              'Die Reihenfolge ist nicht bekannt. Schau jede Rückmeldung einzeln an.',
            ),
          ),
          if (busy) const LinearProgressIndicator(),
          if (error != null)
            Padding(padding: const EdgeInsets.all(12), child: Text(error!)),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (items.isEmpty && !busy && error == null && next == null)
                  const Text('Keine ungelesenen Rückmeldungen.'),
                for (final item in items)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          MathText(
                            item['prompt']?.toString() ??
                                'Aufgabe nicht mehr verfügbar',
                          ),
                          const SizedBox(height: 8),
                          MathText('Deine Antwort: ${item['answer']}'),
                          const SizedBox(height: 8),
                          Text(switch (item['outcome']) {
                            'correct' => 'Richtig',
                            'incorrect' => 'Noch üben',
                            _ => 'Noch offen',
                          }),
                          if (item['assisted'] == true) const Text('Mit Hilfe'),
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton(
                              onPressed: busy ? null : () => acknowledge(item),
                              child: const Text('Gelesen'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                if (next != null)
                  TextButton(
                    onPressed: busy ? null : () => load(next),
                    child: const Text('Weitere anzeigen'),
                  ),
                if (laterPage)
                  TextButton(
                    onPressed: busy ? null : () => load(),
                    child: const Text('Zur ersten Seite'),
                  ),
                if (error != null)
                  TextButton(
                    onPressed: busy ? null : () => load(),
                    child: const Text('Erneut versuchen'),
                  ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
