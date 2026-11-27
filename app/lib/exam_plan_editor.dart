import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api.dart';
import 'calendar_dates.dart';
import 'exams_scope.dart';
import 'ui.dart';

/// Edits only an exam plan. Generating or starting exercises is a separate action.
class ExamPlanEditor extends StatefulWidget {
  final AppState state;
  final String childId;
  final Json? existing;
  final String purpose;
  const ExamPlanEditor(
    this.state, {
    super.key,
    required this.childId,
    this.existing,
    this.purpose = 'preparation',
  });
  @override
  State<ExamPlanEditor> createState() => _ExamPlanEditorState();
}

class _ExamPlanEditorState extends State<ExamPlanEditor> {
  late final scope = ExamScope(widget.state)..addListener(changed);
  late final title = TextEditingController(
    text: widget.existing?['title'] ?? '',
  );
  late final subjectInput = TextEditingController(
    text: widget.existing?['subject'] as String? ?? '',
  );
  String get subject => subjectInput.text;
  late String kind = widget.existing?['kind'] as String? ?? 'classwork';
  late DateTime? examDay = DateTime.tryParse(
    '${widget.existing?['exam_date'] ?? ''}',
  );
  late final minutesInput = TextEditingController(
    text: '${widget.existing?['minutes'] as int? ?? 15}',
  );
  int get minutes => int.tryParse(minutesInput.text) ?? 0;
  late bool reminders = widget.existing?['reminders'] == true;
  late String reminderTime =
      widget.existing?['reminder_time'] as String? ?? '16:00';
  late final topics = examObjects(widget.existing?['topics']);
  late final dates = <String>{
    ...((widget.existing?['schedule']?['dates'] as List?) ?? [])
        .whereType<String>(),
  };
  final weekdays = <int>{};
  final counters = <String, TextEditingController>{};
  TextEditingController counter(Json topic) => counters.putIfAbsent(
    topic['id'],
    () => TextEditingController(text: '${topic['question_count']}'),
  );
  DateTime from = DateUtils.dateOnly(DateTime.now());
  late DateTime until = DateTime(from.year, from.month, from.day + 13);
  int step = 0;
  bool saving = false, uncertain = false;
  String? error;
  final loadedSources = <Json>[];
  bool loadingSources = false, sourcesLoaded = false, sourcesMore = false;
  bool legacySources = false;
  String? sourcesCursor, sourcesError;
  int sourcesGeneration = 0;
  Json? pending;
  final requestKey = examRequestKey();
  late final String initialFingerprint;
  @override
  void initState() {
    super.initState();
    initialFingerprint = jsonEncode(body());
  }

  bool get review =>
      (widget.existing?['purpose'] ?? widget.purpose) == 'review';
  bool get hasSourcesForSubject => loadedSources.isNotEmpty;

