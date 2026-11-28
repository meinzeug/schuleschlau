import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'admin_workspace_ui.dart';
import 'api.dart';
import 'ui.dart';

/// Shared public candidates only. This screen never reads a family or learner.
class AdminMediaExplorerScreen extends StatefulWidget {
  final AppState state;

  /// Injectable for widget tests; real launches still require an explicit tap.
  final Future<bool> Function(Uri)? openExternal;
  const AdminMediaExplorerScreen(this.state, {super.key, this.openExternal});

  @override
  State<AdminMediaExplorerScreen> createState() =>
      _AdminMediaExplorerScreenState();
}

Uri? _safeYoutubeUrl(Object? value) {
  if (value is! String) return null;
  final match = RegExp(
    r'^https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}$',
  ).firstMatch(value);
  if (match == null || match.end != value.length) {
    return null;
  }
  return Uri.tryParse(value);
}

String _checkedDate(Object? value) {
  if (value is! int || value < 946684800 || value >= 4102444800) {
    return 'unbekannt';
  }
  final date = DateTime.fromMillisecondsSinceEpoch(value * 1000, isUtc: true);
  return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')}.${date.year}';
}

class _AdminMediaExplorerScreenState extends State<AdminMediaExplorerScreen> {
  late final Json? owner;
  late final String? ownerToken, ownerFamily;
  late (Object?, String?, int?) identity;
  final age = TextEditingController();
  final contextText = TextEditingController();
  final counterpoint = TextEditingController();
  Json? listing, detail;
  String? error, notice, cursor;
  final previous = <String?>[];
  String? decision, contentKind;
  bool reviewed = false, loading = false, saving = false, paused = false;
  bool routeCovered = false;
  int generation = 0, draftVersion = 0;

  bool get sameOwner =>
      mounted &&
      owner != null &&
      widget.state.isAdmin &&
      identical(owner, widget.state.user) &&
      ownerToken == widget.state.api.token &&
      ownerFamily == widget.state.familyId;
  bool get current =>
      sameOwner &&
      !paused &&
      !widget.state.authenticationPending &&
      widget.state.api.ownsRequest(identity);
  bool get visible => current && ModalRoute.of(context)?.isCurrent != false;
  String? get selectedId =>
      detail?['id'] is String ? detail!['id'] as String : null;
  static bool validId(Object? id) =>
      id is String && RegExp(r'^[a-f0-9]{32}$').hasMatch(id);

