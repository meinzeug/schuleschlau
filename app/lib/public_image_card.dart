import 'dart:async';
import 'dart:math';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// A shared public illustration, separate from source-bound explanations.
/// Looking at a round only performs reads; image creation is an explicit action.
class PublicImageCard extends StatefulWidget {
  final AppState state;
  final Json unit;
  final bool Function() isCurrent;

  /// While answering, the task needs the available vertical space. The
  /// illustration remains available to open without starting any work.
  final bool compact;
  const PublicImageCard({
    super.key,
    required this.state,
    required this.unit,
    required this.isCurrent,
    this.compact = false,
  });

  @override
  State<PublicImageCard> createState() => _PublicImageCardState();
}

class _PublicImageCardState extends State<PublicImageCard>
    with WidgetsBindingObserver {
  late final Json? owner = widget.state.user;
  late final String? ownerToken = widget.state.api.token,
      ownerFamily = widget.state.familyId;
  String? status, requestKey;
  String? reviewRequestKey;
  String? reviewStatus;
  Object? error;
  Object? reviewError;
  Uint8List? image;
  bool busy = false;
  bool retryAllowed = false;
  bool reviewAllowed = false, reviewBusy = false;
  bool reviewReferenceAvailable = false;
  bool expanded = false;
  bool? routeWasCurrent;
  int epoch = 0, actionEpoch = 0;
  Timer? timer;

  bool get current =>
      mounted &&
      widget.isCurrent() &&
      identical(widget.state.user, owner) &&
      widget.state.api.token == ownerToken &&
      widget.state.familyId == ownerFamily &&
      (WidgetsBinding.instance.lifecycleState == null ||
          WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed);
  String? get path =>
      widget.unit['id'] is String &&
          widget.unit['explanation_visual_status'] is String
      ? '/units/${Uri.encodeComponent(widget.unit['id'] as String)}/public-image'
      : null;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) unawaited(load());
    });
  }

  @override
  void dispose() {
    epoch++;
    actionEpoch++;
    timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    timer?.cancel();
    if (state == AppLifecycleState.resumed && current) unawaited(load());
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final routeCurrent = ModalRoute.of(context)?.isCurrent != false;
    if (!routeCurrent) {
      timer?.cancel();
    } else if (routeWasCurrent == false &&
        (status == 'queued' ||
            status == 'running' ||
            reviewStatus == 'pending')) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (current) unawaited(load());
      });
    }
    routeWasCurrent = routeCurrent;
  }

  @override
  void didUpdateWidget(covariant PublicImageCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(oldWidget.unit, widget.unit)) {
      epoch++;
      timer?.cancel();
      final changedUnit = widget.unit['id'] != oldWidget.unit['id'];
      status = null;
      if (changedUnit) {
        actionEpoch++;
        requestKey = null;
        reviewRequestKey = null;
        busy = false;
        reviewBusy = false;
        expanded = false;
      }
      reviewStatus = null;
      image = null;
      error = null;
      reviewError = null;
      retryAllowed = false;
      reviewAllowed = false;
      reviewReferenceAvailable = false;
      unawaited(load());
    }
  }

  Future<void> load() async {
    timer?.cancel();
    final url = path;
    final snapshot = widget.unit;
    if (!current || url == null || ModalRoute.of(context)?.isCurrent == false) {
      return;
    }
    final serial = ++epoch;
    final identity = widget.state.api.requestIdentity();
    try {
      final value = await widget.state.api.get(url);
      if (!current ||
          !widget.state.api.ownsRequest(identity) ||
          serial != epoch ||
          path != url ||
          !identical(widget.unit, snapshot)) {
        return;
      }
      final next = value['status'];
      if (next is! String ||
          !{
            'missing',
            'queued',
            'running',
            'ready',
            'failed',
            'unavailable',
          }.contains(next)) {
        return;
      }
      final proposedReview = value['review_status'];
      final nextReview =
          proposedReview is String &&
              {
                'pending',
                'approved',
                'rejected',
                'uncertain',
                'unavailable',
              }.contains(proposedReview)
          ? proposedReview
          : null;
      // A contradictory response must never leave a rejected image visible.
      // A new generation remains a separate, explicitly confirmed action.
      final rejectedRetry =
          nextReview == 'rejected' &&
          next == 'missing' &&
          value['retry_allowed'] == true;
      final effectiveStatus = nextReview == 'rejected'
          ? (rejectedRetry ? 'missing' : 'unavailable')
          : next;
      if (!reviewBusy &&
          ({'approved', 'rejected'}.contains(nextReview) ||
              (reviewStatus == 'pending' &&
                  {'uncertain', 'unavailable'}.contains(nextReview)))) {
        reviewRequestKey = null;
      }
      setState(() {
        status = effectiveStatus;
        reviewStatus = nextReview;
        reviewReferenceAvailable = value['review_reference_available'] == true;
        reviewAllowed =
            value['review_request_allowed'] == true &&
            {'uncertain', 'unavailable'}.contains(nextReview);
        retryAllowed =
            rejectedRetry ||
            (effectiveStatus == 'failed' && value['retry_allowed'] == true);
        if (effectiveStatus != 'ready') image = null;
      });
      if (effectiveStatus == 'ready') {
        if (image == null) {
          final bytes = await widget.state.api.bytes('$url/file');
          if (!current ||
              !widget.state.api.ownsRequest(identity) ||
              serial != epoch ||
              path != url ||
              !identical(widget.unit, snapshot)) {
            return;
          }
          if (bytes.isEmpty || bytes.length > 6 * 1024 * 1024) {
            throw ApiError('Das Bild konnte nicht geladen werden.');
          }
          setState(() {
            image = bytes;
            error = null;
          });
        }
        if (nextReview == 'pending') {
          timer = Timer(const Duration(seconds: 5), () {
            if (current && widget.state.api.ownsRequest(identity)) {
              unawaited(load());
            }
          });
        }
      } else if (effectiveStatus == 'queued' || effectiveStatus == 'running') {
        timer = Timer(const Duration(seconds: 5), () {
          if (current && widget.state.api.ownsRequest(identity)) {
            unawaited(load());
          }
        });
      } else if (effectiveStatus == 'failed' && !busy) {
        requestKey = null;
      }
    } catch (_) {
      if (current &&
          widget.state.api.ownsRequest(identity) &&
          serial == epoch) {
        // Older servers do not provide the optional endpoint.
        setState(() {
          status ??= 'unavailable';
          if (status == 'ready') {
            error = ApiError('Das Bild konnte nicht geladen werden.');
          }
        });
      }
    }
  }

  Future<void> prepare() async {
    final url = path;
    final serial = actionEpoch;
    final identity = widget.state.api.requestIdentity();
    if (busy ||
        !current ||
        url == null ||
        ModalRoute.of(context)?.isCurrent == false) {
      return;
    }
    requestKey ??=
        'picture-${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 30)}';
    final key = requestKey!;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final value = await widget.state.api.post(url, null, {
        'Idempotency-Key': key,
      });
      if (!current ||
          !widget.state.api.ownsRequest(identity) ||
          path != url ||
          requestKey != key ||
          serial != actionEpoch) {
        return;
      }
      final next = value['status'];
      if (next is String) setState(() => status = next);
      await load();
      if (current &&
          widget.state.api.ownsRequest(identity) &&
          path == url &&
          serial == actionEpoch &&
          status == 'failed') {
        requestKey = null;
      }
    } catch (e) {
      if (current &&
          widget.state.api.ownsRequest(identity) &&
          path == url &&
          requestKey == key &&
          serial == actionEpoch) {
        setState(() => error = e);
      }
    } finally {
      if (mounted && path == url && serial == actionEpoch) {
        setState(() => busy = false);
      }
    }
  }

  Future<void> requestReview() async {
    final url = path;
    final serial = actionEpoch;
    final identity = widget.state.api.requestIdentity();
    if (reviewBusy ||
        !reviewAllowed ||
        !current ||
        url == null ||
        ModalRoute.of(context)?.isCurrent == false) {
      return;
    }
    setState(() {
      reviewBusy = true;
      reviewError = null;
    });
    reviewRequestKey ??=
        'review-${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 30)}';
    final key = reviewRequestKey!;
    try {
      final result = await widget.state.api.post('$url/review', null, {
        'Idempotency-Key': key,
      });
      if (current &&
          widget.state.api.ownsRequest(identity) &&
          path == url &&
          reviewRequestKey == key &&
          serial == actionEpoch) {
        if ({
          'approved',
          'rejected',
          'uncertain',
          'unavailable',
        }.contains(result['review_status'])) {
          reviewRequestKey = null;
        }
        await load();
        if (current &&
            widget.state.api.ownsRequest(identity) &&
            path == url &&
            serial == actionEpoch &&
            {
              'approved',
              'rejected',
              'uncertain',
              'unavailable',
            }.contains(reviewStatus)) {
          reviewRequestKey = null;
        }
      }
    } catch (e) {
      if (current &&
          widget.state.api.ownsRequest(identity) &&
          path == url &&
          reviewRequestKey == key &&
          serial == actionEpoch) {
        setState(
          () => reviewError = e is ApiError
              ? e.message
              : 'Die KI-Prüfung konnte nicht gestartet werden.',
        );
      }
    } finally {
      if (mounted && path == url && serial == actionEpoch) {
        setState(() => reviewBusy = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (reviewStatus == 'rejected') {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Das Bild hat die KI-Prüfung nicht bestanden. Du kannst weiterlernen.',
            ),
            if (status == 'missing' &&
                retryAllowed &&
                widget.unit['synthetic'] != true)
              TextButton.icon(
                onPressed: busy || !current ? null : prepare,
                icon: const Icon(Icons.image_outlined),
                label: Text(busy ? 'Wird angefragt …' : 'Neues Bild erstellen'),
              ),
            if (error != null) Notice(error.toString(), warning: true),
          ],
        ),
      );
    }
    if (status == null || status == 'unavailable') {
      return const SizedBox.shrink();
    }
    if (status == 'ready' && image != null) {
      final reviewLabel = switch (reviewStatus) {
        'approved' =>
          reviewReferenceAvailable
              ? 'Von KI eingeschätzt · nicht fachlich garantiert'
              : 'Von KI eingeschätzt · ohne Sachquelle, Fehler möglich',
        'pending' => 'KI prüft das Bild … · fachlich ungeprüft',
        'uncertain' => 'KI-Prüfung unklar · fachlich ungeprüft',
        'unavailable' => 'KI-Prüfung nicht verfügbar · fachlich ungeprüft',
        _ =>
          widget.compact && !expanded
              ? 'KI-Bild · fachlich ungeprüft'
              : 'KI-Bild · fachlich noch nicht geprüft',
      };
      if (widget.compact && !expanded) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Align(
            alignment: Alignment.centerLeft,
            child: TextButton(
              onPressed: current ? () => setState(() => expanded = true) : null,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Image.memory(
                      image!,
                      width: 44,
                      height: 44,
                      fit: BoxFit.cover,
                      excludeFromSemantics: true,
                      errorBuilder: (_, _, _) =>
                          const Icon(Icons.image_outlined),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Flexible(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('Bild ansehen'),
                        Text(reviewLabel, style: const TextStyle(fontSize: 12)),
                      ],
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Icon(Icons.expand_more_rounded),
                ],
              ),
            ),
          ),
        );
      }
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.memory(
                image!,
                height: 180,
                fit: BoxFit.contain,
                semanticLabel: 'Allgemeines KI-Bild zum Thema',
                errorBuilder: (_, _, _) =>
                    const Text('Das Bild konnte nicht angezeigt werden.'),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              reviewLabel,
              style: TextStyle(color: context.palette.muted, fontSize: 12),
            ),
            if (reviewAllowed)
              TextButton.icon(
                onPressed: reviewBusy || !current ? null : requestReview,
                icon: const Icon(Icons.fact_check_outlined),
                label: Text(
                  reviewBusy ? 'Wird angefragt …' : 'KI-Bildprüfung starten',
                ),
              ),
            if (reviewError != null)
              Notice(reviewError.toString(), warning: true),
            if (widget.compact)
              TextButton.icon(
                onPressed: current
                    ? () => setState(() => expanded = false)
                    : null,
                icon: const Icon(Icons.expand_less_rounded),
                label: const Text('Bild schließen'),
              ),
          ],
        ),
      );
    }
    final pending = status == 'queued' || status == 'running';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (pending)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text('Dein Themenbild entsteht …'),
          ),
        if (status == 'failed' && !retryAllowed)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'Das Bild ist gerade nicht verfügbar. Du kannst weiterlernen.',
            ),
          ),
        if (status == 'ready' && image == null && error != null)
          TextButton.icon(
            onPressed: current ? load : null,
            icon: const Icon(Icons.refresh_rounded),
            label: const Text('Bild erneut laden'),
          ),
        if (!pending &&
            status != 'ready' &&
            (status != 'failed' || retryAllowed) &&
            widget.unit['synthetic'] != true)
          TextButton.icon(
            onPressed: busy || !current ? null : prepare,
            icon: const Icon(Icons.image_outlined),
            label: Text(
              busy
                  ? 'Wird angefragt …'
                  : status == 'failed'
                  ? 'Bild erneut versuchen'
                  : 'Bild zum Thema erstellen',
            ),
          ),
        if (error != null) Notice(error.toString(), warning: true),
      ],
    );
  }
}
