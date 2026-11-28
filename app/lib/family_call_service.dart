import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart' show AppLifecycleState;
import 'package:flutter_webrtc/flutter_webrtc.dart' show Helper;

import 'api.dart';
import 'family_call_media.dart';
import 'family_call_native.dart';

String familyCallKey() {
  final random = Random.secure();
  return List.generate(
    20,
    (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0'),
  ).join();
}

/// One session-bound call, independent of the currently open learning route.
/// Opening pages and receiving an invitation never opens a camera or microphone.
class FamilyCallService extends ChangeNotifier {
  final AppState state;
  final FamilyCallMedia Function() mediaFactory;
  final Duration pollInterval;
  final bool nativeEnabled;
  final Future<bool> Function() requestScreenPermission;
  final bool webPlatform;
  final Duration Function()? authorityClock;
  final Stopwatch _uptime = Stopwatch()..start();
  final Duration authorityLease;
  FamilyCallService(
    this.state, {
    FamilyCallMedia Function()? mediaFactory,
    this.pollInterval = const Duration(seconds: 2),
    this.nativeEnabled = true,
    this.webPlatform = kIsWeb,
    this.authorityClock,
    this.authorityLease = const Duration(seconds: 90),
    Future<bool> Function()? requestScreenPermission,
  }) : mediaFactory = mediaFactory ?? WebRtcFamilyCallMedia.new,
       requestScreenPermission =
           requestScreenPermission ?? (() => Helper.requestCapturePermission());

  Json? _owner;
  Json? call;
  FamilyCallMedia? media;
  String? error;
  bool busy = false;
  bool _polling = false;
  bool _foreground = true;
  bool _connecting = false;
  bool _ending = false;
  bool _connected = false;
  bool _offerPending = false;
  bool _screenPreparing = false;
  bool _renegotiatePending = false;
  int _generation = 0;
  int _cursor = 0;
  int _heartbeat = 0;
  int _networkFailures = 0;
  int _lastDiscovery = 0;
  Timer? _timer;
  Timer? _authorityWatchdog;
  int? _authorityDeadline;
  int get _authorityNow =>
      authorityClock?.call().inMilliseconds ?? _uptime.elapsedMilliseconds;
  StreamSubscription<FamilyCallIntent>? _nativeSubscription;
  String? _nativeShown;
  String? _mediaCallId;
  bool _nativeInitialized = false;
  bool _nativeInitializing = false;
  bool _nativeInitializationWanted = false;
  bool _watchingAuthentication = false;
  String? _startKey;
  void Function(String callId, String action)? onNativeIntent;
  Object? get accountIdentity => _owner;
  bool get isChild => _owner?['role'] == 'child';
  bool get isParent => _owner?['role'] == 'parent';
  bool get live => ['ringing', 'accepted'].contains(call?['status']);
  bool get incoming => live && isParent && call?['status'] == 'ringing';
  bool get joined => media != null;
  bool get accepted => call?['status'] == 'accepted';
  String? get callId => call?['id'] as String?;
  bool get _nativeAndroid =>
      nativeEnabled &&
      !webPlatform &&
      defaultTargetPlatform == TargetPlatform.android;
  bool _current(Json? owner, int generation) =>
      identical(state.user, owner) &&
      identical(_owner, owner) &&
      generation == _generation;

  void _renewAuthority(Json metadata) {
    if (!['ringing', 'accepted'].contains(metadata['status'])) return;
    final bound =
        metadata['valid_until'] ??
        (metadata['status'] == 'ringing' ? metadata['ring_expires'] : null);
    final serverNow = metadata['server_now'];
    final remaining = bound is num && serverNow is num
        ? ((bound - serverNow) * 1000).toInt().clamp(
            0,
            authorityLease.inMilliseconds,
          )
        : authorityLease.inMilliseconds;
    _authorityDeadline = _authorityNow + remaining;
    _authorityWatchdog ??= Timer.periodic(const Duration(seconds: 1), (_) {
      final deadline = _authorityDeadline;
      if (media != null && deadline != null && _authorityNow >= deadline) {
        error = 'Die sichere Anrufverbindung ist abgelaufen. Kamera, Mikrofon und Bildschirm sind aus. Prüfe die Verbindung und tritt bewusst erneut bei.';
        unawaited(_closeMedia());
        notifyListeners();
      }
    });
  }

  // A live call must not continue capturing while a different sign-in is
  // being initiated, even before the old account object is replaced.
  void _authenticationChanged() {
    if (state.authenticationPending) call = null;
    if (media != null || _nativeShown != null) unawaited(_closeMedia());
    notifyListeners();
  }

  void _watchAuthentication(bool watch) {
    if (watch == _watchingAuthentication) return;
    _watchingAuthentication = watch;
    if (watch) {
      state.authenticationChanges.addListener(_authenticationChanged);
    } else {
      state.authenticationChanges.removeListener(_authenticationChanged);
    }
  }

  void activate(Json? user) {
    final allowed = ['child', 'parent'].contains(user?['role']) ? user : null;
    if (identical(_owner, allowed)) {
      if (allowed != null &&
          _nativeAndroid &&
          !state.authenticationPending &&
          _nativeSubscription == null) {
        unawaited(_initializeNative());
      }
      return;
    }
    _generation++;
    _owner = allowed;
    _watchAuthentication(allowed != null);
    _timer?.cancel();
    _timer = null;
    _polling = false;
    call = null;
    error = null;
    _startKey = null;
    _lastDiscovery = 0;
    _networkFailures = 0;
    _cursor = 0;
    _connected = false;
    _connecting = false;
    busy = false;
    _ending = false;
    unawaited(_closeMedia());
    if (allowed != null) {
      if (_nativeAndroid && !state.authenticationPending) {
        unawaited(_initializeNative());
      }
      _timer = Timer.periodic(pollInterval, (_) => unawaited(refresh()));
      unawaited(refresh());
    }
  }

  Future<void> _initializeNative() async {
    if (_nativeInitializing) {
      _nativeInitializationWanted = true;
      return;
    }
    _nativeInitializing = true;
    final owner = _owner, generation = _generation;
    try {
      await FamilyCallNative.instance.initialize();
      _nativeInitialized = true;
      if (!_current(owner, generation) || state.authenticationPending) return;
      await _nativeSubscription?.cancel();
      _nativeSubscription = FamilyCallNative.instance.intents.listen((intent) {
        if (_current(owner, generation) && !state.authenticationPending) {
          onNativeIntent?.call(intent.callId, intent.action);
        }
      });
      final initial = await FamilyCallNative.instance.initialIntent();
      if (initial != null &&
          _current(owner, generation) &&
          !state.authenticationPending) {
        onNativeIntent?.call(initial.callId, initial.action);
      }
    } finally {
      _nativeInitializing = false;
      final wanted = _nativeInitializationWanted;
      _nativeInitializationWanted = false;
      if (wanted &&
          _owner != null &&
          !state.authenticationPending &&
          (!_current(owner, generation) || _nativeSubscription == null)) {
        unawaited(_initializeNative());
      }
    }
  }

  void lifecycle(AppLifecycleState phase) {
    foreground(phase == AppLifecycleState.resumed);
    // Browsers may suspend JavaScript timers in a hidden tab. Stop capture
    // before suspension; a transient permission picker (inactive) is safe.
    if (webPlatform &&
        [AppLifecycleState.hidden, AppLifecycleState.paused].contains(phase) &&
        (media != null || (isChild && live))) {
      unawaited(end());
    }
  }

  void foreground(bool value) {
    _foreground = value;
    if (value) {
      _lastDiscovery = 0;
      unawaited(refresh());
    }
  }

  Future<void> refresh({bool force = false}) async {
    final owner = _owner, generation = _generation;
    final family = state.familyId, identity = state.api.requestIdentity();
    bool valid() =>
        _current(owner, generation) &&
        !state.authenticationPending &&
        state.familyId == family &&
        state.api.ownsRequest(identity);
    if (owner == null ||
        !valid() ||
        _polling ||
        _ending ||
        (!_foreground && !live)) {
      return;
    }
    final now = DateTime.now().millisecondsSinceEpoch;
    if (!live && !force && now - _lastDiscovery < 10000) return;
    _polling = true;
    try {
      if (live) {
        final currentId = callId!;
        final response = await state.api.get('/family-calls/$currentId');
        if (!valid()) return;
        call = response;
        _renewAuthority(response);
      } else {
        _lastDiscovery = now;
        final response = await state.api.get('/family-calls/active');
        if (!valid()) return;
        final calls = response['calls'] as List? ?? [];
        if (calls.isNotEmpty) {
          call = Json.from(calls.first);
          _renewAuthority(call!);
        }
      }
      _networkFailures = 0;
      if (!live) {
        await _closeMedia();
      } else {
        if (incoming && _nativeAndroid && _nativeShown != callId) {
          final incomingId = callId!;
          _nativeShown = incomingId;
          await FamilyCallNative.instance.showIncoming(
            incomingId,
            DateTime.fromMillisecondsSinceEpoch(
              (call!['ring_expires'] as num).toInt() * 1000,
            ),
          );
          if (!valid()) {
            // A delayed platform completion may have shown the old notice
            // after cleanup. Do not cancel a newer notice for the same call.
            if (_current(owner, generation) && _nativeShown != incomingId) {
              await FamilyCallNative.instance.cancel(incomingId);
            }
            return;
          }
        }
        if (accepted && media != null) {
          await _connect(owner, generation);
          if (!valid()) return;
          await _receiveSignals(owner, generation);
          if (!valid()) return;
        }
        final now = DateTime.now().millisecondsSinceEpoch;
        if ((isChild || call?['is_participant'] == true) &&
            now - _heartbeat >= 15000) {
          _heartbeat = now;
          final response = await state.api.post(
            '/family-calls/$callId/heartbeat',
            {},
          );
          if (!valid()) return;
          call = response;
          _renewAuthority(response);
        }
      }
      if (valid()) notifyListeners();
    } on ApiError catch (e) {
      if (!valid()) return;
      _networkFailures++;
      if ([401, 403, 404, 409, 410].contains(e.status)) {
        await _closeMedia();
        if (!valid()) return;
        call = null;
        error = 'Dieser Anruf ist nicht mehr verfügbar.';
      } else if (_networkFailures >= 3) {
        error = 'Die Verbindung ist unterbrochen. Du kannst den Anruf beenden und eine Nachricht senden.';
      }
      notifyListeners();
    } catch (_) {
      if (valid()) {
        error = 'Die Verbindung konnte nicht hergestellt werden. Versuche es erneut oder sende eine Nachricht.';
        notifyListeners();
      }
    } finally {
      if (_current(owner, generation)) _polling = false;
    }
  }

  Future<void> open(String id, {bool Function()? isCurrent}) async {
    final owner = _owner, generation = _generation;
    final family = state.familyId, identity = state.api.requestIdentity();
    bool valid() =>
        _current(owner, generation) &&
        !state.authenticationPending &&
        state.familyId == family &&
        state.api.ownsRequest(identity) &&
        isCurrent?.call() != false;
    if (owner == null || !valid()) return;
    // Old notification links must not replace or close a newer live call.
    if (live && callId != id) {
      throw ApiError('Ein anderes Gespräch ist bereits geöffnet.');
    }
    final previousCall = callId;
    final response = await state.api.get('/family-calls/$id');
    if (!valid()) return;
    if (callId != previousCall && callId != id) return;
    if (live && callId != id) return;
    if (callId != id) {
      await _closeMedia();
      if (!valid()) return;
      if (callId != previousCall && callId != id) return;
      _cursor = 0;
      _connected = false;
      _connecting = false;
    }
    call = response;
    _renewAuthority(response);
    error = null;
    notifyListeners();
  }

  Future<FamilyCallMedia> _prepare(bool camera, bool Function() valid) async {
    final next = mediaFactory();
    media = next;
    next.addListener(_mediaChanged);
    try {
      await next.prepare(camera: camera);
      if (!valid() || media != next) {
        await next.close();
        throw ApiError('Der Zugang hat sich geändert.');
      }
      if (_authorityDeadline == null) _renewAuthority({'status': 'accepted'});
      return next;
    } catch (_) {
      if (media == next) media = null;
      next.removeListener(_mediaChanged);
      await next.close();
      rethrow;
    }
  }

  Future<String?> start({
    String contextKind = 'general',
    String? contextId,
    bool camera = true,
  }) async {
    if (state.authenticationPending || !isChild || busy || _ending) {
      return callId;
    }
    if (live) return callId;
    final owner = _owner, generation = _generation;
    final family = state.familyId, identity = state.api.requestIdentity();
    bool valid() =>
        _current(owner, generation) &&
        !state.authenticationPending &&
        state.familyId == family &&
        state.api.ownsRequest(identity);
    void invalidate() {
      if (!valid() && _current(owner, generation)) unawaited(_closeMedia());
    }

    state.authenticationChanges.addListener(invalidate);
    busy = true;
    error = null;
    notifyListeners();
    try {
      final config = await state.api.get('/family-calls/config');
      if (!valid()) return null;
      if (config['available'] != true) {
        throw ApiError(
          config['notice'] is String ? config['notice'] : 'Videoanrufe sind gerade nicht verfügbar. Du kannst eine Nachricht senden.',
        );
      }
      await _prepare(camera, valid);
      if (!valid()) return null;
      _startKey ??= familyCallKey();
      final response = await state.api.post('/family-calls', {
        'idempotency_key': _startKey,
        'context_kind': contextKind,
        'context_id': ?contextId,
      });
      if (!valid()) return null;
      call = response;
      _renewAuthority(response);
      _startKey = null;
      if (_nativeAndroid) {
        final startedCallId = callId!;
        _mediaCallId = startedCallId;
        await FamilyCallNative.instance.startMedia(
          startedCallId,
          camera: camera,
          microphone: true,
        );
        if (!valid()) {
          if (_current(owner, generation)) {
            await FamilyCallNative.instance.stopMedia(callId: startedCallId);
          }
          return null;
        }
      }
      notifyListeners();
      return callId;
    } catch (e) {
      if (valid()) {
        await _closeMedia();
        error = e is ApiError ? e.message : 'Kamera oder Mikrofon konnten nicht geöffnet werden. Erlaube den Zugriff oder sende eine Nachricht.';
        notifyListeners();
      }
      return null;
    } finally {
      state.authenticationChanges.removeListener(invalidate);
      if (_current(owner, generation)) {
        if (!valid()) await _closeMedia();
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> join({bool camera = true}) async {
    if (state.authenticationPending ||
        busy ||
        _ending ||
        !live ||
        media != null) {
      return;
    }
    final owner = _owner, generation = _generation;
    final family = state.familyId, identity = state.api.requestIdentity();
    bool valid() =>
        _current(owner, generation) &&
        !state.authenticationPending &&
        state.familyId == family &&
        state.api.ownsRequest(identity);
    void invalidate() {
      if (!valid() && _current(owner, generation)) unawaited(_closeMedia());
    }

    state.authenticationChanges.addListener(invalidate);
    final id = callId!;
    busy = true;
    error = null;
    notifyListeners();
    try {
      final resuming = accepted;
      if (resuming) {
        final current = await state.api.get('/family-calls/$id');
        if (!valid()) return;
        if (current['status'] != 'accepted' ||
            current['is_participant'] != true) {
          throw ApiError('Dieser Anruf ist nicht mehr für dich geöffnet.', 403);
        }
        call = current;
        _renewAuthority(current);
        final history = await state.api.get(
          '/family-calls/$id/signals?after=0',
        );
        if (!valid()) return;
        _cursor = (history['cursor'] as num?)?.toInt() ?? 0;
      }
      await _prepare(camera, valid);
      if (!valid()) return;
      if (incoming) {
        final response = await state.api.post('/family-calls/$id/accept', {});
        if (!valid()) return;
        call = response;
        _renewAuthority(response);
      }
      if (_nativeAndroid) {
        _mediaCallId = id;
        await FamilyCallNative.instance.cancel(id);
        if (!valid()) return;
        await FamilyCallNative.instance.startMedia(
          id,
          camera: camera,
          microphone: true,
        );
        if (!valid()) {
          if (_current(owner, generation)) {
            await FamilyCallNative.instance.stopMedia(callId: id);
          }
          return;
        }
      }
      await _connect(owner, generation);
      if (valid() && resuming && isParent) {
        await _sendSignal('renegotiate', {}, owner, generation);
      }
      if (valid()) notifyListeners();
    } catch (e) {
      if (valid()) {
        await _closeMedia();
        error = e is ApiError ? e.message : 'Kamera oder Mikrofon konnten nicht geöffnet werden. Prüfe die Freigabe und versuche es erneut.';
        notifyListeners();
      }
    } finally {
      state.authenticationChanges.removeListener(invalidate);
      if (_current(owner, generation)) {
        if (!valid()) await _closeMedia();
        busy = false;
        notifyListeners();
      }
    }
  }

  Future<void> _connect(Json? owner, int generation) async {
    if (state.authenticationPending ||
        _connecting ||
        _connected ||
        media == null ||
        !accepted) {
      return;
    }
    _connecting = true;
    final currentMedia = media!;
    final id = callId!;
    try {
      final response = await state.api.post('/family-calls/$id/ice', {});
      if (!_current(owner, generation) ||
          media != currentMedia ||
          callId != id) {
        return;
      }
      currentMedia.onIce = (candidate) {
        if (_current(owner, generation) &&
            callId == id &&
            media == currentMedia) {
          unawaited(_sendSignal('ice', candidate, owner, generation));
        }
      };
      currentMedia.onScreenStopped = () {
        if (_current(owner, generation) && callId == id) {
          unawaited(_restoreCaptureForeground(id).then((_) => _renegotiate()));
        }
      };
      await currentMedia.connect(response['ice_servers'] as List? ?? []);
      if (!_current(owner, generation) || media != currentMedia) return;
      _connected = true;
      if (isChild) await _publishOffer(currentMedia, owner, generation);
    } finally {
      if (_current(owner, generation)) _connecting = false;
    }
  }

  Future<bool> _sendSignal(
    String kind,
    Json payload,
    Json? owner,
    int generation,
  ) async {
    if (state.authenticationPending ||
        !_current(owner, generation) ||
        !accepted) {
      return false;
    }
    try {
      await state.api.post('/family-calls/$callId/signals', {
        'idempotency_key': familyCallKey(),
        'kind': kind,
        'payload': payload,
      });
      return _current(owner, generation) && accepted;
    } catch (_) {
      if (_current(owner, generation)) {
        error = 'Die Verbindung ist instabil. Falls Bild oder Ton fehlen, beende den Anruf und starte ihn erneut.';
        notifyListeners();
      }
      return false;
    }
  }

  Future<bool> _publishOffer(
    FamilyCallMedia currentMedia,
    Json? owner,
    int generation,
  ) async {
    var delivered = false;
    _offerPending = true;
    try {
      final offer = await currentMedia.offer();
      if (!_current(owner, generation) || media != currentMedia) return false;
      delivered = await _sendSignal('offer', offer, owner, generation);
      return delivered;
    } catch (_) {
      if (_current(owner, generation) && media == currentMedia) {
        error = 'Die Verbindung konnte nicht vorbereitet werden. Beende den Anruf und starte ihn bewusst erneut.';
        notifyListeners();
      }
      return false;
    } finally {
      if (!delivered && _current(owner, generation) && media == currentMedia) {
        _offerPending = false;
        _renegotiatePending = false;
        if (currentMedia.sharingScreen) {
          await currentMedia.stopScreen();
          final id = callId;
          if (id != null) await _restoreCaptureForeground(id);
          if (_current(owner, generation) && media == currentMedia) {
            error = 'Die Bildschirmfreigabe konnte nicht verbunden werden und ist gestoppt. Kamera und Gespräch bleiben verfügbar.';
            notifyListeners();
          }
        }
      }
    }
  }

  Future<void> _receiveSignals(Json? owner, int generation) async {
    if (!_connected || media == null) return;
    final currentMedia = media!;
    final response = await state.api.get(
      '/family-calls/$callId/signals?after=$_cursor',
    );
    if (!_current(owner, generation) || media != currentMedia) return;
    for (final raw in response['signals'] as List? ?? []) {
      final signal = Json.from(raw);
      final payload = Json.from(signal['payload']);
      if (!_current(owner, generation) || media != currentMedia) return;
      switch (signal['kind']) {
        case 'offer':
          if (isParent) {
            final answer = await currentMedia.answer(payload);
            await _sendSignal('answer', answer, owner, generation);
          }
        case 'answer':
          if (isChild) {
            await currentMedia.receiveAnswer(payload);
            _offerPending = false;
            if (_renegotiatePending) await _renegotiate();
          }
        case 'ice':
          await currentMedia.receiveIce(payload);
        case 'renegotiate':
          if (isChild) await _renegotiate();
      }
      _cursor = (signal['sequence'] as num).toInt();
    }
    _cursor = (response['cursor'] as num?)?.toInt() ?? _cursor;
  }

  void _mediaChanged() => notifyListeners();

  Future<void> toggleMicrophone() async {
    final owner = _owner, generation = _generation;
    final currentMedia = media;
    if (state.authenticationPending || currentMedia == null || !accepted) {
      return;
    }
    try {
      await currentMedia.toggleMicrophone();
      if (_current(owner, generation) && media == currentMedia) {
        error = null;
        notifyListeners();
      }
    } catch (_) {
      if (_current(owner, generation) && media == currentMedia) {
        error = 'Das Mikrofon konnte nicht eingeschaltet werden. Prüfe die Mikrofonfreigabe am Gerät.';
        notifyListeners();
      }
    }
  }

  Future<void> toggleCamera() async {
    final owner = _owner, generation = _generation;
    final currentMedia = media;
    if (state.authenticationPending || currentMedia == null || !accepted) {
      return;
    }
    try {
      final addedTrack = await currentMedia.toggleCamera();
      if (!_current(owner, generation) || media != currentMedia) return;
      if (_nativeAndroid) {
        await FamilyCallNative.instance.startMedia(
          callId!,
          camera: currentMedia.cameraEnabled,
          microphone: true,
        );
      }
      if (addedTrack) {
        if (isChild) {
          await _renegotiate();
        } else {
          await _sendSignal('renegotiate', {}, owner, generation);
        }
      }
      error = null;
      notifyListeners();
    } catch (_) {
      if (_current(owner, generation)) {
        error = 'Die Kamera konnte nicht eingeschaltet werden. Prüfe die Kamerafreigabe. Du kannst mit Ton weiterreden.';
        notifyListeners();
      }
    }
  }

  Future<void> _restoreCaptureForeground(String id) async {
    if (_nativeAndroid) {
      try {
        await FamilyCallNative.instance.stopProjection(id);
      } catch (_) {}
    }
  }

  Future<void> shareScreen() async {
    if (state.authenticationPending ||
        !isChild ||
        media == null ||
        !accepted ||
        !_connected ||
        media!.sharingScreen ||
        _screenPreparing) {
      return;
    }
    final owner = _owner, generation = _generation;
    final currentMedia = media!;
    final id = callId!;
    final family = state.familyId, identity = state.api.requestIdentity();
    bool valid() =>
        _current(owner, generation) &&
        !state.authenticationPending &&
        state.familyId == family &&
        state.api.ownsRequest(identity) &&
        media == currentMedia;
    void invalidate() {
      if (!valid() && _current(owner, generation) && media == currentMedia) {
        unawaited(_closeMedia());
      }
    }

    state.authenticationChanges.addListener(invalidate);
    _screenPreparing = true;
    error = null;
    try {
      if (_nativeAndroid) {
        if (!await requestScreenPermission()) return;
        if (!valid()) return;
        await FamilyCallNative.instance.startProjection(id);
        if (!valid()) {
          await _restoreCaptureForeground(id);
          return;
        }
      }
      await currentMedia.startScreen();
      if (!valid()) {
        await currentMedia.stopScreen();
        await _restoreCaptureForeground(id);
        return;
      }
      if (!currentMedia.sharingScreen || !await _renegotiate()) {
        throw StateError('Screen sender was not published.');
      }
    } catch (_) {
      // Only screen capture is rolled back. Existing camera and microphone
      // tracks remain available; no automatic capture or signaling retry.
      await currentMedia.stopScreen();
      await _restoreCaptureForeground(id);
      if (_current(owner, generation) && media == currentMedia) {
        error = 'Der Bildschirm wurde nicht geteilt. Die Freigabe ist gestoppt. Kamera und Gespräch bleiben verfügbar. Du kannst es bewusst erneut versuchen.';
        notifyListeners();
      }
    } finally {
      state.authenticationChanges.removeListener(invalidate);
      if (_current(owner, generation) && media == currentMedia) {
        _screenPreparing = false;
      }
    }
  }

  Future<bool> _renegotiate() async {
    final owner = _owner, generation = _generation;
    if (state.authenticationPending ||
        !isChild ||
        media == null ||
        !accepted ||
        !_connected) {
      return false;
    }
    if (_offerPending) {
      _renegotiatePending = true;
      return true;
    }
    _renegotiatePending = false;
    return _publishOffer(media!, owner, generation);
  }

  Future<void> stopScreen() async {
    final currentMedia = media;
    final id = callId;
    await currentMedia?.stopScreen();
    if (id != null) await _restoreCaptureForeground(id);
    await _renegotiate();
  }

  Future<void> end({bool decline = false}) async {
    final owner = _owner, generation = _generation;
    final id = callId;
    if (_ending) return;
    _ending = true;
    if (call != null) {
      call = {...call!, 'status': decline ? 'declined' : 'ended'};
    }
    // Stop tracks immediately even if the server cannot be reached.
    await _closeMedia();
    if (id == null ||
        state.authenticationPending ||
        !_current(owner, generation)) {
      if (_current(owner, generation)) _ending = false;
      return;
    }
    try {
      final response = await state.api.post(
        '/family-calls/$id/${decline ? 'decline' : 'end'}',
        {},
      );
      if (!_current(owner, generation)) return;
      call = response;
      error = null;
    } catch (_) {
      if (_current(owner, generation)) {
        call = {...?call, 'status': 'ended'};
        error = 'Kamera, Mikrofon und Bildschirm sind aus. Der Anruf läuft auf dem Server automatisch ab.';
      }
    }
    if (_current(owner, generation)) {
      _ending = false;
      notifyListeners();
    }
  }

  Future<void> _closeMedia() async {
    final previous = media;
    final previousNativeCall = _mediaCallId;
    final previousShown = _nativeShown;
    media = null;
    _mediaCallId = null;
    _nativeShown = null;
    _authorityWatchdog?.cancel();
    _authorityWatchdog = null;
    _authorityDeadline = null;
    _connected = false;
    _connecting = false;
    _cursor = 0;
    _offerPending = false;
    _renegotiatePending = false;
    _screenPreparing = false;
    if (previous != null) previous.removeListener(_mediaChanged);
    final closing = previous?.close();
    try {
      if (_nativeAndroid) {
        if (previousShown != null) {
          await FamilyCallNative.instance.cancel(previousShown);
        }
        if (previousNativeCall != null) {
          await FamilyCallNative.instance.stopMedia(callId: previousNativeCall);
        }
      }
    } catch (_) {
      // Track and peer shutdown has already started independently. Notification
      // cleanup must not block a revoked session or affect a newer call.
    }
    try {
      await closing;
    } catch (_) {
      // Every track and the peer were asked to stop before renderer disposal.
    }
  }

  Future<void> clear() async {
    _generation++;
    _owner = null;
    _watchAuthentication(false);
    _timer?.cancel();
    _timer = null;
    await _nativeSubscription?.cancel();
    _nativeSubscription = null;
    await _closeMedia();
    if (_nativeAndroid && _nativeInitialized) {
      await FamilyCallNative.instance.clear();
    }
    call = null;
    error = null;
    busy = false;
    _polling = false;
    _ending = false;
    _startKey = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _watchAuthentication(false);
    _timer?.cancel();
    unawaited(_nativeSubscription?.cancel());
    unawaited(_closeMedia());
    super.dispose();
  }
}
