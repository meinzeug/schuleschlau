import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// Existing family owners can explicitly apply; reads never create an application.
class ParentBetaApplication extends StatefulWidget {
  final AppState state;
  const ParentBetaApplication(this.state, {super.key});

  @override
  State<ParentBetaApplication> createState() => _ParentBetaApplicationState();
}

class _ParentBetaApplicationState extends State<ParentBetaApplication>
    with WidgetsBindingObserver {
  late final Object? owner = widget.state.user;
  late final String? family = widget.state.familyId;
  late final authentication = widget.state.api.requestIdentity();
  bool busy = false,
      loading = true,
      enabled = false,
      foreground = true,
      supported = true;
  int epoch = 0;
  String? status, error;

  bool get current =>
      mounted &&
      widget.state.isOwner &&
      family != null &&
      identical(owner, widget.state.user) &&
      widget.state.familyId == family &&
      widget.state.api.ownsRequest(authentication);
  bool get active =>
      current && foreground && ModalRoute.of(context)?.isCurrent != false;

  @override
  void initState() {
    super.initState();
    foreground =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
    widget.state.addListener(identityChanged);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (active) load();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState value) {
    foreground = value == AppLifecycleState.resumed;
    if (!foreground) {
      epoch++;
      if (mounted) {
        setState(() {
          status = null;
          loading = false;
          busy = false;
        });
      }
    } else {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (active) load();
      });
    }
  }

  void identityChanged() {
    if (current) return;
    epoch++;
    if (mounted) {
      setState(() {
        status = null;
        error = null;
        loading = false;
      });
    }
  }

  @override
  void dispose() {
    epoch++;
    widget.state.removeListener(identityChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> load() async {
    if (!active || busy) return;
    final request = ++epoch;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final catalog = await widget.state.api.get('/store/catalog');
      if (!active || request != epoch) return;
      final beta = catalog['beta'];
      if (beta is! Map || beta['enabled'] is! bool) {
        setState(() {
          supported = false;
          status = null;
        });
        return;
      }
      final value = (await widget.state.api.get(
        '/families/$family/beta-application',
      ))['status'];
      if (!active || request != epoch) return;
      if (!const {
        'none',
        'pending',
        'approved',
        'rejected',
        'revoked',
      }.contains(value)) {
        throw ApiError('Der Beta-Status ist unvollständig.');
      }
      setState(() {
        status = value as String;
        enabled = beta['enabled'] == true;
        supported = true;
      });
    } catch (failure) {
      if (active && request == epoch) {
        setState(
          () => error = failure is ApiError
              ? failure.message
              : 'Beta-Status konnte nicht geladen werden.',
        );
      }
    } finally {
      if (current && request == epoch) setState(() => loading = false);
    }
  }

  Future<void> apply() async {
    if (!active ||
        busy ||
        loading ||
        !enabled ||
        !const {'none', 'rejected', 'revoked'}.contains(status)) {
      return;
    }
    final request = epoch;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final result = await widget.state.api.post(
        '/families/$family/beta-application',
        {},
      );
      if (!active || request != epoch) return;
      if (!const {'pending', 'approved'}.contains(result['status'])) {
        throw ApiError(
          'Der aktuelle Beta-Status konnte nicht bestätigt werden.',
        );
      }
      setState(() => status = result['status'] as String);
    } catch (failure) {
      if (active && request == epoch) {
        setState(
          () => error = failure is ApiError
              ? failure.message
              : 'Ergebnis unklar. Bitte den Status aktualisieren.',
        );
      }
    } finally {
      if (current && request == epoch) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!current || (!loading && !supported)) return const SizedBox.shrink();
    final description = switch (status) {
      'pending' =>
        'Deine Anmeldung wird geprüft. Der Zugang beginnt nach der Freigabe.',
      'approved' => 'Deine Familie ist für die Beta freigegeben.',
      'rejected' => 'Deine vorige Beta-Anmeldung wurde abgelehnt.',
      'revoked' => 'Der vorige Beta-Zugang wurde beendet.',
      'none' => 'Du kannst deine Familie für die Beta anmelden.',
      _ => 'Der Beta-Status wird geladen.',
    };
    return Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'SchuleSchlau Beta',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(description),
          if (error != null) Notice(error!, warning: true),
          if (loading) const LinearProgressIndicator(),
          if (!loading &&
              status != null &&
              status != 'pending' &&
              status != 'approved') ...[
            const SizedBox(height: 8),
            if (enabled) ...[
              const Text(
                'Das Team prüft jede Anmeldung. Bei Freigabe werden KI-Nutzung und Kosten für die Auswertung erfasst.',
              ),
              TextButton.icon(
                onPressed: busy ? null : apply,
                icon: const Icon(Icons.send_outlined),
                label: const Text('Für die Beta anmelden'),
              ),
            ] else
              const Text('Neue Beta-Anmeldungen sind derzeit geschlossen.'),
          ],
          if (error != null || (!loading && status == null))
            TextButton.icon(
              onPressed: busy ? null : load,
              icon: const Icon(Icons.refresh),
              label: const Text('Status aktualisieren'),
            ),
        ],
      ),
    );
  }
}