  @override
  void initState() {
    super.initState();
    owner = widget.state.user;
    ownerToken = widget.state.api.token;
    ownerFamily = widget.state.familyId;
    identity = widget.state.api.requestIdentity();
    widget.state.addListener(accountChanged);
    widget.state.authenticationChanges.addListener(authenticationChanged);
    paused = widget.state.authenticationPending;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (current) load();
    });
  }

  void resetDraft() {
    draftVersion++;
    age.clear();
    contextText.clear();
    counterpoint.clear();
    decision = contentKind = null;
    reviewed = false;
  }

  void invalidate() {
    generation++;
    resetDraft();
    if (mounted) {
      setState(() {
        listing = detail = null;
        cursor = error = notice = null;
        previous.clear();
        loading = saving = false;
        paused = true;
      });
    }
  }

  void accountChanged() {
    if (!sameOwner) invalidate();
  }

  void authenticationChanged() => invalidate();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final covered = ModalRoute.of(context)?.isCurrent == false;
    if (covered && !routeCovered && (loading || saving)) {
      generation++;
      if (saving) {
        detail = null;
        resetDraft();
        error = 'Der Speicherstand ist unklar. Bitte öffne das Medium erneut.';
      }
      loading = saving = false;
    }
    routeCovered = covered;
  }

  void resume() {
    if (!sameOwner ||
        widget.state.authenticationPending ||
        ModalRoute.of(context)?.isCurrent == false) {
      return;
    }
    setState(() {
      identity = widget.state.api.requestIdentity();
      paused = false;
    });
    load();
  }

  @override
  void didUpdateWidget(covariant AdminMediaExplorerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.state, widget.state)) {
      oldWidget.state.removeListener(accountChanged);
      oldWidget.state.authenticationChanges.removeListener(
        authenticationChanged,
      );
      widget.state.addListener(accountChanged);
      widget.state.authenticationChanges.addListener(authenticationChanged);
      invalidate();
    }
  }

  @override
  void dispose() {
    generation++;
    widget.state.removeListener(accountChanged);
    widget.state.authenticationChanges.removeListener(authenticationChanged);
    age.dispose();
    contextText.dispose();
    counterpoint.dispose();
    super.dispose();
  }

  String errorText(Object e) => e is ApiError && e.status == 409
      ? 'Der Stand wurde geändert. Bitte lade das Medium neu.'
      : 'Die Medienredaktion ist gerade nicht erreichbar. Bitte versuche es erneut.';

  Future<void> load({String? after, int navigation = 0}) async {
    if (!visible || loading || saving) return;
    final request = ++generation;
    setState(() {
      loading = true;
      error = notice = null;
      detail = null;
      resetDraft();
    });
    try {
      final params = <String, String>{'limit': '20'};
      if (after != null) params['after'] = after;
      final response = await widget.state.api.get(
        Uri(path: '/admin/media-explorer', queryParameters: params).toString(),
      );
      if (!visible || request != generation) return;
      setState(() {
        if (navigation == 1) previous.add(cursor);
        if (navigation == -1 && previous.isNotEmpty) previous.removeLast();
        listing = response;
        cursor = after;
      });
    } catch (e) {
      if (visible && request == generation) {
        setState(() => error = errorText(e));
      }
    } finally {
      if (visible && request == generation) setState(() => loading = false);
    }
  }

  Future<void> open(Json candidate) async {
    final id = candidate['id'];
    if (!visible || loading || saving || !validId(id)) return;
    final request = ++generation;
    setState(() {
      loading = true;
      error = notice = null;
      detail = null;
      resetDraft();
    });
    try {
      final response = await widget.state.api.get('/admin/media-explorer/$id');
      if (!visible || request != generation || response['id'] != id) return;
      setState(() => detail = response);
    } catch (e) {
      if (visible && request == generation) {
        setState(() => error = errorText(e));
      }
    } finally {
      if (visible && request == generation) setState(() => loading = false);
    }
  }

  Future<void> openVideo() async {
    if (!visible || saving || detail == null) return;
    final item = detail;
    final uri = _safeYoutubeUrl(item?['url']);
    if (uri == null || item?['provider'] != 'youtube') return;
    final request = generation;
    bool opened = false;
    try {
      opened =
          await (widget.openExternal?.call(uri) ??
              launchUrl(
                uri,
                mode: LaunchMode.externalApplication,
                webOnlyWindowName: '_blank',
              ));
    } catch (_) {
      /* Keep the editor available when a browser cannot open it. */
    }
    if (visible &&
        request == generation &&
        identical(item, detail) &&
        !opened) {
      setState(() => error = 'Der Link konnte nicht geöffnet werden.');
    }
  }

  Future<void> save() async {
    final shown = detail;
    final id = selectedId;
    final selected = decision, kind = contentKind;
    final minimumAge = int.tryParse(age.text);
    if (!visible || saving || shown == null || !validId(id)) return;
    final revision = shown['revision'];
    final review = shown['review'];
    final previousReview = review == null
        ? 0
        : review is Map
        ? review['review_number']
        : null;
    if (revision is! int ||
        revision < 1 ||
        previousReview is! int ||
        previousReview < 0) {
      setState(
        () => error =
            'Der Prüfstand ist unvollständig. Bitte lade das Medium neu.',
      );
      return;
    }
    if (selected == null ||
        kind == null ||
        minimumAge == null ||
        minimumAge < 0 ||
        minimumAge > 99) {
      setState(
        () => error = 'Bitte Entscheidung, Inhaltsart und ein Mindestalter von 0 bis 99 angeben.',
      );
      return;
    }
    if (selected == 'approved' && !reviewed) {
      setState(
        () => error = 'Für eine Freigabe musst du den Inhalt selbst prüfen und dies bestätigen.',
      );
      return;
    }
    if (selected == 'approved' &&
        kind != 'general' &&
        contextText.text.trim().isEmpty) {
      setState(() => error = 'Bitte gib eine altersgerechte Einordnung an.');
      return;
    }
    if (selected == 'approved' &&
        (kind == 'propaganda' || kind == 'sensitive') &&
        counterpoint.text.trim().isEmpty) {
      setState(() => error = 'Bitte ergänze eine Gegenperspektive.');
      return;
    }
    final request = generation;
    setState(() {
      saving = true;
      error = notice = null;
    });
    try {
      final value = await widget.state.api.post(
        '/admin/media-explorer/$id/decisions',
        {
          'resource_revision': revision,
          'previous_review': previousReview,
          'decision': selected,
          'evidence_scope': reviewed ? 'content' : 'metadata',
          'content_kind': kind,
          'min_age': minimumAge,
          'context': contextText.text.trim(),
          'counterpoint': counterpoint.text.trim(),
          'content_reviewed': reviewed,
        },
      );
      if (!visible ||
          request != generation ||
          !identical(shown, detail) ||
          value['id'] != id) {
        return;
      }
      final savedReview = value['review'];
      if (value['revision'] != revision ||
          savedReview is! Map ||
          savedReview['resource_revision'] != revision ||
          savedReview['review_number'] != previousReview + 1 ||
          savedReview['decision'] != selected) {
        setState(() {
          detail = null;
          resetDraft();
          error =
              'Der Speicherstand ist unklar. Bitte öffne das Medium erneut.';
        });
        return;
      }
      setState(() {
        detail = value;
        notice = 'Entscheidung gespeichert.';
        resetDraft();
      });
    } catch (e) {
      if (!visible || request != generation || !identical(shown, detail)) {
        return;
      }
      setState(() {
        final unknown = e is ApiError && (e.status == 0 || e.status >= 500);
        error = unknown
            ? 'Der Speicherstand ist unklar. Bitte öffne das Medium erneut.'
            : errorText(e);
        if (unknown || (e is ApiError && e.status == 409)) {
          detail = null;
          resetDraft();
        }
      });
    } finally {
      if (visible && request == generation) setState(() => saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!sameOwner) return const SizedBox.shrink();
    if (paused || widget.state.authenticationPending) {
      return PageFrame(
        state: widget.state,
        title: 'Medienredaktion',
        child: Column(
          children: [
            const Text('Die Ansicht ist pausiert.'),
            TextButton(
              onPressed: widget.state.authenticationPending ? null : resume,
              child: const Text('Ansicht wieder öffnen'),
            ),
          ],
        ),
      );
    }
    final items = listing?['items'] is List
        ? (listing!['items'] as List).whereType<Map>().map(Json.from).toList()
        : <Json>[];
    final next = listing?['next'];
    return PageFrame(
      state: widget.state,
      title: 'Medienredaktion',
      showTitle: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const AdminWorkspaceHeader(
            title: 'Medienredaktion',
            currentPath: '/admin/media-explorer',
            subtitle: 'Öffentliche Kandidaten selbst sichten und Entscheidungen dokumentieren.',
          ),
          const SizedBox(height: 16),
          if (notice != null)
            Semantics(liveRegion: true, child: Notice(notice!)),
          if (error != null) Semantics(liveRegion: true, child: Notice(error!)),
          if (loading) const LinearProgressIndicator(),
          if (detail != null) ...[
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: saving || !visible
                    ? null
                    : () {
                        generation++;
                        setState(() {
                          detail = null;
                          resetDraft();
                          error = notice = null;
                        });
                      },
                icon: const Icon(Icons.arrow_back_rounded),
                label: const Text('Zur Kandidatenliste'),
              ),
            ),
            _detailView(detail!),
          ] else ...[
            if (!loading && listing == null)
              OutlinedButton.icon(
                onPressed: visible ? () => load(after: cursor) : null,
                icon: const Icon(Icons.refresh_rounded),
                label: const Text('Liste laden'),
              ),
            if (listing != null && items.isEmpty)
              Notice(
                previous.isEmpty ? 'Noch keine Medienkandidaten vorhanden.' : 'Auf dieser Seite sind keine Medien mehr. Über „Zurück“ erreichst du die vorherige Seite.',
              ),
            for (final item in items) _candidate(item),
            if (listing != null)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton(
                    onPressed: previous.isEmpty || loading
                        ? null
                        : () {
                            if (!visible) return;
                            load(after: previous.last, navigation: -1);
                          },
                    child: const Text('Zurück'),
                  ),
                  OutlinedButton(
                    onPressed: !validId(next) || loading
                        ? null
                        : () {
                            if (!visible) return;
                            load(after: next as String, navigation: 1);
                          },
                    child: const Text('Weitere Kandidaten'),
                  ),
                  TextButton(
                    onPressed: loading ? null : () => load(after: cursor),
                    child: const Text('Aktualisieren'),
                  ),
                ],
              ),
          ],
        ],
      ),
    );
  }

  Widget _candidate(Json item) => Panel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${item['title'] ?? 'Titel nicht verfügbar'}',
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
        ),
        Text('Quelle: ${item['channel'] ?? 'unbekannt'}'),
        Text(
          item['review'] is Map
              ? 'Prüfstand: ${_reviewStatus(item)}'
              : 'Noch nicht redaktionell geprüft',
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: validId(item['id']) && !loading && visible
              ? () => open(item)
              : null,
          icon: const Icon(Icons.fact_check_outlined),
          label: const Text('Medium prüfen'),
        ),
      ],
    ),
  );

  String _decisionLabel(Object? value) => switch (value) {
    'approved' => 'Freigabe vermerkt',
    'rejected' => 'Abgelehnt',
    'blocked' => 'Gesperrt',
    _ => 'Unbekannt',
  };

  String _kindLabel(Object? value) => switch (value) {
    'general' => 'Allgemein',
    'historical_source' => 'Historische Quelle',
    'propaganda' => 'Propaganda',
    'sensitive' => 'Sensibler Inhalt',
    _ => 'Offen',
  };

  String _reviewStatus(Json item) {
    final value = item['review'];
    if (value is! Map) return 'Offen';
    if (value['resource_revision'] != item['revision']) {
      return 'Frühere Prüfung veraltet';
    }
    if (value['decision'] == 'approved' &&
        value['evidence_scope'] != 'content') {
      return 'Freigabe unvollständig';
    }
    return _decisionLabel(value['decision']);
  }

  Widget _detailView(Json item) {
    final link = _safeYoutubeUrl(item['url']);
    final oldReview = item['review'] is Map ? item['review'] as Map : null;
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            '${item['title'] ?? 'Titel nicht verfügbar'}',
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
          ),
          Text('Quelle: ${item['channel'] ?? 'unbekannt'}'),
          Text(
            item['available'] == true
                ? 'Zuletzt gemeldeter Quellenstatus: verfügbar'
                : 'Verfügbarkeit nicht bestätigt',
          ),
          if (item['checked_at'] is num)
            Text(
              'Metadaten geprüft (UTC): ${_checkedDate(item['checked_at'])} · Region: ${item['checked_region'] ?? 'offen'}',
            ),
          Text(
            oldReview != null
                ? 'Bisher: ${_reviewStatus(item)}'
                : 'Bisher keine Inhaltsprüfung',
          ),
          if (oldReview != null) ...[
            Text(
              'Prüfumfang: ${switch (oldReview['evidence_scope']) {
                'content' => 'Inhalt',
                'metadata' => 'Metadaten',
                _ => 'offen',
              }}',
            ),
            Text('Bisheriges Mindestalter: ${oldReview['min_age'] ?? 'offen'}'),
            Text(
              'Bisherige Inhaltsart: ${_kindLabel(oldReview['content_kind'])}',
            ),
            if (oldReview['context'] is String &&
                (oldReview['context'] as String).trim().isNotEmpty)
              Text('Einordnung: ${oldReview['context']}'),
            if (oldReview['counterpoint'] is String &&
                (oldReview['counterpoint'] as String).trim().isNotEmpty)
              Text('Gegenperspektive: ${oldReview['counterpoint']}'),
          ],
          const Text(
            'Eine Freigabe allein ist noch keine Empfehlung. Lehrplanzuordnung und aktuelle Verfügbarkeit werden separat geprüft.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Öffne die Quelle zur eigenen Sichtung. Der Link öffnet einen externen Dienst.',
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              onPressed:
                  item['provider'] == 'youtube' &&
                      link != null &&
                      !saving &&
                      visible
                  ? openVideo
                  : null,
              icon: const Icon(Icons.open_in_new_rounded),
              label: const Text('Quelle extern öffnen'),
            ),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            key: ValueKey('media-decision-$draftVersion'),
            initialValue: decision,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Entscheidung'),
            items: const [
              DropdownMenuItem(value: 'approved', child: Text('Freigeben')),
              DropdownMenuItem(value: 'rejected', child: Text('Ablehnen')),
              DropdownMenuItem(value: 'blocked', child: Text('Sperren')),
            ],
            onChanged: saving || !current
                ? null
                : (value) {
                    if (visible) setState(() => decision = value);
                  },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            key: ValueKey('media-kind-$draftVersion'),
            initialValue: contentKind,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Inhaltsart'),
            items: const [
              DropdownMenuItem(value: 'general', child: Text('Allgemein')),
              DropdownMenuItem(
                value: 'historical_source',
                child: Text('Historische Quelle'),
              ),
              DropdownMenuItem(value: 'propaganda', child: Text('Propaganda')),
              DropdownMenuItem(
                value: 'sensitive',
                child: Text('Sensibler Inhalt'),
              ),
            ],
            onChanged: saving || !current
                ? null
                : (value) {
                    if (visible) setState(() => contentKind = value);
                  },
          ),
          const SizedBox(height: 12),
          TextField(
            controller: age,
            enabled: !saving && visible,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'Mindestalter',
              hintText: '0 bis 99',
            ),
            maxLength: 2,
          ),
          const Text(
            'Nur öffentliche Inhalte beschreiben. Keine Angaben zu Kindern oder Familien eintragen.',
          ),
          TextField(
            controller: contextText,
            enabled: !saving && visible,
            maxLength: 2000,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Altersgerechte Einordnung',
              hintText: 'Bei historischen und sensiblen Quellen erforderlich',
            ),
          ),
          TextField(
            controller: counterpoint,
            enabled: !saving && visible,
            maxLength: 2000,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Gegenperspektive',
              hintText: 'Bei Propaganda und sensiblen Inhalten erforderlich',
            ),
          ),
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            value: reviewed,
            onChanged: saving || !visible
                ? null
                : (value) => setState(() => reviewed = value == true),
            title: const Text(
              'Ich habe den Inhalt selbst angesehen und geprüft.',
            ),
          ),
          const Text(
            'Eine Freigabe erfordert die bestätigte Inhaltsprüfung. Eine Sperre ist auch ohne Sichtung möglich.',
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: saving || !visible ? null : save,
            icon: const Icon(Icons.save_outlined),
            label: const Text('Entscheidung speichern'),
          ),
        ],
      ),
    );
  }
}
