import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';

import 'api.dart';
import 'learning_explanation.dart';

// A unit has one server-side position per user, even when multiple explanation
// widgets for that unit are mounted in the same app. Serialize those writes
// locally; server revisions still reject changes made by another device.
final _visualWrites = Expando<Map<String, _VisualWriteGate>>();

class _VisualWriteGate {
  final Json? owner;
  final String? token, family;
  Future<void> tail = Future.value();
  String? signature;
  int revision = 0, generation = 0;
  int listeners = 0, writes = 0;

  _VisualWriteGate(this.owner, this.token, this.family);
}

void _releaseGate(AppState state, String unit, _VisualWriteGate gate) {
  final units = _visualWrites[state];
  if (gate.listeners == 0 &&
      gate.writes == 0 &&
      identical(units?[unit], gate)) {
    units?.remove(unit);
  }
}

_VisualWriteGate _writeGate(
  AppState state,
  String unit,
  Json? owner,
  String? token,
  String? family,
) {
  final units = _visualWrites[state] ??= <String, _VisualWriteGate>{};
  final previous = units[unit];
  if (previous != null &&
      identical(previous.owner, owner) &&
      previous.token == token &&
      previous.family == family) {
    return previous;
  }
  return units[unit] = _VisualWriteGate(owner, token, family);
}

/// Restores one private technical reading position. Only explicit local changes
/// save it; loading, replaying an API response and parent reading create no activity.
class SavedVisualExplanation extends StatefulWidget {
  final AppState state;
  final String unitId, text;
  final String? questionId, prompt;
  final List<Json> steps;
  final Object sourceKey;
  final bool Function()? isCurrent;
  final int initialStep;
  final ValueChanged<int>? onStepChanged;
  const SavedVisualExplanation({
    super.key,
    required this.state,
    required this.unitId,
    required this.text,
    required this.steps,
    required this.sourceKey,
    this.questionId,
    this.prompt,
    this.isCurrent,
    this.initialStep = 0,
    this.onStepChanged,
  });
  @override
  State<SavedVisualExplanation> createState() => _SavedVisualExplanationState();
}

