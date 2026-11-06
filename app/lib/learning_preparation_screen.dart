import 'dart:async';

import 'package:flutter/material.dart';

import 'api.dart';
import 'study_path_panel.dart' show isTechnicalPreparationFailure;
import 'ui.dart';

/// Observes a single already reserved job. Opening/reloading never creates one.
class LearningPreparationScreen extends StatelessWidget {
  final AppState state;
  final String childId;
  final String jobId;
  const LearningPreparationScreen(
    this.state, {
    super.key,
    required this.childId,
    required this.jobId,
  });

  @override
  Widget build(BuildContext context) => _LearningPreparationBody(
    state,
    childId: childId,
    jobId: jobId,
    key: ValueKey((
      state,
      ObjectKey(state.user),
      state.familyId,
      childId,
      jobId,
    )),
  );
}

class _LearningPreparationBody extends StatefulWidget {
  final AppState state;
  final String childId, jobId;
  const _LearningPreparationBody(
    this.state, {
    super.key,
    required this.childId,
    required this.jobId,
  });
  @override
  State<_LearningPreparationBody> createState() =>
      _LearningPreparationScreenState();
}

class _LearningPreparationScreenState extends State<_LearningPreparationBody>
    with WidgetsBindingObserver {
  Json? job;
  Timer? poll;
  Object? error;
  Object? startError;
  bool startTargetUnavailable = false;
  String? readingJob;
  bool refreshAfterRead = false;
  late final Json? owner;
  late final String? family, session;
  bool foreground = true;
  bool get sameOwner =>
      mounted &&
      owner != null &&
      identical(widget.state.user, owner) &&
      widget.state.familyId == family &&
      widget.state.api.token == session;
  bool get waiting =>
      job == null || ['queued', 'running'].contains(job?['status']);
  bool get recoverableReadError =>
      error == null ||
      (error is ApiError &&
          ((error as ApiError).status == 0 ||
              (error as ApiError).status >= 500));

  @override
  void initState() {
    super.initState();
    owner = widget.state.user;
    family = widget.state.familyId;
    session = widget.state.api.token;
    foreground =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
    widget.state.addListener(accountChanged);
    load();
    poll = Timer.periodic(Duration(seconds: 3), (_) {
      if (foreground &&
          sameOwner &&
          waiting &&
          error == null &&
          (ModalRoute.of(context)?.isCurrent ?? true)) {
        load();
      }
    });
  }

  void accountChanged() {
    if (!sameOwner) {
      poll?.cancel();
      if (mounted) {
        setState(() {
          job = null;
          error = null;
          startError = null;
          startTargetUnavailable = false;
        });
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState lifecycle) {
    foreground = lifecycle == AppLifecycleState.resumed;
    if (foreground &&
        sameOwner &&
        waiting &&
        recoverableReadError &&
        (ModalRoute.of(context)?.isCurrent ?? true)) {
      if (readingJob != null) {
        refreshAfterRead = true;
      } else {
        unawaited(load());
      }
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    widget.state.removeListener(accountChanged);
    poll?.cancel();
    super.dispose();
  }

  Future<void> load() async {
    final id = widget.jobId;
    if (readingJob == id || !sameOwner) return;
    final requestIdentity = widget.state.api.requestIdentity();
    bool currentRequest() =>
        sameOwner && widget.state.api.ownsRequest(requestIdentity);
    readingJob = id;
    try {
      var result = await widget.state.api.get('/jobs/$id');
      final recovery = result['recovery_job_id'];
      if (result['kind'] == 'unit' &&
          result['status'] == 'failed' &&
          recovery is String &&
          recovery != id &&
          RegExp(r'^[a-f0-9]{32}$').hasMatch(recovery) &&
          currentRequest()) {
        result = await widget.state.api.get('/jobs/$recovery');
      }
      if (![
        'unit',
        'study_block',
        'controller_check',
        'decision',
      ].contains(result['kind'])) {
        throw ApiError('Diese Vorbereitung gehört zu einem anderen Schritt.');
      }
      if (mounted && currentRequest() && id == widget.jobId) {
        setState(() {
          job = result;
          error = null;
          startTargetUnavailable = false;
        });
      }
    } catch (e) {
      if (mounted && currentRequest() && id == widget.jobId) {
        setState(() => error = e);
      }
    } finally {
      if (readingJob == id) readingJob = null;
      if (sameOwner && !widget.state.api.ownsRequest(requestIdentity)) {
        setState(() {
          job = null;
          error = ApiError(
            'Der Stand hat sich möglicherweise geändert. Bitte lade ihn erneut.',
            409,
          );
        });
      }
      if (refreshAfterRead) {
        refreshAfterRead = false;
        if (mounted &&
            foreground &&
            sameOwner &&
            waiting &&
            recoverableReadError &&
            (ModalRoute.of(context)?.isCurrent ?? true)) {
          unawaited(load());
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!sameOwner) return SizedBox.shrink();
    final ready =
        job?['status'] == 'completed' && job?['result']?['unit_id'] is String;
    final failed = job != null && !waiting && !ready;
    final planning = job?['kind'] == 'decision';
    final failure = error ?? job?['error'];
    final missingJob =
        widget.state.isChild &&
        error is ApiError &&
        (error as ApiError).status == 404;
    final technicalFailure =
        (failed || error != null) &&
        widget.state.isChild &&
        isTechnicalPreparationFailure(
          failure,
          code: error == null ? (job?['error_code'] as String?) : null,
        );
    return PageFrame(
      state: widget.state,
      title: planning ? 'Dein nächster Lernschritt' : 'Deine Lernrunde',
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: 660),
          child: Panel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(
                  ready
                      ? Icons.auto_stories_rounded
                      : failed || error != null
                      ? Icons.cloud_off_rounded
                      : Icons.auto_awesome_rounded,
                  color: context.palette.teal,
                  size: 32,
                ),
                SizedBox(height: 16),
                Text(
                  ready
                      ? planning
                            ? 'Dein Lernplan ist bereit.'
                            : 'Deine Runde ist bereit.'
                      : failed
                      ? planning
                            ? 'Dein Lernplan konnte nicht vorbereitet werden.'
                            : 'Diese Runde konnte nicht vorbereitet werden.'
                      : error != null
                      ? startTargetUnavailable
                            ? 'Diese Runde ist nicht mehr verfügbar.'
                            : missingJob
                            ? 'Vorbereitung nicht gefunden.'
                            : 'Wir können gerade nicht nachsehen.'
                      : job?['status'] == 'queued'
                      ? widget.state.isChild
                            ? 'Deine Runde wartet.'
                            : 'Deine Vorbereitung wartet auf ihren Start.'
                      : planning
                      ? 'Dein Lernplan entsteht …'
                      : 'Deine Runde entsteht …',
                  style: TextStyle(fontWeight: FontWeight.w800, fontSize: 22),
                ),
                SizedBox(height: 14),
                if (waiting && error == null) ...[
                  Semantics(
                    liveRegion: true,
                    label: job?['status'] == 'queued'
                        ? 'Vorbereitung wartet'
                        : 'Vorbereitung läuft',
                    child: LinearProgressIndicator(),
                  ),
                  SizedBox(height: 16),
                  Text(
                    widget.state.isChild
                        ? 'Die Vorbereitung geht auch ohne offene App weiter.'
                        : 'Du kannst die App schließen. Wir arbeiten weiter.',
                  ),
                ],
                if (failed || error != null) ...[
                  Text(
                    technicalFailure
                        ? failed
                              ? 'Deine Hefte und gespeicherten Runden bleiben erhalten.'
                              : 'Wir können den Stand gerade nicht laden. Deine Heftseiten und gespeicherten Runden bleiben erhalten.'
                        : error is ApiError
                        ? (error as ApiError).message
                        : job?['error'] as String? ??
                              'Deine Heftseiten bleiben gespeichert.',
                  ),
                  SizedBox(height: 12),
                ],
                if (ready && startError != null) ...[
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      startError is ApiError &&
                              (startError as ApiError).status == 409
                          ? (startError as ApiError).message
                          : 'Das Öffnen hat nicht geklappt. Versuche es noch einmal.',
                    ),
                  ),
                  SizedBox(height: 12),
                ],
                SizedBox(height: 16),
                if (ready)
                  ActionButton(
                    label: widget.state.isChild
                        ? 'Los geht’s'
                        : 'Übungen ansehen',
                    icon: widget.state.isChild
                        ? Icons.play_arrow_rounded
                        : Icons.visibility_outlined,
                    onPressed: () async {
                      if (!sameOwner) return;
                      final route = ModalRoute.of(context);
                      if (route?.isCurrent == false) return;
                      final requestIdentity = widget.state.api
                          .requestIdentity();
                      bool currentRequest() =>
                          sameOwner &&
                          widget.state.api.ownsRequest(requestIdentity);
                      final requestJob = widget.jobId;
                      final id = job!['result']['unit_id'];
                      if (widget.state.isChild) {
                        setState(() => startError = null);
                        try {
                          await widget.state.api.post('/units/$id/start');
                        } catch (e) {
                          if (context.mounted &&
                              currentRequest() &&
                              (route?.isCurrent ?? true) &&
                              widget.jobId == requestJob) {
                            setState(() {
                              if (e is ApiError &&
                                  (e.status == 403 || e.status == 404)) {
                                job = null;
                                error = e;
                                startTargetUnavailable = true;
                              } else {
                                startError = e;
                              }
                            });
                          }
                          return;
                        }
                      }
                      if (context.mounted &&
                          currentRequest() &&
                          (route?.isCurrent ?? true) &&
                          widget.jobId == requestJob) {
                        openRoute(context, '/unit/$id');
                      }
                    },
                  )
                else if (missingJob)
                  ActionButton(
                    label: 'Gespeicherte Runden ansehen',
                    icon: Icons.auto_stories_outlined,
                    onPressed: () async {
                      if (sameOwner) {
                        openRoute(context, '/learn/${widget.childId}');
                      }
                    },
                  )
                else if (error != null)
                  ActionButton(
                    label: 'Status neu laden',
                    icon: Icons.refresh_rounded,
                    onPressed: load,
                  ),
                if ((failed || error != null) &&
                    widget.state.isChild &&
                    !missingJob) ...[
                  SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () {
                      if (sameOwner) {
                        openRoute(context, '/learn/${widget.childId}');
                      }
                    },
                    icon: Icon(Icons.auto_stories_outlined),
                    label: Text('Gespeicherte Runden ansehen'),
                  ),
                ],
                SizedBox(height: 12),
                TextButton.icon(
                  onPressed: () {
                    if (!sameOwner) return;
                    openRoute(
                      context,
                      widget.state.isParent
                          ? '/parent-plan/${widget.childId}'
                          : '/app',
                    );
                  },
                  icon: Icon(Icons.home_outlined),
                  label: Text(
                    widget.state.isParent ? 'Zum Lernplan' : 'Zur Startseite',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