  Future<void> loadSources({bool more = false}) async {
    if (!scope.current ||
        loadingSources ||
        subject.isEmpty ||
        (more && (!sourcesMore || sourcesCursor == null))) {
      return;
    }
    final stamp = scope.epoch;
    final requestedSubject = subject;
    final generation = ++sourcesGeneration;
    final cursor = more ? sourcesCursor : null;
    setState(() {
      loadingSources = true;
      sourcesError = null;
    });
    try {
      final result = await widget.state.api.get(
        Uri(
          path: '/children/${widget.childId}/exam-sources',
          queryParameters: {'subject': requestedSubject, 'cursor': ?cursor},
        ).toString(),
      );
      if (!mounted ||
          !scope.valid(stamp) ||
          subject != requestedSubject ||
          generation != sourcesGeneration) {
        return;
      }
      if (result['items'] is! List || result['has_more'] is! bool) {
        throw const FormatException('Invalid source page');
      }
      final rawItems = result['items'] as List;
      final items = examObjects(rawItems);
      final hasMore = result['has_more'] == true;
      final next = result['next_cursor'];
      if (items.length != rawItems.length ||
          items.any(
            (item) =>
                item['id'] is! String ||
                (item['id'] as String).isEmpty ||
                item['revision'] is! int ||
                (item['revision'] as int) < 1,
          ) ||
          (hasMore && (next is! String || next.isEmpty || next == cursor))) {
        throw const FormatException('Invalid source page');
      }
      setState(() {
        if (!more) loadedSources.clear();
        final known = loadedSources.map((item) => item['id']).toSet();
        loadedSources.addAll(items.where((item) => known.add(item['id'])));
        sourcesLoaded = true;
        sourcesMore = hasMore;
        sourcesCursor = hasMore ? next as String : null;
        legacySources = false;
      });
    } catch (value) {
      if (!mounted ||
          !scope.valid(stamp) ||
          subject != requestedSubject ||
          generation != sourcesGeneration) {
        return;
      }
      if (value is ApiError && value.status == 404 && !more) {
        // Older servers provide only a bounded preview. Read it again so a
        // missing child or revoked access cannot revive a stale local preview.
        try {
          final fallback = await widget.state.api.get(
            '/children/${widget.childId}/exams',
          );
          if (!mounted ||
              !scope.valid(stamp) ||
              subject != requestedSubject ||
              generation != sourcesGeneration) {
            return;
          }
          if (fallback['sources'] is! List) {
            throw const FormatException('Invalid legacy source list');
          }
          final items = examObjects(fallback['sources']);
          setState(() {
            loadedSources
              ..clear()
              ..addAll(items.where((item) => item['subject'] == subject));
            sourcesLoaded = true;
            sourcesMore = false;
            sourcesCursor = null;
            legacySources = true;
          });
        } catch (_) {
          if (mounted &&
              scope.valid(stamp) &&
              subject == requestedSubject &&
              generation == sourcesGeneration) {
            setState(
              () =>
                  sourcesError = 'Die Heftseiten konnten nicht geladen werden.',
            );
          }
        }
      } else {
        setState(
          () => sourcesError = value is ApiError && value.status == 409
              ? 'Die Heftseiten haben sich geändert. Lade sie neu.'
              : 'Die Heftseiten konnten nicht geladen werden.',
        );
      }
    } finally {
      if (mounted &&
          scope.owner &&
          subject == requestedSubject &&
          generation == sourcesGeneration) {
        setState(() {
          loadingSources = false;
          if (!scope.valid(stamp)) {
            sourcesError = 'Die Heftseiten wurden noch nicht geladen.';
          }
        });
      }
    }
  }

