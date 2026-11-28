import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// Public curriculum metadata; choosing a subject never enrolls a learner.
class CurriculumTopicsDialog extends StatefulWidget {
  final AppState state;
  final String stateCode, schoolForm;
  final String? stateLabel, schoolFormLabel;
  const CurriculumTopicsDialog(
    this.state, {
    super.key,
    required this.stateCode,
    required this.schoolForm,
    this.stateLabel,
    this.schoolFormLabel,
  });

  @override
  State<CurriculumTopicsDialog> createState() => _CurriculumTopicsDialogState();
}

class _CurriculumTopicsDialogState extends State<CurriculumTopicsDialog> {
  late final AppState ownerState = widget.state;
  late final Json? owner = ownerState.user;
  late final String? family = widget.state.familyId,
      token = widget.state.api.token;
  late final (Object?, String?, int?) identity = widget.state.api
      .requestIdentity();
  final subjects = <Json>[];
  final topics = <Json>[];
  String? selected, cursor, error;
  bool loading = true, invalidated = false, complete = false;
  int epoch = 0;

  bool get current =>
      mounted &&
      identical(widget.state, ownerState) &&
      !invalidated &&
      !widget.state.authenticationPending &&
      identical(widget.state.user, owner) &&
      owner != null &&
      widget.state.familyId == family &&
      widget.state.api.token == token &&
      widget.state.api.ownsRequest(identity);

  @override
  void initState() {
    super.initState();
    invalidated = widget.state.authenticationPending;
    ownerState.authenticationChanges.addListener(invalidate);
    ownerState.addListener(accountChanged);
    if (current) loadSubjects();
  }

  void accountChanged() {
    if (!current) invalidate();
  }

  void invalidate() {
    if (!mounted || invalidated) return;
    epoch++;
    setState(() {
      invalidated = true;
      loading = false;
      subjects.clear();
      topics.clear();
      selected = cursor = error = null;
    });
  }

