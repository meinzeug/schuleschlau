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
  const PublicImageCard({
    super.key,
    required this.state,
    required this.unit,
    required this.isCurrent,
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
  Object? error;
  Uint8List? image;
  bool busy = false;
  bool retryAllowed = false;
  bool? routeWasCurrent;
  int epoch = 0;
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
        (status == 'queued' || status == 'running')) {
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
      status = requestKey = null;
      image = null;
      error = null;
      retryAllowed = false;
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
    try {
      final value = await widget.state.api.get(url);
      if (!current ||
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
      setState(() {
        status = next;
        retryAllowed = next == 'failed' && value['retry_allowed'] == true;
        if (next != 'ready') image = null;
      });
      if (next == 'ready') {
        final bytes = await widget.state.api.bytes('$url/file');
        if (!current ||
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
      } else if (next == 'queued' || next == 'running') {
        timer = Timer(const Duration(seconds: 5), () {
          if (current) unawaited(load());
        });
      } else if (next == 'failed') {
        requestKey = null;
      }
    } catch (_) {
      if (current && serial == epoch) {
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
    final snapshot = widget.unit;
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
          path != url ||
          requestKey != key ||
          !identical(widget.unit, snapshot)) {
        return;
      }
      final next = value['status'];
      if (next is String) setState(() => status = next);
      await load();
    } catch (e) {
      if (current &&
          path == url &&
          requestKey == key &&
          identical(widget.unit, snapshot)) {
        setState(() => error = e);
      }
    } finally {
      if (mounted && path == url) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (status == null || status == 'unavailable') {
      return const SizedBox.shrink();
    }
    if (status == 'ready' && image != null) {
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
              'KI-Bild · fachlich noch nicht geprüft',
              style: TextStyle(color: context.palette.muted, fontSize: 12),
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
