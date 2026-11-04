import 'package:flutter/material.dart';

import 'api.dart';

/// Separates a human review from both the OCR transcript and the learning source.
class MaterialVisualReview extends StatefulWidget {
  const MaterialVisualReview({
    super.key,
    required this.state,
    required this.data,
    required this.onRefresh,
  });
  final AppState state;
  final Json data;
  final VoidCallback onRefresh;

  @override
  State<MaterialVisualReview> createState() => _MaterialVisualReviewState();
}

class _MaterialVisualReviewState extends State<MaterialVisualReview> {
  late final account = widget.state.user;
  late final family = widget.state.familyId;
  late final token = widget.state.api.token;
  Object? materialId;
  Object? materialRevision;
  Object? observationsDigest;
  List<dynamic>? localReviews;
  bool get current =>
      mounted &&
      account != null &&
      identical(account, widget.state.user) &&
      family == widget.state.familyId &&
      token == widget.state.api.token;
  @override
  void initState() {
    super.initState();
    materialId = widget.data['id'];
    materialRevision = widget.data['revision'];
    observationsDigest = widget.data['visual_observations_digest'];
    widget.state.addListener(accountChanged);
  }

  void accountChanged() {
    if (mounted && !current) {
      setState(() {
        localReviews = null;
      });
    }
  }

  @override
  void didUpdateWidget(covariant MaterialVisualReview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (materialId != widget.data['id'] ||
        materialRevision != widget.data['revision'] ||
        observationsDigest != widget.data['visual_observations_digest']) {
      localReviews = null;
      materialId = widget.data['id'];
      materialRevision = widget.data['revision'];
      observationsDigest = widget.data['visual_observations_digest'];
    }
  }

  @override
  void dispose() {
    widget.state.removeListener(accountChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!current) return const SizedBox.shrink();
    const overflowWarning =
        'Nicht alle Bildbefunde werden angezeigt. Schau dir das Foto an.';
    final warnings = widget.data['quality_warnings'];
    final hasOverflow = warnings is List && warnings.contains(overflowWarning);
    final observations = widget.data['visual_observations'] is List
        ? widget.data['visual_observations'] as List
        : const [];
    final reviews =
        localReviews ??
        (widget.data['visual_observation_reviews'] is List
            ? widget.data['visual_observation_reviews'] as List
            : const []);
    final canReview =
        widget.data['revision'] is int &&
        widget.data['visual_observations_digest'] is String &&
        widget.data['id'] is String &&
        widget.data['image_digest'] is String &&
        widget.data['fixture_id'] == null &&
        widget.data['synthetic'] != true &&
        (!widget.state.isParent || widget.state.canManage);
    final entries = <Widget>[];
    for (var i = 0; i < observations.length; i++) {
      final value = observations[i];
      if (value is! Map ||
          value['description'] is! String ||
          (value['description'] as String).trim().isEmpty) {
        continue;
      }
      final matched = reviews
          .whereType<Map>()
          .where((r) => r['index'] == i)
          .toList();
      final review = matched.isEmpty ? null : matched.first;
      entries.add(
        _VisualItem(
          key: ValueKey((
            widget.data['id'],
            widget.data['revision'],
            widget.data['visual_observations_digest'],
            i,
            ObjectKey(account),
          )),
          original: Map<String, dynamic>.from(value),
          review: review == null ? null : Map<String, dynamic>.from(review),
          enabled: canReview,
          submit: (decision, observation, version) async {
            if (!current) throw ApiError('Bitte neu anmelden.');
            final snapshotId = widget.data['id'];
            final snapshotRevision = widget.data['revision'];
            final snapshotDigest = widget.data['visual_observations_digest'];
            final result = await widget.state.api.put(
              '/materials/$snapshotId/visual-observations/$i/review',
              {
                'revision': snapshotRevision,
                'image_digest': widget.data['image_digest'],
                'observations_digest': snapshotDigest,
                'review_version': version,
                'decision': decision,
                'observation': observation,
              },
            );
            if (!current ||
                widget.data['id'] != snapshotId ||
                widget.data['revision'] != snapshotRevision ||
                widget.data['visual_observations_digest'] != snapshotDigest) {
              return;
            }
            if (result['visual_observation_reviews'] is List) {
              setState(
                () =>
                    localReviews = result['visual_observation_reviews'] as List,
              );
            }
            widget.onRefresh();
          },
        ),
      );
    }
    if (entries.isEmpty && !hasOverflow) return const SizedBox.shrink();
    return ExpansionTile(
      tilePadding: EdgeInsets.zero,
      initiallyExpanded: true,
      leading: const Icon(Icons.image_outlined),
      title: const Text('Bilder auf der Seite'),
      children: [
        if (hasOverflow)
          const Padding(
            padding: EdgeInsets.only(bottom: 8),
            child: Text(overflowWarning),
          ),
        const Text(
          'Prüfe die Bildhinweise am Foto. „Stimmt, weiter“ bestätigt nur den Text. Bildhinweise werden nicht zum Lernen verwendet.',
        ),
        ...entries,
      ],
    );
  }
}