  @override
  void didUpdateWidget(covariant CurriculumTopicsDialog oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.state, widget.state) ||
        oldWidget.stateCode != widget.stateCode ||
        oldWidget.schoolForm != widget.schoolForm) {
      invalidate();
    }
  }

  @override
  void dispose() {
    epoch++;
    ownerState.authenticationChanges.removeListener(invalidate);
    ownerState.removeListener(accountChanged);
    super.dispose();
  }

  Future<void> loadSubjects() async {
    if (!current) return;
    final request = ++epoch;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final catalog = await widget.state.api.get('/curriculum/catalog');
      if (!current || epoch != request) return;
      final raw = catalog['subjects'];
      if (raw is! List ||
          raw.any(
            (item) =>
                item is! Map ||
                item['id'] is! String ||
                item['title'] is! String,
          )) {
        throw ApiError('Die Fachauswahl ist gerade nicht verfügbar.');
      }
      final ids = raw.map((item) => (item as Map)['id']).toList();
      if (ids.toSet().length != ids.length) {
        throw ApiError('Die Fachauswahl ist widersprüchlich.');
      }
      setState(() {
        subjects
          ..clear()
          ..addAll(raw.map((item) => Json.from(item)));
        loading = false;
      });
    } catch (_) {
      if (current && epoch == request) {
        setState(() {
          error = 'Die Fachauswahl konnte nicht geladen werden.';
          loading = false;
        });
      }
    }
  }

  Future<void> loadTopics(String subject, {String? after}) async {
    if (!current || loading || selected != subject) return;
    final request = ++epoch;
    setState(() {
      loading = true;
      error = null;
    });
    final uri = Uri(
      path: '/curriculum/topics',
      queryParameters: {
        'state_code': widget.stateCode,
        'school_form_id': widget.schoolForm,
        'subject_id': subject,
        'limit': '30',
        'cursor': ?after,
      },
    );
    try {
      final data = await widget.state.api.get(uri.toString());
      if (!current || request != epoch || selected != subject) return;
      final raw = data['items'];
      final next = data['next_cursor'];
      if (raw is! List ||
          raw.length > 30 ||
          (after != null && topics.length + raw.length > 150) ||
          (next != null &&
              (next is! String || next.isEmpty || next.length > 140)) ||
          raw.any(
            (item) =>
                item is! Map ||
                item['id'] is! String ||
                item['title'] is! String ||
                item['subject_id'] != subject ||
                item['state_code'] != widget.stateCode ||
                item['school_form_id'] != widget.schoolForm ||
                item['source'] is! Map,
          )) {
        throw ApiError('Die Themenübersicht ist unvollständig.');
      }
      final ids = raw.map((item) => (item as Map)['id']).toList();
      if (ids.toSet().length != ids.length ||
          (after != null &&
              (next == after ||
                  topics.any((topic) => ids.contains(topic['id']))))) {
        throw ApiError('Die Themenübersicht ist widersprüchlich.');
      }
      setState(() {
        if (after == null) topics.clear();
        topics.addAll(raw.map((item) => Json.from(item)));
        cursor = next as String?;
        complete = next == null;
        loading = false;
      });
    } catch (_) {
      if (current && request == epoch) {
        setState(() {
          error = 'Die Themen konnten nicht geladen werden.';
          loading = false;
        });
      }
    }
  }

  String displayTitle(Json topic) {
    final title = topic['title'] as String;
    final subject = subjects
        .where((item) => item['id'] == selected)
        .firstOrNull;
    final label = subject?['title'];
    if (label is! String || label.isEmpty) return title;
    final prefix = RegExp(
      '^${RegExp.escape(label)}\\s*:\\s*',
      caseSensitive: false,
    );
    final shortened = title.replaceFirst(prefix, '');
    return shortened.isEmpty ? title : shortened;
  }

  String scope(Json topic) {
    final phase = topic['phase_label'];
    if (phase is String && phase.isNotEmpty) return phase;
    final grades = topic['grades'];
    if (grades is List &&
        grades.isNotEmpty &&
        grades.every((value) => value is int)) {
      return grades.length == 1
          ? 'Klasse ${grades.first}'
          : 'Klassen ${grades.join('/')}';
    }
    return 'Ohne feste Klassenstufe';
  }

  @override
  Widget build(BuildContext context) {
    final renderEpoch = epoch;
    final renderSubject = selected, renderCursor = cursor;
    return AlertDialog(
      scrollable: true,
      title: const Text('Lehrplanthemen'),
      content: SizedBox(
        width: 480,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!current)
              const Text('Öffne die Übersicht nach der Anmeldung erneut.')
            else ...[
              Text(
                '${widget.stateLabel ?? widget.stateCode} · ${widget.schoolFormLabel ?? widget.schoolForm}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              const Text(
                'Vorschau für deine Auswahl. Die Liste ist unvollständig und legt keinen Kurs an.',
              ),
              const SizedBox(height: 12),
              if (loading) const LinearProgressIndicator(),
              if (!loading && subjects.isEmpty && error == null)
                const Text('Zurzeit sind keine Fächer verfügbar.'),
              if (subjects.isNotEmpty)
                DropdownButtonFormField<String>(
                  key: const ValueKey('curriculum-topic-subject'),
                  initialValue: selected,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Fach'),
                  items: [
                    for (final subject in subjects)
                      DropdownMenuItem(
                        value: subject['id'] as String,
                        child: Text(
                          subject['title'] as String,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                  ],
                  onChanged: loading
                      ? null
                      : (value) {
                          if (!current ||
                              epoch != renderEpoch ||
                              value == null ||
                              !subjects.any((s) => s['id'] == value)) {
                            return;
                          }
                          setState(() {
                            selected = value;
                            topics.clear();
                            cursor = null;
                            complete = false;
                          });
                          loadTopics(value);
                        },
                ),
              if (error != null) ...[
                const SizedBox(height: 12),
                Notice(error!, warning: true),
                TextButton(
                  onPressed: loading
                      ? null
                      : () {
                          if (!current ||
                              epoch != renderEpoch ||
                              selected != renderSubject ||
                              cursor != renderCursor) {
                            return;
                          }
                          if (renderSubject == null) {
                            loadSubjects();
                          } else {
                            loadTopics(renderSubject, after: renderCursor);
                          }
                        },
                  child: const Text('Erneut laden'),
                ),
              ],
              if (!loading &&
                  selected != null &&
                  topics.isEmpty &&
                  complete &&
                  error == null)
                const Padding(
                  padding: EdgeInsets.only(top: 16),
                  child: Text(
                    'Für dieses Fach sind hier noch keine Themen erfasst.',
                  ),
                ),
              for (final topic in topics)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(displayTitle(topic)),
                  subtitle: Text(
                    '${scope(topic)} · ${topic['source']['title'] is String ? topic['source']['title'] : 'Lehrplan'}${topic['source']['page'] is int ? ' · S. ${topic['source']['page']}' : ''}${topic['source']['status'] == 'current_verified' ? '' : ' · Fassung ungeprüft'}',
                  ),
                ),
              if (topics.length >= 150 && !complete)
                const Text('Die Anzeige ist auf 150 Themen begrenzt.'),
              if (!complete &&
                  cursor != null &&
                  error == null &&
                  topics.length < 150)
                TextButton(
                  onPressed: loading
                      ? null
                      : () {
                          if (current &&
                              epoch == renderEpoch &&
                              selected == renderSubject &&
                              cursor == renderCursor &&
                              renderSubject != null) {
                            loadTopics(renderSubject, after: renderCursor);
                          }
                        },
                  child: const Text('Weitere Themen'),
                ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () {
            if (context.mounted && ModalRoute.of(context)?.isCurrent == true) {
              Navigator.pop(context);
            }
          },
          child: const Text('Schließen'),
        ),
      ],
    );
  }
}
