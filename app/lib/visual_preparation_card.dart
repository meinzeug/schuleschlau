import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import 'api.dart';
import 'subject_graphic.dart';
import 'ui.dart';

/// A deliberate normal reserved job. Viewing this card only reads saved state.
class VisualPreparationCard extends StatefulWidget {
  final AppState state;
  final Json unit;
  final bool Function() isCurrent;
  final Future<void> Function() refresh;
  const VisualPreparationCard({
    super.key,
    required this.state,
    required this.unit,
    required this.isCurrent,
    required this.refresh,
  });
  @override
  State<VisualPreparationCard> createState() => _VisualPreparationCardState();
}

class _VisualPreparationCardState extends State<VisualPreparationCard>
    with WidgetsBindingObserver {
  bool busy = false, dispatched = false;
  Object? error;
  String? requestKey;
  String? acceptedJobId;
  Json? publicVisual;
  Timer? publicTimer;
  int publicEpoch = 0, missingChecks = 0;
  int prepareEpoch = 0;
  (Object?, Object?, Object?, Object?) get publicContext => (
    widget.unit['id'],
    widget.unit['subject'],
    widget.unit['topic'],
    widget.unit['explanation_visual_status'],
  );
  late final Json? owner = widget.state.user;
  late final String? ownerToken = widget.state.api.token,
      ownerFamily = widget.state.familyId;
  bool get current =>
      mounted &&
      widget.isCurrent() &&
      identical(widget.state.user, owner) &&
      widget.state.api.token == ownerToken &&
      widget.state.familyId == ownerFamily &&
      (WidgetsBinding.instance.lifecycleState == null ||
          WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(loadPublicVisual());
    });
  }

  @override
  void dispose() {
    publicEpoch++;
    prepareEpoch++;
    publicTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    publicTimer?.cancel();
    if (state == AppLifecycleState.resumed && current) {
      unawaited(loadPublicVisual());
    }
  }

  Future<void> loadPublicVisual() async {
    publicTimer?.cancel();
    if (!current || ModalRoute.of(context)?.isCurrent == false) return;
    final id = widget.unit['id'];
    if (id is! String ||
        widget.unit['explanation_visual_status'] is! String ||
        widget.unit['explanation_visual_status'] == 'ready') {
      return;
    }
    final epoch = ++publicEpoch;
    final identity = widget.state.api.requestIdentity();
    final contextAtRequest = publicContext;
    try {
      final value = await widget.state.api.get('/units/$id/public-visual');
      if (!current ||
          !widget.state.api.ownsRequest(identity) ||
          epoch != publicEpoch ||
          publicContext != contextAtRequest) {
        return;
      }
      setState(() => publicVisual = value);
      final status = value['status'];
      if (status == 'missing') missingChecks++;
      if (status == 'queued' ||
          status == 'claimed' ||
          (status == 'missing' && missingChecks < 4)) {
        publicTimer = Timer(const Duration(seconds: 5), () {
          if (widget.state.api.ownsRequest(identity)) {
            unawaited(loadPublicVisual());
          }
        });
      }
    } catch (_) {
      // The optional public example never blocks the saved unit.
    }
  }

  @override
  void didUpdateWidget(covariant VisualPreparationCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    final changedUnit = widget.unit['id'] != oldWidget.unit['id'];
    if (changedUnit ||
        widget.unit['subject'] != oldWidget.unit['subject'] ||
        widget.unit['topic'] != oldWidget.unit['topic'] ||
        widget.unit['explanation_visual_status'] !=
            oldWidget.unit['explanation_visual_status']) {
      publicEpoch++;
      publicTimer?.cancel();
      publicVisual = null;
      missingChecks = 0;
      unawaited(loadPublicVisual());
    }
    if (changedUnit) {
      prepareEpoch++;
      busy = false;
      dispatched = false;
      error = null;
      requestKey = null;
      acceptedJobId = null;
    }
    if (widget.unit['visual_preparation'] is Map &&
        ![
          'queued',
          'running',
        ].contains(widget.unit['visual_preparation']['status'])) {
      dispatched = false;
    }
    if (widget.unit['visual_preparation'] is Map &&
        widget.unit['visual_preparation']['status'] == 'failed' &&
        !busy &&
        acceptedJobId != null &&
        widget.unit['visual_preparation']['id'] == acceptedJobId &&
        (oldWidget.unit['visual_preparation'] is! Map ||
            oldWidget.unit['visual_preparation']['status'] != 'failed')) {
      requestKey = null;
      acceptedJobId = null;
    }
  }

  Future<void> prepare() async {
    if (busy || !current || ModalRoute.of(context)?.isCurrent == false) return;
    final owner = widget.state.user,
        token = widget.state.api.token,
        family = widget.state.familyId;
    final identity = widget.state.api.requestIdentity();
    final unitId = widget.unit['id'];
    if (unitId is! String || unitId.isEmpty) return;
    final serial = ++prepareEpoch;
    bool requestCurrent() =>
        current &&
        widget.state.api.ownsRequest(identity) &&
        widget.unit['id'] == unitId &&
        serial == prepareEpoch &&
        identical(widget.state.user, owner) &&
        widget.state.api.token == token &&
        widget.state.familyId == family;
    setState(() {
      busy = true;
      error = null;
    });
    requestKey ??=
        'visual-${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 30)}';
    try {
      final job = await widget.state.api.post(
        '/units/${Uri.encodeComponent(unitId)}/visual-explanation',
        null,
        {'Idempotency-Key': requestKey!},
      );
      if (requestCurrent()) {
        acceptedJobId = job['id'] is String ? job['id'] as String : null;
        setState(
          () => dispatched = ['queued', 'running'].contains(job['status']),
        );
      }
      if (requestCurrent()) await widget.refresh();
      // An explicit response for this same key proves that its job has
      // finished; a lost response does not authorize a fresh request key.
      if (requestCurrent() &&
          (job['status'] == 'failed' ||
              (acceptedJobId != null &&
                  widget.unit['visual_preparation'] is Map &&
                  widget.unit['visual_preparation']['id'] == acceptedJobId &&
                  widget.unit['visual_preparation']['status'] == 'failed'))) {
        requestKey = null;
        acceptedJobId = null;
      }
    } catch (e) {
      if (requestCurrent()) setState(() => error = e);
    } finally {
      if (mounted && serial == prepareEpoch) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final renderedUnit = widget.unit;
    final status = widget.unit['explanation_visual_status'];
    if (status == null || status == 'ready') return const SizedBox.shrink();
    final job = widget.unit['visual_preparation'];
    final pending =
        dispatched ||
        job is Map && ['queued', 'running'].contains(job['status']);
    final failed = job is Map && job['status'] == 'failed';
    final unavailable = widget.unit['visual_prepare_unavailable'] == true;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (pending || status == 'legacy_text' || unavailable)
            Text(
              pending
                  ? 'Grafische Erklärung wird vorbereitet …'
                  : unavailable &&
                        widget.unit['visual_prepare_reason'] ==
                            'attempts_exhausted'
                  ? 'Die Grafik ist gerade nicht verfügbar. Du kannst weiterlernen.'
                  : unavailable
                  ? 'Dazu gibt es gerade keine passende Grafik. Du kannst weiterlernen.'
                  : 'Zu deiner Erklärung fehlt noch eine Grafik.',
              key: const ValueKey('visual-readiness'),
              style: TextStyle(color: context.palette.muted, fontSize: 14),
            ),
          if (!pending &&
              widget.unit['synthetic'] != true &&
              widget.unit['can_prepare_visual'] != false)
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: busy || !current
                    ? null
                    : () {
                        if (identical(widget.unit, renderedUnit)) prepare();
                      },
                icon: const Icon(Icons.auto_awesome_outlined),
                label: Text(
                  busy
                      ? 'Wird angefragt …'
                      : failed
                      ? 'Grafische Erklärung erneut anfragen'
                      : 'Grafische Erklärung vorbereiten',
                ),
              ),
            ),
          if (pending)
            const Text(
              'Deine gespeicherten Aufgaben und Antworten bleiben erhalten.',
            ),
          if (publicVisual?['status'] == 'queued' ||
              publicVisual?['status'] == 'claimed')
            const Text('Ein allgemeines KI-Beispiel entsteht …'),
          if (publicVisual?['status'] == 'ready' &&
              publicVisual?['asset'] is Map)
            ExpansionTile(
              title: const Text('Allgemeines KI-Beispiel ansehen'),
              subtitle: const Text('Noch nicht fachlich geprüft'),
              children: [
                Text(publicVisual!['asset']['title'].toString()),
                const SizedBox(height: 8),
                SubjectPresentation(
                  Json.from(publicVisual!['asset']['presentation']),
                  state: widget.state,
                ),
                Text(publicVisual!['asset']['text'].toString()),
                const Text(
                  'Allgemeines Beispiel, nicht deine Heftseite. KI kann Fehler machen.',
                ),
              ],
            ),
          if (error != null) Notice(error.toString(), warning: true),
        ],
      ),
    );
  }
}