class _SavedVisualExplanationState extends State<SavedVisualExplanation>
    with WidgetsBindingObserver {
  Json? owner, restored, pending;
  String? token, family, signature;
  int revision = 0, epoch = 0;
  bool foreground = true,
      ready = false,
      writing = false,
      conflict = false,
      touched = false,
      resync = false;
  ModalRoute<dynamic>? route;
  late _VisualWriteGate gate;
  bool get current =>
      mounted &&
      foreground &&
      identical(widget.state.user, owner) &&
      widget.state.api.token == token &&
      widget.state.familyId == family &&
      (widget.isCurrent?.call() ?? true);
  @override
  void initState() {
    super.initState();
    owner = widget.state.user;
    token = widget.state.api.token;
    family = widget.state.familyId;
    gate = _writeGate(widget.state, widget.unitId, owner, token, family);
    gate.listeners++;
    foreground =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
    widget.state.addListener(identityChanged);
    restore();
  }

  void identityChanged() {
    if (!current) {
      epoch++;
      pending = null;
    }
    if (!identical(widget.state.user, owner) ||
        widget.state.api.token != token ||
        widget.state.familyId != family) {
      final units = _visualWrites[widget.state];
      if (identical(units?[widget.unitId], gate)) units?.remove(widget.unitId);
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    route = ModalRoute.of(context);
    if (route?.isCurrent != false && pending != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (current) flush();
      });
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState value) {
    foreground = value == AppLifecycleState.resumed;
    if (!foreground) {
      epoch++;
      pending = null;
      resync = resync || ready || writing;
      ready = false;
    } else if (!ready) {
      restore();
    }
  }

  @override
  void didUpdateWidget(covariant SavedVisualExplanation oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sourceKey != widget.sourceKey ||
        oldWidget.unitId != widget.unitId ||
        oldWidget.questionId != widget.questionId) {
      epoch++;
      restored = pending = null;
      signature = null;
      revision = 0;
      ready = touched = conflict = resync = false;
      final oldGate = gate;
      gate = _writeGate(widget.state, widget.unitId, owner, token, family);
      if (!identical(oldGate, gate)) {
        oldGate.listeners--;
        _releaseGate(oldWidget.state, oldWidget.unitId, oldGate);
        gate.listeners++;
      }
      restore();
    }
  }

  Future<void> restore() async {
    if (widget.steps.isEmpty) return;
    final request = epoch;
    try {
      final currentGate = gate;
      await currentGate.tail;
      if (!current || request != epoch || !identical(currentGate, gate)) return;
      final readGeneration = currentGate.generation;
      final previousSignature = signature;
      final previousRevision =
          currentGate.signature == signature && currentGate.revision > revision
          ? currentGate.revision
          : revision;
      final value = await widget.state.api.call(
        'GET',
        '/units/${widget.unitId}/visual-position',
        null,
        {'X-Schulpilot-Account': owner?['id']?.toString() ?? ''},
      );
      if (!current || request != epoch) return;
      // Another local widget may have written while this GET was in flight.
      // Read again after its queued writes instead of treating our own update
      // as a different device or restoring an outdated position.
      if (currentGate.writes != 0 || currentGate.generation != readGeneration) {
        await restore();
        return;
      }
      final incomingSignature = value['source_signature'] as String?;
      final incomingRevision = value['revision'] as int? ?? 0;
      final changedElsewhere =
          resync &&
          previousSignature != null &&
          (previousSignature != incomingSignature ||
              previousRevision != incomingRevision);
      signature = incomingSignature;
      revision = incomingRevision;
      if (currentGate.generation == readGeneration) {
        currentGate.signature = signature;
        currentGate.revision = revision;
      }
      final position = value['position'];
      setState(() {
        resync = false;
        if (changedElsewhere) {
          conflict = true;
          pending = null;
        }
        ready = signature != null;
        if (!touched &&
            position is Map &&
            position['question_id'] == widget.questionId &&
            position['explanation_kind'] ==
                (widget.questionId == null ? 'intro' : 'question')) {
          restored = Json.from(position);
        }
      });
      if (pending != null) await flush();
    } catch (_) {
      /* Reading remains available while the position is offline. */
    }
  }

  void change(Json value) {
    if (!current) return;
    touched = true;
    pending = Json.from(jsonDecode(jsonEncode(value)));
    flush();
  }

  Future<void> flush() async {
    if (!current ||
        route?.isCurrent == false ||
        !ready ||
        writing ||
        conflict ||
        pending == null) {
      return;
    }
    final request = epoch, value = pending!;
    final currentGate = gate;
    final requestSignature = signature;
    final requestUnit = widget.unitId;
    final requestState = widget.state;
    final previous = currentGate.tail;
    final finished = Completer<void>();
    currentGate.tail = finished.future;
    currentGate.writes++;
    pending = null;
    writing = true;
    try {
      await previous;
      if (!current || request != epoch || !identical(currentGate, gate)) return;
      final sentRevision =
          currentGate.signature == requestSignature &&
              currentGate.revision > revision
          ? currentGate.revision
          : revision;
      final result = await widget.state.api.call(
        'PUT',
        '/units/${widget.unitId}/visual-position',
        {
          'source_signature': requestSignature,
          'revision': sentRevision,
          'position': value,
        },
        {'X-Schulpilot-Account': owner?['id']?.toString() ?? ''},
      );
      final nextRevision = result['revision'] as int? ?? sentRevision;
      if (identical(widget.state.user, owner) &&
          widget.state.api.token == token &&
          widget.state.familyId == family) {
        currentGate.signature = requestSignature;
        currentGate.revision = nextRevision;
        currentGate.generation++;
      }
      if (!current || request != epoch) return;
      revision = nextRevision;
    } catch (error) {
      if (current &&
          request == epoch &&
          error is ApiError &&
          error.status == 409) {
        setState(() => conflict = true);
        pending = null;
      }
    } finally {
      finished.complete();
      currentGate.writes--;
      _releaseGate(requestState, requestUnit, currentGate);
      writing = false;
      if (current && pending != null) flush();
    }
  }

  @override
  void dispose() {
    epoch++;
    gate.listeners--;
    _releaseGate(widget.state, widget.unitId, gate);
    widget.state.removeListener(identityChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      LearningExplanation(
        text: widget.text,
        steps: widget.steps,
        unitId: widget.unitId,
        questionId: widget.questionId,
        prompt: widget.prompt,
        state: widget.state,
        sourceKey: widget.sourceKey,
        isCurrent: widget.isCurrent,
        initialStep: widget.initialStep,
        onStepChanged: widget.onStepChanged,
        initialPosition: restored,
        onPositionChanged: change,
      ),
      if (conflict)
        const Text(
          'Deine Leseposition hat sich inzwischen geändert. Deine Antworten bleiben erhalten.',
        ),
    ],
  );
}
