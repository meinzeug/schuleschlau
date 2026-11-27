import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'api.dart';
import 'ui.dart';
import 'notebook_photo.dart';

/// A conscious, source-revision-bound request. Viewing/selecting is GET-only.
class NotebookPracticeDialog extends StatefulWidget {
  final AppState state;
  final String childId, subjectId;
  final Json page;
  const NotebookPracticeDialog({
    super.key,
    required this.state,
    required this.childId,
    required this.subjectId,
    required this.page,
  });

  @override
  State<NotebookPracticeDialog> createState() => _NotebookPracticeDialogState();
}

class _NotebookPracticeDialogState extends State<NotebookPracticeDialog>
    with WidgetsBindingObserver {
  late final owner = widget.state.user;
  late final family = widget.state.familyId;
  late final token = widget.state.api.token;
  late final authenticationRevision = widget.state.api.requestIdentity().$3;
  late final pages = <String, Json>{widget.page['id']: Json.from(widget.page)};
  final count = TextEditingController(text: '2');
  final form = GlobalKey<FormState>();
  List<Json> candidates = [];
  int pageNumber = 1, total = 0, readEpoch = 0;
  bool loading = false, sending = false, expanded = false;
  String? error, listError;
  Json? sentBody;
  String? requestKey;
  String? jobId;
  bool restoring = true;
  late final requestEpoch = widget.state.notebookRequests.generation;
  late final requestSlot =
      '${owner!['id']}:$family:${widget.childId}:${widget.subjectId}:${widget.page['id']}';

  bool get sameAccount =>
      identical(widget.state.user, owner) &&
      widget.state.familyId == family &&
      widget.state.api.token == token &&
      widget.state.notebookRequests.generation == requestEpoch;

  bool get current =>
      mounted &&
      owner != null &&
      sameAccount &&
      !widget.state.authenticationPending &&
      authenticationRevision == widget.state.api.requestIdentity().$3;
  bool get active =>
      current &&
      (WidgetsBinding.instance.lifecycleState == null ||
          WidgetsBinding.instance.lifecycleState ==
              AppLifecycleState.resumed) &&
      ModalRoute.of(context)?.isCurrent == true;
  bool get locked => restoring || sending || sentBody != null;
  bool get onlyUnusableSource {
    final source = widget.page['source_learning'];
    return sentBody == null &&
        source is Map &&
        source['content'] is String &&
        (source['content'] as String).trim().isEmpty;
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.state.addListener(accountChanged);
    widget.state.authenticationChanges.addListener(accountChanged);
    if (!current) {
      WidgetsBinding.instance.addPostFrameCallback((_) => accountChanged());
    } else {
      restoreRequest();
    }
  }

  void applyRequest(Json value) {
    final body = value['body'];
    final sources = body is Map ? body['notebook_sources'] : null;
    if (body is! Map ||
        body['material_id'] != widget.page['id'] ||
        body['question_count'] is! int ||
        body['question_count'] < 2 ||
        body['question_count'] > 5 ||
        sources is! List ||
        sources.isEmpty ||
        sources.length > 12 ||
        sources.any(
          (s) =>
              s is! Map ||
              s['id'] is! String ||
              s['revision'] is! int ||
              s['revision'] < 1,
        ) ||
        value['key'] is! String ||
        !RegExp(r'^notebook-[a-f0-9]{32}$').hasMatch(value['key']) ||
        (value['job_id'] != null && value['job_id'] is! String)) {
      throw ApiError(
        'Der gespeicherte Auftrag konnte nicht sicher zugeordnet werden.',
      );
    }
    sentBody = Json.from(value['body']);
    requestKey = value['key'] as String;
    jobId = value['job_id'] as String?;
    count.text = '${sentBody!['question_count']}';
    pages
      ..clear()
      ..addEntries([
        for (final source in sentBody!['notebook_sources'])
          MapEntry(source['id'] as String, Json.from(source)),
      ]);
  }

  Future<void> restoreRequest() async {
    try {
      final value = await widget.state.notebookRequests.get(requestSlot);
      if (!current) return;
      if (value != null) applyRequest(value);
      setState(() => restoring = false);
    } catch (_) {
      if (current) {
        setState(
          () => error = 'Der gespeicherte Auftrag konnte nicht geladen werden. Öffne die Seite erneut.',
        );
      }
    }
  }

  Future<void> newRound() async {
    if (!active || sending || jobId == null) return;
    setState(() => sending = true);
    try {
      await widget.state.notebookRequests.finish(
        requestSlot,
        requestKey!,
        null,
        requestEpoch,
      );
      if (!active) return;
      setState(() {
        sentBody = null;
        requestKey = jobId = null;
        pages
          ..clear()
          ..[widget.page['id']] = Json.from(widget.page);
      });
    } catch (_) {
      if (current) {
        setState(() => error = 'Der Auftrag konnte nicht abgeglichen werden.');
      }
    } finally {
      if (current) setState(() => sending = false);
    }
  }

  void accountChanged() {
    if (!current && mounted) {
      readEpoch++;
      setState(() {
        candidates = [];
        pages.clear();
        error = listError = null;
      });
      final route = ModalRoute.of(context);
      if (route is DialogRoute) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (route.isActive) route.navigator?.removeRoute(route);
        });
        WidgetsBinding.instance.ensureVisualUpdate();
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      readEpoch++;
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  void dispose() {
    readEpoch++;
    WidgetsBinding.instance.removeObserver(this);
    widget.state.removeListener(accountChanged);
    widget.state.authenticationChanges.removeListener(accountChanged);
    count.dispose();
    super.dispose();
  }

  Future<void> loadPages(int number) async {
    if (!active || loading || locked) return;
    final ticket = ++readEpoch;
    setState(() {
      loading = true;
      listError = null;
    });
    try {
      final result = await widget.state.api.get(
        Uri(
          path: '/children/${widget.childId}/materials',
          queryParameters: {
            'subject_id': widget.subjectId,
            'status': 'confirmed',
            'sort': 'newest',
            'page': '$number',
            'page_size': '20',
          },
        ).toString(),
      );
      if (!current || ticket != readEpoch) return;
      final rows = [
        for (final value in result['items'] as List) Json.from(value),
      ];
      if (rows.any(
        (r) =>
            r['subject_id'] != widget.subjectId ||
            r['id'] is! String ||
            r['revision'] is! int,
      )) {
        throw ApiError(
          'Die Heftseiten konnten nicht sicher zugeordnet werden.',
        );
      }
      setState(() {
        candidates = rows
            .where(
              (r) =>
                  r['confirmed'] == true &&
                  r['purpose'] == 'notebook' &&
                  r['synthetic'] != true &&
                  r['fixed_example'] != true,
            )
            .toList();
        pageNumber = number;
        total = result['total'] as int;
      });
    } catch (e) {
      if (current && ticket == readEpoch) {
        setState(
          () => listError = e is ApiError
              ? e.message
              : 'Die Seiten konnten nicht geladen werden.',
        );
      }
    } finally {
      if (current && ticket == readEpoch) setState(() => loading = false);
    }
  }

  Future<void> prepare() async {
    if (!active ||
        restoring ||
        sending ||
        onlyUnusableSource ||
        !(form.currentState?.validate() ?? false)) {
      return;
    }
    if (jobId != null) {
      Navigator.of(context).pop(jobId);
      return;
    }
    var reconciliation = sentBody != null;
    FocusManager.instance.primaryFocus?.unfocus();
    sentBody ??= {
      'material_id': widget.page['id'],
      'notebook_sources': [
        for (final row in pages.values)
          {'id': row['id'], 'revision': row['revision']},
      ],
      'question_count': int.parse(count.text),
    };
    requestKey ??=
        'notebook-${List.generate(16, (_) => Random.secure().nextInt(256).toRadixString(16).padLeft(2, '0')).join()}';
    setState(() {
      sending = true;
      error = null;
    });
    try {
      final saved = await widget.state.notebookRequests.claim(requestSlot, {
        'body': sentBody,
        'key': requestKey,
      }, requestEpoch);
      if (!mounted || !active) return;
      reconciliation = reconciliation || saved['key'] != requestKey;
      applyRequest(saved);
      if (jobId != null) {
        Navigator.of(context).pop(jobId);
        return;
      }
      final result = await widget.state.api.post(
        '/children/${widget.childId}/units',
        sentBody,
        {
          'Idempotency-Key': requestKey!,
          'X-Schulpilot-Account': owner!['id'] as String,
        },
      );
      if (result['id'] is! String) {
        throw ApiError('Der vorbereitete Stand konnte nicht geöffnet werden.');
      }
      if (!sameAccount) return;
      await widget.state.notebookRequests.finish(
        requestSlot,
        requestKey!,
        result['id'] as String,
        requestEpoch,
      );
      if (!mounted || !active) return;
      Navigator.of(context).pop(result['id'] as String);
    } catch (e) {
      bool rejected = false;
      if (!reconciliation &&
          sameAccount &&
          e is ApiError &&
          e.status >= 400 &&
          e.status < 500) {
        try {
          await widget.state.notebookRequests.finish(
            requestSlot,
            requestKey!,
            null,
            requestEpoch,
          );
          rejected = true;
        } catch (_) {
          // Keep the key/body when local storage cannot confirm removal.
        }
      }
      if (!current) return;
      setState(() {
        error = e is ApiError ? e.message : 'Die Verbindung wurde unterbrochen. Du kannst denselben Auftrag abgleichen.';
        // A definitive rejection created no job. Unknown outcomes retain the
        // exact payload/key; a deliberate reconciliation cannot reserve twice.
        if (rejected) {
          sentBody = null;
          requestKey = null;
        }
      });
    } finally {
      if (current) setState(() => sending = false);
    }
  }

  String title(Json row) =>
      [row['topic'], row['title']]
          .whereType<String>()
          .where((text) => text.trim().isNotEmpty)
          .firstOrNull ??
      'Bestätigte Heftseite';

  @override
  Widget build(BuildContext context) {
    if (!current) return const SizedBox.shrink();
    return AlertDialog(
      title: const Text('Übungen zu deinem Heft'),
      titlePadding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      contentPadding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
      actionsPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      scrollable: true,
      content: SizedBox(
        width: 520,
        child: Form(
          key: form,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title(widget.page),
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              if (pages.length > 1) ...[
                const SizedBox(height: 4),
                Text('${pages.length} Heftseiten ausgewählt'),
              ],
              if (onlyUnusableSource) ...[
                const SizedBox(height: 12),
                Notice(
                  widget.state.isChild
                      ? 'Diese Seite hat noch keinen sicher lesbaren Lernstoff. Deine Eltern können offene Stellen prüfen. Wähle zum Lernen eine andere Heftseite.'
                      : 'Diese Seite hat noch keinen sicher lesbaren Lernstoff. Prüfe offene Stellen oder wähle eine andere Heftseite.',
                  warning: true,
                ),
              ],
              const SizedBox(height: 8),
              if (!onlyUnusableSource)
                TextFormField(
                  controller: count,
                  enabled: !locked,
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  decoration: const InputDecoration(
                    labelText: 'Anzahl der Aufgaben',
                    helperText: '2 bis 5 Aufgaben pro Runde',
                    isDense: true,
                  ),
                  validator: (value) {
                    final n = int.tryParse(value ?? '');
                    return n == null || n < 2 || n > 5
                        ? 'Bitte eine Zahl von 2 bis 5 eingeben.'
                        : null;
                  },
                ),
              const SizedBox(height: 8),
              if (!onlyUnusableSource)
                ExpansionTile(
                  initiallyExpanded: expanded,
                  title: const Text('Weitere Heftseiten hinzufügen'),
                  onExpansionChanged: locked
                      ? null
                      : (value) {
                          setState(() => expanded = value);
                          if (value && candidates.isEmpty) loadPages(1);
                        },
                  children: [
                    if (pages.length > 1)
                      Wrap(
                        spacing: 4,
                        children: [
                          for (final row in pages.values)
                            if (row['id'] != widget.page['id'])
                              InputChip(
                                label: Text(
                                  title(row),
                                  overflow: TextOverflow.ellipsis,
                                ),
                                onDeleted: locked
                                    ? null
                                    : () => setState(
                                        () => pages.remove(row['id']),
                                      ),
                              ),
                        ],
                      ),
                    if (loading) const LinearProgressIndicator(),
                    if (listError != null) ...[
                      Text(listError!),
                      TextButton(
                        onPressed: locked ? null : () => loadPages(pageNumber),
                        child: const Text('Seiten erneut laden'),
                      ),
                    ],
                    for (final row in candidates)
                      CheckboxListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(title(row)),
                        secondary: row['has_image'] == true
                            ? SizedBox(
                                width: 48,
                                height: 64,
                                child: NotebookPhoto(
                                  widget.state,
                                  materialId: row['id'] as String,
                                  revision: row['revision'] as int,
                                  thumbnail: true,
                                ),
                              )
                            : null,
                        value: pages.containsKey(row['id']),
                        onChanged: locked || row['id'] == widget.page['id']
                            ? null
                            : (value) {
                                if (!active) return;
                                if (value == true && pages.length >= 12) {
                                  toast(
                                    context,
                                    'Wähle höchstens 12 Heftseiten für eine Runde.',
                                  );
                                  return;
                                }
                                setState(() {
                                  if (value == true) {
                                    pages[row['id']] = row;
                                  } else {
                                    pages.remove(row['id']);
                                  }
                                });
                              },
                      ),
                    if (!loading && listError == null && candidates.isEmpty)
                      const Text(
                        'Hier gibt es keine weiteren bestätigten Heftseiten.',
                      ),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        IconButton(
                          tooltip: 'Vorherige Heftseiten',
                          onPressed: locked || loading || pageNumber <= 1
                              ? null
                              : () => loadPages(pageNumber - 1),
                          icon: const Icon(Icons.chevron_left),
                        ),
                        Flexible(
                          child: Text(
                            'Seite $pageNumber',
                            textAlign: TextAlign.center,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Nächste Heftseiten',
                          onPressed:
                              locked || loading || pageNumber * 20 >= total
                              ? null
                              : () => loadPages(pageNumber + 1),
                          icon: const Icon(Icons.chevron_right),
                        ),
                      ],
                    ),
                  ],
                ),
              const SizedBox(height: 8),
              if (sentBody != null)
                Text(
                  jobId != null
                      ? 'Diese Vorbereitung ist bereits gespeichert. Du kannst sie öffnen oder bewusst eine neue Runde anfragen.'
                      : 'Ein Auftrag wurde bereits angefragt. Gleiche denselben Auftrag ab; dabei wird keine zweite Runde angelegt.',
                ),
              if (jobId != null)
                TextButton(
                  onPressed: sending ? null : newRound,
                  child: const Text('Neue Runde auswählen'),
                ),
              if (error != null)
                Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
      actions: [
        Row(
          children: [
            Expanded(
              flex: 2,
              child: TextButton(
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                ),
                onPressed: sending
                    ? null
                    : () {
                        if (active) Navigator.of(context).pop();
                      },
                child: const Text('Zurück'),
              ),
            ),
            if (!onlyUnusableSource) ...[
              const SizedBox(width: 8),
              Expanded(
                flex: 4,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                  ),
                  onPressed: sending || restoring || onlyUnusableSource
                      ? null
                      : prepare,
                  child: Text(
                    restoring
                        ? 'Gespeicherten Auftrag prüfen …'
                        : sending
                        ? 'Wird angefragt …'
                        : jobId != null
                        ? 'Vorbereitung öffnen'
                        : sentBody != null
                        ? 'Vorbereitung abgleichen'
                        : 'Runde vorbereiten',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }
}