typedef _Submit = Future<void> Function(
  String decision,
  Json observation,
  int version,
);

class _VisualItem extends StatefulWidget {
  const _VisualItem({
    super.key,
    required this.original,
    required this.review,
    required this.enabled,
    required this.submit,
  });
  final Json original;
  final Json? review;
  final bool enabled;
  final _Submit submit;
  @override
  State<_VisualItem> createState() => _VisualItemState();
}

class _VisualItemState extends State<_VisualItem> {
  late final TextEditingController description = TextEditingController(
    text:
        ((widget.review?['observation'] as Map?)?['description'] ??
                widget.original['description'])
            as String,
  );
  bool editing = false, busy = false;
  String? error;
  @override
  void didUpdateWidget(covariant _VisualItem oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!editing) {
      final reviewed = widget.review?['observation'];
      final shown = reviewed is Map ? reviewed : widget.original;
      description.text = shown['description'] as String;
    }
  }

  @override
  void dispose() {
    description.dispose();
    super.dispose();
  }

  Future<void> send(String decision) async {
    if (busy || !widget.enabled || description.text.trim().isEmpty) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final reviewed = widget.review?['observation'];
      final original = decision == 'confirmed'
          ? widget.original
          : (reviewed is Map ? reviewed : widget.original);
      await widget.submit(decision, {
        'description': decision == 'confirmed'
            ? original['description']
            : description.text.trim(),
        'image_region': original['image_region'],
        'uncertainty': original['uncertainty'] ?? '',
      }, widget.review?['review_version'] as int? ?? 0);
      if (mounted) setState(() => editing = false);
    } on ApiError catch (e) {
      if (mounted) {
        setState(
          () => error = e.status == 409
              ? 'Die Seite wurde geändert. Dein Text bleibt hier. Lade die Seite neu und prüfe ihn erneut.'
              : 'Das Speichern hat nicht geklappt. Versuche es erneut.',
        );
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final decision = widget.review?['decision'];
    final reviewed = widget.review?['observation'];
    final shown = reviewed is Map ? reviewed : widget.original;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          decision == 'confirmed' || decision == 'corrected'
              ? 'Geprüft · keine Lernquelle'
              : decision == 'uncertain'
              ? 'Noch unsicher'
              : 'Noch nicht geprüft',
          style: Theme.of(context).textTheme.labelMedium,
        ),
        if (editing)
          TextField(
            controller: description,
            enabled: !busy,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Was ist auf dem Bild?',
            ),
          )
        else
          Text((shown['description'] as String).trim()),
        if (shown['uncertainty'] is String &&
            (shown['uncertainty'] as String).trim().isNotEmpty)
          Text('Unsicher: ${(shown['uncertainty'] as String).trim()}'),
        if (error != null)
          Text(
            error!,
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        if (widget.enabled)
          Wrap(
            spacing: 8,
            children: [
              if (editing)
                TextButton(
                  onPressed: busy ? null : () => send('corrected'),
                  child: const Text('Korrektur speichern'),
                )
              else ...[
                TextButton(
                  onPressed: busy ? null : () => setState(() => editing = true),
                  child: const Text('Ändern'),
                ),
                TextButton(
                  onPressed: busy ? null : () => send('confirmed'),
                  child: const Text('Stimmt'),
                ),
                TextButton(
                  onPressed: busy ? null : () => send('uncertain'),
                  child: const Text('Unsicher'),
                ),
              ],
              if (editing)
                TextButton(
                  onPressed: busy
                      ? null
                      : () => setState(() {
                          description.text = (shown['description'] as String);
                          editing = false;
                          error = null;
                        }),
                  child: const Text('Abbrechen'),
                ),
            ],
          ),
      ],
    );
  }
}