  void changed() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    scope.removeListener(changed);
    scope.dispose();
    title.dispose();
    subjectInput.dispose();
    minutesInput.dispose();
    for (final value in counters.values) {
      value.dispose();
    }
    super.dispose();
  }

  Future<void> cancel() async {
    if (!scope.current || saving) return;
    if (jsonEncode(body()) != initialFingerprint || uncertain) {
      final discard = await scope.dialog<bool>(
        context,
        (ctx) => AlertDialog(
          title: const Text('Planentwurf verwerfen?'),
          content: const Text(
            'Deine Änderungen sind noch nicht bestätigt. Du kannst sie weiterbearbeiten oder bewusst verwerfen.',
          ),
          actions: [
            TextButton(
              onPressed: () {
                if (scope.active && ModalRoute.of(ctx)?.isCurrent == true) {
                  Navigator.pop(ctx, false);
                }
              },
              child: const Text('Weiterbearbeiten'),
            ),
            FilledButton(
              onPressed: () {
                if (scope.active && ModalRoute.of(ctx)?.isCurrent == true) {
                  Navigator.pop(ctx, true);
                }
              },
              child: const Text('Entwurf verwerfen'),
            ),
          ],
        ),
      );
      if (!mounted || discard != true || !scope.current) return;
    }
    Navigator.pop(context);
  }

  Future<void> pickSubject() async {
    if (!scope.current || saving || uncertain) return;
    final stamp = scope.epoch;
    try {
      final catalog = await widget.state.api.get(
        '/children/${widget.childId}/subjects',
      );
      if (!mounted || !scope.valid(stamp)) return;
      final names =
          examObjects(catalog['items'])
              .map((item) => '${item['title'] ?? ''}')
              .where((item) => item.isNotEmpty)
              .toSet()
              .toList()
            ..sort();
      var query = '';
      final chosen = await scope.dialog<String>(
        context,
        (ctx) => StatefulBuilder(
          builder: (ctx, refresh) => Dialog(
            insetPadding: const EdgeInsets.symmetric(
              horizontal: 16,
              vertical: 12,
            ),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520, maxHeight: 460),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Fach auswählen',
                            style: Theme.of(ctx).textTheme.titleLarge,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Fachauswahl schließen',
                          onPressed: () {
                            if (scope.active &&
                                ModalRoute.of(ctx)?.isCurrent == true) {
                              FocusManager.instance.primaryFocus?.unfocus();
                              Navigator.pop(ctx);
                            }
                          },
                          icon: const Icon(Icons.close),
                        ),
                      ],
                    ),
                    TextField(
                      decoration: const InputDecoration(
                        labelText: 'Fach suchen',
                        prefixIcon: Icon(Icons.search),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                      ),
                      textInputAction: TextInputAction.search,
                      onChanged: (value) =>
                          refresh(() => query = value.trim().toLowerCase()),
                      onSubmitted: (_) =>
                          FocusManager.instance.primaryFocus?.unfocus(),
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: Builder(
                        builder: (ctx) {
                          final matches = names
                              .where(
                                (name) => name.toLowerCase().contains(query),
                              )
                              .toList();
                          if (matches.isEmpty) {
                            return const Notice('Kein Fach gefunden.');
                          }
                          return ListView.builder(
                            itemCount: matches.length,
                            itemBuilder: (ctx, index) => ListTile(
                              title: Text(matches[index]),
                              dense: true,
                              onTap: () {
                                if (scope.active &&
                                    ModalRoute.of(ctx)?.isCurrent == true) {
                                  FocusManager.instance.primaryFocus?.unfocus();
                                  Navigator.pop(ctx, matches[index]);
                                }
                              },
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
      if (chosen != null && scope.valid(stamp)) {
        setState(() {
          if (subject != chosen) {
            topics.clear();
            loadedSources.clear();
            sourcesLoaded = false;
            sourcesMore = false;
            sourcesCursor = null;
            sourcesError = null;
            loadingSources = false;
            sourcesGeneration++;
          }
          subjectInput.text = chosen;
          if (error == 'Wähle ein Fach aus.' ||
              error == 'Wähle das Fach der bestätigten Quellen.') {
            error = null;
          }
        });
      }
    } catch (value) {
      if (scope.valid(stamp)) setState(() => error = examError(value));
    }
  }

  Future<DateTime?> datePicker(DateTime initial) async {
    if (!scope.current || saving || uncertain) return null;
    final stamp = scope.epoch;
    final value = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      builder: (ctx, child) {
        scope.track(ModalRoute.of(ctx));
        return child!;
      },
    );
    return scope.valid(stamp) ? value : null;
  }

  Future<void> addTopic() async {
    if (!scope.current || topics.length >= 8 || saving || uncertain) return;
    final candidates = loadedSources.toList();
    if (candidates.isEmpty) {
      setState(
        () => error = widget.state.isChild
            ? 'Keine geprüften Seiten für dieses Fach. Bitte deine Eltern um Hilfe.'
            : 'Bestätige zuerst eine passende Heftquelle für dieses Fach.',
      );
      return;
    }
    final source = await scope.dialog<Json>(
      context,
      (ctx) => AlertDialog(
        scrollable: true,
        title: Text(
          widget.state.isChild
              ? 'Wähle ein Thema aus deinem Heft'
              : 'Bestätigte Heftquelle auswählen',
        ),
        content: SizedBox(
          width: 520,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (final item in candidates)
                ListTile(
                  title: Text(
                    '${item['topic'] ?? item['title'] ?? 'Heftquelle'}',
                  ),
                  subtitle: item['title'] == null
                      ? null
                      : Text('${item['title']}'),
                  onTap: () {
                    if (scope.active && ModalRoute.of(ctx)?.isCurrent == true) {
                      Navigator.pop(ctx, item);
                    }
                  },
                ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () {
              if (scope.active && ModalRoute.of(ctx)?.isCurrent == true) {
                Navigator.pop(ctx);
              }
            },
            child: const Text('Abbrechen'),
          ),
        ],
      ),
    );
    if (source == null || !scope.current) return;
    setState(() {
      final label = [
        '${source['topic'] ?? ''}'.trim(),
        '${source['title'] ?? ''}'.trim(),
        subject,
      ].firstWhere((value) => value.isNotEmpty);
      topics.add({
        'id': 'topic_${examRequestKey().substring(5, 21)}',
        'label': String.fromCharCodes(label.runes.take(160)),
        'question_count': 3,
        'material_refs': [
          {'id': source['id'], 'revision': source['revision']},
        ],
      });
      error = null;
    });
  }

  void clearResolvedValidationHint() {
    final message = error;
    final validCounts =
        topics.isNotEmpty &&
        topics.every(
          (topic) =>
              topic['question_count'] is int &&
              topic['question_count'] >= 1 &&
              topic['question_count'] <= 50,
        );
    if ((message == 'Wähle pro Thema zwischen 1 und 50 Aufgaben je Lerntag.' &&
            validCounts) ||
        (message == 'Wähle zwischen 5 und 60 Minuten pro Lerntag.' &&
            minutes >= 5 &&
            minutes <= 60) ||
        (message == 'Wähle mindestens einen konkreten Lerntag.' &&
            dates.isNotEmpty) ||
        (message == 'Lerntage dürfen nicht nach dem Prüfungstermin liegen.' &&
            (examDay == null ||
                dates.every(
                  (date) => date.compareTo(examDate(examDay!)) <= 0,
                )))) {
      error = null;
    }
  }

  bool validateStep() {
    String? problem;
    if (step == 0) {
      if (title.text.trim().isEmpty) {
        problem = 'Gib der Arbeit einen kurzen Titel.';
      } else if (subject.isEmpty) {
        problem = widget.state.isChild
            ? 'Wähle ein Fach aus.'
            : 'Wähle das Fach der bestätigten Quellen.';
      }
    } else if (step == 1 && !review && topics.isEmpty) {
      problem = widget.state.isChild
          ? 'Wähle mindestens ein Thema aus deinem Heft.'
          : 'Wähle mindestens ein Thema aus deinen bestätigten Heftquellen.';
    } else if (step == 1 &&
        topics.any(
          (topic) =>
              topic['question_count'] is! int ||
              topic['question_count'] < 1 ||
              topic['question_count'] > 50,
        )) {
      problem = 'Wähle pro Thema zwischen 1 und 50 Aufgaben je Lerntag.';
    } else if (step == 2 && (minutes < 5 || minutes > 60)) {
      problem = 'Wähle zwischen 5 und 60 Minuten pro Lerntag.';
    } else if (step == 2 && !review && dates.isEmpty) {
      problem = 'Wähle mindestens einen konkreten Lerntag.';
    } else if (step == 2 &&
        examDay != null &&
        dates.any((date) => date.compareTo(examDate(examDay!)) > 0)) {
      problem = 'Lerntage dürfen nicht nach dem Prüfungstermin liegen.';
    }
    setState(() => error = problem);
    return problem == null;
  }

  Json body() => {
    'purpose': widget.existing?['purpose'] ?? widget.purpose,
    'title': title.text.trim(),
    'kind': kind,
    'subject': subject,
    'exam_date': examDay == null ? null : examDate(examDay!),
    'timezone': widget.existing?['timezone'] ?? 'Europe/Berlin',
    'minutes': minutes,
    'topics': topics,
    'schedule': {'dates': dates.toList()..sort()},
    'reminders': reminders,
    'reminder_time': reminderTime,
    if (widget.existing != null) 'revision': widget.existing!['revision'],
  };
  Future<void> save() async {
    if (!scope.current || saving || (!uncertain && !validateStep())) return;
    final stamp = scope.epoch;
    final payload = pending ?? Json.from(jsonDecode(jsonEncode(body())));
    setState(() {
      saving = true;
      error = null;
      pending = payload;
    });
    try {
      final result = widget.existing == null
          ? await widget.state.api.post(
              '/children/${widget.childId}/exams',
              payload,
              {'Idempotency-Key': requestKey},
            )
          : await widget.state.api.put(
              '/exams/${widget.existing!['id']}',
              payload,
            );
      if (!mounted || !scope.valid(stamp)) return;
      Navigator.pop(context, result);
    } catch (value) {
      if (scope.valid(stamp)) {
        setState(() {
          error = examError(value);
          uncertain =
              value is! ApiError || value.status == 0 || value.status >= 500;
          if (!uncertain) pending = null;
        });
      }
    } finally {
      if (mounted && scope.valid(stamp)) setState(() => saving = false);
    }
  }

  void edit(VoidCallback action) {
    if (scope.current && !saving && !uncertain) setState(action);
  }

  Widget gap() => const SizedBox(height: 12);
  Widget basics() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      TextField(
        controller: title,
        enabled: !saving && !uncertain,
        onChanged: (value) {
          if (scope.current &&
              value.trim().isNotEmpty &&
              error == 'Gib der Arbeit einen kurzen Titel.') {
            setState(() => error = null);
          }
        },
        maxLength: 160,
        decoration: const InputDecoration(labelText: 'Titel der Arbeit'),
      ),
      gap(),
      DropdownButtonFormField<String>(
        initialValue: kind,
        isExpanded: true,
        decoration: const InputDecoration(labelText: 'Art'),
        items: const [
          DropdownMenuItem(
            value: 'classwork',
            child: Text('Klassenarbeit (KA)'),
          ),
          DropdownMenuItem(
            value: 'test',
            child: Text('Leistungskontrolle (LK)'),
          ),
        ],
        onChanged: saving || uncertain
            ? null
            : (value) => edit(() => kind = value!),
      ),
      gap(),
      OutlinedButton.icon(
        onPressed: saving || uncertain ? null : pickSubject,
        icon: const Icon(Icons.school_outlined),
        label: Text(subject.isEmpty ? 'Fach auswählen' : subject),
      ),
      gap(),
      OutlinedButton.icon(
        icon: const Icon(Icons.calendar_month_outlined),
        label: Text(
          examDay == null
              ? 'Termin auswählen (optional)'
              : 'Termin: ${friendlyDate(examDate(examDay!))}',
        ),
        onPressed: saving || uncertain
            ? null
            : () async {
                final selected = await datePicker(examDay ?? from);
                if (selected != null && scope.current) {
                  setState(() => examDay = selected);
                }
              },
      ),
      if (examDay != null)
        TextButton(
          onPressed: saving || uncertain
              ? null
              : () => edit(() => examDay = null),
          child: const Text('Termin offen lassen'),
        ),
    ],
  );
  Widget topicFields() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text(
        widget.state.isChild
            ? 'Wähle deine Themen und wie viele Aufgaben du üben möchtest.'
            : 'Aufgaben je Thema und Lerntag. Die Vorbereitung wird erst beim bewussten Start erzeugt.',
      ),
      gap(),
      for (var index = 0; index < topics.length; index++) ...[
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                '${topics[index]['label']}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              gap(),
              TextField(
                key: ValueKey(('exam-topic-count', topics[index]['id'])),
                controller: counter(topics[index]),
                enabled: !saving && !uncertain,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(2),
                ],
                decoration: const InputDecoration(
                  labelText: 'Aufgaben je Thema und Lerntag',
                  helperText: 'Individuell: 1 bis 50',
                ),
                onChanged: (value) => edit(() {
                  if (index < topics.length) {
                    topics[index]['question_count'] = int.tryParse(value) ?? 0;
                    clearResolvedValidationHint();
                  }
                }),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final count in [3, 5, 10])
                    AccessibleActionChip(
                      semanticsLabel: '$count Aufgaben',
                      label: Text('$count'),
                      onPressed: saving || uncertain
                          ? null
                          : () => edit(() {
                              if (index < topics.length) {
                                topics[index]['question_count'] = count;
                                counter(topics[index]).text = '$count';
                                clearResolvedValidationHint();
                              }
                            }),
                    ),
                ],
              ),
              TextButton.icon(
                onPressed: saving || uncertain
                    ? null
                    : () => edit(() {
                        if (index < topics.length) {
                          topics.removeAt(index);
                          clearResolvedValidationHint();
                        }
                      }),
                icon: const Icon(Icons.close),
                label: const Text('Thema entfernen'),
              ),
            ],
          ),
        ),
        gap(),
      ],
      if (loadingSources && !sourcesLoaded)
        const Center(child: CircularProgressIndicator())
      else if (sourcesError != null && !sourcesLoaded)
        Notice(sourcesError!)
      else if (hasSourcesForSubject)
        OutlinedButton.icon(
          onPressed: saving || uncertain || loadingSources || topics.length >= 8
              ? null
              : addTopic,
          icon: const Icon(Icons.add),
          label: Text(
            widget.state.isChild
                ? 'Thema aus dem Heft wählen (${topics.length}/8)'
                : 'Thema aus Heftquelle wählen (${topics.length}/8)',
          ),
        )
      else if (sourcesLoaded && !sourcesMore)
        Notice(
          widget.state.isChild
              ? 'Hier sind keine geprüften Seiten für dieses Fach geladen. Fotografiere deine Seiten. Falls eine Prüfung offen ist, helfen deine Eltern.'
              : 'Hier sind keine bestätigten Seiten für dieses Fach geladen. Ergänze oder bestätige passende Seiten im Hefter.',
        ),
      if (sourcesError != null && sourcesLoaded) Notice(sourcesError!),
      if (sourcesError != null)
        TextButton.icon(
          onPressed: loadingSources ? null : () => loadSources(),
          icon: const Icon(Icons.refresh),
          label: const Text('Heftseiten neu laden'),
        )
      else if (sourcesMore)
        TextButton.icon(
          onPressed: loadingSources ? null : () => loadSources(more: true),
          icon: const Icon(Icons.expand_more),
          label: Text(
            loadingSources ? 'Wird geladen …' : 'Weitere Heftseiten laden',
          ),
        ),
      if (legacySources)
        const Text('Hier siehst du die zuletzt geladenen Seiten.'),
      if (review)
        const Text(
          'Für eine geschriebene Arbeit kannst du diesen Schritt überspringen.',
        ),
    ],
  );
  Widget calendar() => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      Text('${dates.length} von höchstens 30 konkreten Lerntagen'),
      gap(),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          for (final date in dates.toList()..sort())
            InputChip(
              label: Text(friendlyDate(date)),
              onDeleted: saving || uncertain
                  ? null
                  : () => edit(() {
                      dates.remove(date);
                      clearResolvedValidationHint();
                    }),
            ),
        ],
      ),
      gap(),
      OutlinedButton.icon(
        icon: const Icon(Icons.event_available_outlined),
        label: const Text('Einzelnen Lerntag auswählen'),
        onPressed: saving || uncertain || dates.length >= 30
            ? null
            : () async {
                final selected = await datePicker(from);
                if (selected != null && scope.current) {
                  setState(() {
                    dates.add(examDate(selected));
                    clearResolvedValidationHint();
                  });
                }
              },
      ),
      ExpansionTile(
        title: const Text('Mehrere Tage nach Wochentagen wählen'),
        children: [
          OutlinedButton(
            onPressed: saving || uncertain
                ? null
                : () async {
                    final value = await datePicker(from);
                    if (value != null && scope.current) {
                      setState(() => from = value);
                    }
                  },
            child: Text('Von ${friendlyDate(examDate(from))}'),
          ),
          OutlinedButton(
            onPressed: saving || uncertain
                ? null
                : () async {
                    final value = await datePicker(until);
                    if (value != null && scope.current) {
                      setState(() => until = value);
                    }
                  },
            child: Text('Bis ${friendlyDate(examDate(until))}'),
          ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (var day = 1; day <= 7; day++)
                FilterChip(
                  label: Text(
                    const ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][day - 1],
                  ),
                  selected: weekdays.contains(day),
                  onSelected: saving || uncertain
                      ? null
                      : (value) => edit(() {
                          value ? weekdays.add(day) : weekdays.remove(day);
                        }),
                ),
            ],
          ),
          TextButton(
            onPressed: saving || uncertain
                ? null
                : () {
                    if (!mounted || !scope.current) return;
                    final calendarSpan = calendarDayDifference(from, until);
                    if (calendarSpan < 0 || calendarSpan > 365) {
                      setState(
                        () => error = 'Wähle einen geordneten Zeitraum von höchstens einem Jahr.',
                      );
                      return;
                    }
                    final selected = <String>{...dates};
                    for (final date in calendarDays(from, until)) {
                      if (weekdays.contains(date.weekday)) {
                        selected.add(examDate(date));
                      }
                    }
                    if (selected.length > 30) {
                      setState(() => error = 'Wähle höchstens 30 Lerntage.');
                      return;
                    }
                    setState(() {
                      dates
                        ..clear()
                        ..addAll(selected);
                      error = null;
                    });
                  },
            child: const Text('Diese konkreten Tage übernehmen'),
          ),
        ],
      ),
      gap(),
      TextField(
        controller: minutesInput,
        enabled: !saving && !uncertain,
        keyboardType: TextInputType.number,
        inputFormatters: [
          FilteringTextInputFormatter.digitsOnly,
          LengthLimitingTextInputFormatter(3),
        ],
        decoration: const InputDecoration(
          labelText: 'Minuten pro Lerntag',
          suffixText: 'Min.',
          helperText: '5 bis 60 Minuten',
        ),
        onChanged: (_) => edit(clearResolvedValidationHint),
      ),
      Text(
        widget.state.isChild ? 'Ein Vorschlag, kein Zeitlimit.' : 'Eine Empfehlung, kein Zeitlimit. Ausgelassene Tage erzeugen keinen Nachholberg.',
      ),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('An Lerntage erinnern'),
        value: reminders,
        onChanged: saving || uncertain
            ? null
            : (value) => edit(() => reminders = value),
      ),
      if (reminders)
        OutlinedButton(
          onPressed: saving || uncertain
              ? null
              : () async {
                  if (!mounted || !scope.current) return;
                  final stamp = scope.epoch;
                  final parts = reminderTime.split(':');
                  final value = await showTimePicker(
                    context: context,
                    initialTime: TimeOfDay(
                      hour: int.tryParse(parts.first) ?? 17,
                      minute: int.tryParse(parts.last) ?? 0,
                    ),
                    builder: (ctx, child) {
                      scope.track(ModalRoute.of(ctx));
                      return child!;
                    },
                  );
                  if (value != null && scope.valid(stamp)) {
                    setState(
                      () => reminderTime =
                          '${value.hour.toString().padLeft(2, '0')}:${value.minute.toString().padLeft(2, '0')}',
                    );
                  }
                },
          child: Text('Erinnerungszeit: $reminderTime'),
        ),
      if (reminders)
        const Text(
          'Europe/Berlin · Push bleibt von deiner Gerätefreigabe und deinen Ruhezeiten abhängig.',
        ),
    ],
  );
  @override
  Widget build(BuildContext context) {
    scope.bind(context);
    if (!scope.owner) return const SizedBox.shrink();
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) cancel();
      },
      child: AlertDialog(
        scrollable: true,
        title: Text(
          widget.existing == null
              ? (review ? 'Geschriebene Arbeit anlegen' : 'Arbeit planen')
              : 'Plan bearbeiten',
        ),
        content: SizedBox(
          width: 620,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                'Schritt ${step + 1} von ${review ? 1 : 4} · ${const ['Arbeit', 'Themen', 'Lerntage', 'Überblick'][step]}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              gap(),
              if (step == 0) basics(),
              if (step == 1) topicFields(),
              if (step == 2) calendar(),
              if (step == 3) ...[
                Text(
                  title.text,
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  '${kind == 'test' ? 'Leistungskontrolle' : 'Klassenarbeit'} · $subject',
                ),
                Text(
                  examDay == null
                      ? 'Termin noch offen'
                      : friendlyDate(examDate(examDay!)),
                ),
                gap(),
                for (final topic in topics)
                  Text(
                    '• ${topic['label']}: ${topic['question_count']} Aufgaben je Lerntag',
                  ),
                Text(
                  '${dates.length} ausgewählte Lerntage · $minutes Minuten empfohlen',
                ),
                for (final date in dates.toList()..sort())
                  Text(friendlyDate(date)),
                Text(
                  reminders
                      ? 'Erinnerung um $reminderTime · Europe/Berlin'
                      : 'Keine Erinnerung',
                ),
                gap(),
                const Text(
                  'Speichern plant nur. Neue Übungen und KI-Hilfen werden erst bewusst angefordert.',
                ),
              ],
              if (error != null) ...[
                gap(),
                Semantics(liveRegion: true, child: Notice(error!)),
              ],
              if (saving) const LinearProgressIndicator(),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: saving ? null : cancel,
            child: const Text('Abbrechen'),
          ),
          if (step > 0)
            TextButton(
              onPressed: saving || uncertain
                  ? null
                  : () => edit(() {
                      step--;
                      error = null;
                    }),
              child: const Text('Zurück'),
            ),
          FilledButton(
            onPressed: saving
                ? null
                : (review || step == 3)
                ? save
                : () {
                    if (scope.current && validateStep()) {
                      setState(() => step++);
                      if (step == 1 && !sourcesLoaded) loadSources();
                    }
                  },
            child: Text(
              uncertain
                  ? 'Speichern erneut bestätigen'
                  : review
                  ? 'Arbeit anlegen'
                  : step == 3
                  ? 'Plan speichern'
                  : 'Weiter',
            ),
          ),
        ],
      ),
    );
  }
}
