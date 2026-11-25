import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// An explicit parent-only read; it never starts processing or learning.
class LocalProcessingFailuresPanel extends StatefulWidget {
  final AppState state;
  final String childId;
  const LocalProcessingFailuresPanel({
    super.key,
    required this.state,
    required this.childId,
  });

  @override
  State<LocalProcessingFailuresPanel> createState() =>
      _LocalProcessingFailuresPanelState();
}

class _LocalProcessingFailuresPanelState
    extends State<LocalProcessingFailuresPanel> {
  late final owner = widget.state.user;
  late final family = widget.state.familyId;
  late final identity = widget.state.api.requestIdentity();
  bool expanded = false, loading = false, failed = false;
  List<dynamic>? errors;
  int epoch = 0;

  bool get current =>
      mounted &&
      widget.state.isParent &&
      identical(owner, widget.state.user) &&
      family == widget.state.familyId &&
      widget.state.api.ownsRequest(identity);

  String detail(dynamic stamp) {
    if (stamp is! int || stamp < 0 || stamp > 4102444800) {
      return 'Kein KI-Auftrag wurde gestartet.';
    }
    final day = DateTime.fromMillisecondsSinceEpoch(stamp * 1000).toLocal();
    String two(int value) => value.toString().padLeft(2, '0');
    return '${two(day.day)}.${two(day.month)}.${day.year} · '
        '${two(day.hour)}:${two(day.minute)}\nKein KI-Auftrag wurde gestartet.';
  }

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
        errors = null;
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
      final result = await widget.state.api.get(
        '/children/${Uri.encodeComponent(widget.childId)}/processing-errors',
      );
      if (!current ||
          !expanded ||
          request != epoch ||
          route?.isCurrent == false) {
        return;
      }
      if (result['errors'] is! List) {
        throw const FormatException('invalid processing errors');
      }
      setState(() => errors = result['errors'] as List);
    } catch (_) {
      if (current &&
          expanded &&
          request == epoch &&
          route?.isCurrent != false) {
        setState(() {
          errors = null;
          failed = true;
        });
      }
    } finally {
      if (mounted && request == epoch) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!current || !RegExp(r'^[a-f0-9]{32}$').hasMatch(widget.childId)) {
      return const SizedBox.shrink();
    }
    return ExpansionTile(
      title: const Text('Verarbeitungsfehler'),
      subtitle: const Text('Letzte lokale Hinweise'),
      onExpansionChanged: (open) {
        setState(() {
          expanded = open;
          errors = null;
          failed = false;
        });
        if (open) {
          load();
        } else {
          epoch++;
        }
      },
      children: [
        if (loading)
          const Padding(
            padding: EdgeInsets.all(16),
            child: CircularProgressIndicator(),
          ),
        if (failed)
          TextButton(onPressed: load, child: const Text('Erneut laden')),
        if (errors != null && errors!.isEmpty)
          const ListTile(title: Text('Keine Hinweise vorhanden.')),
        if (errors != null)
          for (final row in errors!.take(20))
            if (row is Map)
              ListTile(
                title: Text(switch (row['code']) {
                  'photo_invalid' => 'Foto konnte nicht gelesen werden',
                  'photo_too_large' => 'Foto war zu groß',
                  'photo_unavailable' => 'Fotodienst war nicht erreichbar',
                  'question_missing' => 'Aufgabe war nicht mehr verfügbar',
                  _ => 'Verarbeitung fehlgeschlagen',
                }),
                subtitle: Text(detail(row['created'])),
                trailing:
                    row['unit_id'] is String &&
                        RegExp(r'^[a-f0-9]{32}$').hasMatch(row['unit_id'])
                    ? IconButton(
                        tooltip: 'Runde öffnen',
                        icon: const Icon(Icons.arrow_forward),
                        onPressed: () {
                          if (current) {
                            openRoute(context, '/unit/${row['unit_id']}');
                          }
                        },
                      )
                    : null,
              ),
        if (errors != null && errors!.length >= 20)
          const ListTile(title: Text('Bis zu 20 Hinweise werden angezeigt.')),
      ],
    );
  }
}
