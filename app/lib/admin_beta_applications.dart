import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// Only application/account metadata is shown. A decision always uses the
/// server revision; an uncertain response is never automatically repeated.
class AdminBetaApplications extends StatefulWidget {
  final AppState state;
  const AdminBetaApplications(this.state, {super.key});

  @override
  State<AdminBetaApplications> createState() => _AdminBetaApplicationsState();
}

class _AdminBetaApplicationsState extends State<AdminBetaApplications>
    with WidgetsBindingObserver {
  late final Object? owner = widget.state.user;
  late final String? ownerId = widget.state.user?['id']?.toString();
  late final String? token = widget.state.api.token;
  late final String? family = widget.state.familyId;
  late final authentication = widget.state.api.requestIdentity();
  bool expanded = false, loading = false, acting = false, foreground = true;
  int epoch = 0;
  int page = 1;
  bool hasMore = false;
  String status = 'pending';
  String? error, notice;
  List<Json>? items;
  DialogRoute<bool>? ownedDialog;

  String usageSummary(Object? value) {
    if (value is! Map ||
        value['calls'] is! num ||
        value['known_usd_micros'] is! num ||
        value['unknown_calls'] is! num) {
      return 'Nutzung nicht verfügbar';
    }
    final usd = ((value['known_usd_micros'] as num) / 1000000).toStringAsFixed(
      6,
    );
    final buffer = StringBuffer(
      '${value['calls']} KI-Aufrufe · $usd USD bekannte Kosten · ${value['unknown_calls']} noch unbekannt',
    );
    if (value['input_tokens'] is num && value['output_tokens'] is num) {
      buffer.write(
        '\n${value['input_tokens']} Eingabe- und ${value['output_tokens']} Ausgabetoken',
      );
    }
    final models = value['by_model'];
    if (models is Map && models.isNotEmpty) {
      for (final entry in models.entries.take(10)) {
        final detail = entry.value;
        if (entry.key is! String ||
            detail is! Map ||
            detail['calls'] is! num ||
            detail['known_usd_micros'] is! num ||
            detail['unknown_calls'] is! num) {
          continue;
        }
        final name = entry.key as String;
        final shown = name.length <= 100 ? name : '${name.substring(0, 100)}…';
        final modelCost = ((detail['known_usd_micros'] as num) / 1000000)
            .toStringAsFixed(6);
        buffer.write(
          '\n$shown: ${detail['calls']} Aufrufe, $modelCost USD bekannt, ${detail['unknown_calls']} unbekannt',
        );
      }
    }
    if ((models is Map && models.length > 10) ||
        value['models_truncated'] == true) {
      buffer.write('\nWeitere Modelle sind in den Gesamtkosten enthalten.');
    }
    return buffer.toString();
  }

  bool get current =>
      mounted &&
      widget.state.isAdmin &&
      ownerId != null &&
      identical(owner, widget.state.user) &&
      ownerId == widget.state.user?['id'] &&
      widget.state.api.ownsRequest(authentication) &&
      token == widget.state.api.token &&
      family == widget.state.familyId;

  bool get active =>
      current &&
      foreground &&
      expanded &&
      ModalRoute.of(context)?.isCurrent != false;

  @override
  void initState() {
    super.initState();
    foreground =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    WidgetsBinding.instance.addObserver(this);
    widget.state.addListener(accountChanged);
  }

  void accountChanged() {
    if (current) return;
    epoch++;
    dismissDialog();
    if (mounted) {
      setState(() {
        items = null;
        error = null;
        notice = null;
      });
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    foreground = state == AppLifecycleState.resumed;
    if (!foreground) {
      epoch++;
      dismissDialog();
      if (mounted) {
        setState(() {
          items = null;
          loading = false;
          acting = false;
        });
      }
    } else if (expanded && current) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (active) load();
      });
    }
  }

  @override
  void dispose() {
    epoch++;
    dismissDialog();
    widget.state.removeListener(accountChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void dismissDialog() {
    final dialog = ownedDialog;
    ownedDialog = null;
    if (dialog?.isActive == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (dialog!.isActive) dialog.navigator?.removeRoute(dialog);
      });
      WidgetsBinding.instance.ensureVisualUpdate();
    }
  }

  Future<bool> confirmDecision(
    String title,
    String text,
    String action, {
    required bool destructive,
  }) async {
    late final DialogRoute<bool> dialog;
    dialog = DialogRoute<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        scrollable: true,
        title: Text(title),
        content: Text(text),
        actions: [
          TextButton(
            autofocus: destructive,
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Abbrechen'),
          ),
          FilledButton(
            style: destructive
                ? FilledButton.styleFrom(
                    backgroundColor: context.palette.dangerInk,
                    foregroundColor: context.palette.dangerSurface,
                  )
                : null,
            onPressed: () {
              if (current && foreground && identical(ownedDialog, dialog)) {
                Navigator.pop(dialogContext, true);
              }
            },
            child: Text(action),
          ),
        ],
      ),
    );
    ownedDialog = dialog;
    try {
      final result = await Navigator.of(
        context,
        rootNavigator: true,
      ).push(dialog);
      await dialog.completed;
      return result == true && current && foreground;
    } finally {
      if (identical(ownedDialog, dialog)) ownedDialog = null;
    }
  }

  Future<void> load() async {
    if (!active || acting) return;
    final request = ++epoch;
    final requestedStatus = status;
    final requestedPage = page;
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final response = await widget.state.api.call(
        'GET',
        '/admin/beta-applications?status=$requestedStatus&page=$requestedPage',
        null,
        {'X-Schulpilot-Account': ownerId!},
      );
      if (!active ||
          request != epoch ||
          status != requestedStatus ||
          page != requestedPage) {
        return;
      }
      if (response['items'] is! List ||
          response['page'] != requestedPage ||
          response['has_more'] is! bool) {
        throw ApiError('Die Beta-Liste ist unvollständig.');
      }
      final raw = response['items'] as List;
      if (raw.any(
        (item) =>
            item is! Map ||
            item['id'] is! String ||
            !RegExp(r'^[a-f0-9]{32}$').hasMatch(item['id'] as String) ||
            item['revision'] is! int ||
            (item['revision'] as int) < 1 ||
            !const {
              'pending',
              'approved',
              'rejected',
              'revoked',
            }.contains(item['status']) ||
            item['email_verified'] is! bool,
      )) {
        throw ApiError('Die Beta-Liste ist unvollständig.');
      }
      setState(() {
        items = raw.map((item) => Json.from(item as Map)).toList();
        hasMore = response['has_more'] as bool;
      });
    } catch (failure) {
      if (active && request == epoch) {
        setState(
          () => error = failure is ApiError
              ? failure.message
              : 'Beta-Anmeldungen konnten nicht geladen werden.',
        );
      }
    } finally {
      if (current && request == epoch) setState(() => loading = false);
    }
  }

  Future<void> decide(Json item, String decision) async {
    if (!active || acting || loading) return;
    final request = epoch;
    final id = item['id'];
    final revision = item['revision'];
    final label = item['display_name'] is String
        ? item['display_name'] as String
        : 'dieses Elternkonto';
    final approved = decision == 'approve';
    final confirmed = await confirmDecision(
      approved
          ? 'Beta-Zugang freigeben?'
          : decision == 'reject'
          ? 'Beta-Anmeldung ablehnen?'
          : 'Beta-Zugang widerrufen?',
      approved
          ? '$label erhält nach Freigabe Beta-Zugang ohne persönliche KI-Mengen- und Kostengrenzen. Die tatsächliche Nutzung und Kosten werden weiterhin erfasst.'
          : decision == 'reject'
          ? 'Die Beta-Anmeldung von $label wird abgelehnt. Bestehende Kontodaten bleiben erhalten.'
          : 'Der Beta-Zugang von $label wird beendet. Bereits erfasste Kosten und Daten bleiben erhalten.',
      approved
          ? 'Freigeben'
          : decision == 'reject'
          ? 'Ablehnen'
          : 'Widerrufen',
      destructive: !approved,
    );
    if (!confirmed ||
        !active ||
        request != epoch ||
        acting ||
        id is! String ||
        revision is! int) {
      return;
    }
    setState(() {
      acting = true;
      error = null;
      notice = null;
    });
    String? failureMessage;
    try {
      await widget.state.api.call(
        'POST',
        '/admin/beta-applications/$id/decision',
        {'revision': revision, 'decision': decision},
        {'X-Schulpilot-Account': ownerId!},
      );
      if (!active || request != epoch) return;
      setState(
        () => notice = approved
            ? 'Beta-Zugang freigegeben.'
            : decision == 'reject'
            ? 'Anmeldung abgelehnt.'
            : 'Beta-Zugang widerrufen.',
      );
    } catch (failure) {
      if (active && request == epoch) {
        failureMessage = failure is ApiError
            ? failure.message
            : 'Ergebnis unklar. Bitte den aktuellen Stand neu laden.';
      }
    } finally {
      if (current && request == epoch) {
        setState(() => acting = false);
        if (active) await load();
        if (active && failureMessage != null) {
          setState(() => error = failureMessage);
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!current) return const SizedBox.shrink();
    return ExpansionTile(
      key: const ValueKey('admin-beta-applications'),
      title: const Text('Beta-Anmeldungen'),
      subtitle: const Text('Anmeldungen prüfen und Zugänge verwalten'),
      onExpansionChanged: (open) {
        setState(() {
          expanded = open;
          error = null;
          notice = null;
        });
        if (open) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (active) load();
          });
        } else {
          epoch++;
          items = null;
          loading = false;
          acting = false;
        }
      },
      children: [
        Wrap(
          spacing: 8,
          children: [
            for (final option in const [
              ('pending', 'Offen'),
              ('approved', 'Freigegeben'),
              ('rejected', 'Abgelehnt'),
              ('revoked', 'Widerrufen'),
            ])
              ChoiceChip(
                label: Text(option.$2),
                selected: status == option.$1,
                onSelected: acting
                    ? null
                    : (_) {
                        setState(() {
                          status = option.$1;
                          page = 1;
                          items = null;
                        });
                        load();
                      },
              ),
          ],
        ),
        if (notice != null) Notice(notice!, icon: Icons.check_circle_outline),
        if (error != null) Notice(error!, warning: true),
        if (loading)
          const Padding(
            padding: EdgeInsets.all(16),
            child: CircularProgressIndicator(),
          )
        else if (items != null && items!.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Keine Anmeldungen in dieser Liste.'),
          )
        else if (items != null)
          for (final item in items!)
            ListTile(
              title: Text(item['display_name']?.toString() ?? 'Elternkonto'),
              subtitle: Text(
                '${item['email'] ?? ''}\n${item['family_name'] ?? ''} · ${item['email_verified'] == true ? 'E-Mail bestätigt' : 'E-Mail noch nicht bestätigt'}\n${usageSummary(item['usage'])}',
              ),
              isThreeLine: true,
              trailing: Wrap(
                spacing: 4,
                children: [
                  if (item['status'] == 'pending') ...[
                    IconButton(
                      tooltip: 'Freigeben',
                      onPressed: acting || item['email_verified'] != true
                          ? null
                          : () => decide(item, 'approve'),
                      icon: const Icon(Icons.check_circle_outline),
                    ),
                    IconButton(
                      tooltip: 'Ablehnen',
                      onPressed: acting ? null : () => decide(item, 'reject'),
                      icon: const Icon(Icons.cancel_outlined),
                    ),
                  ],
                  if (item['status'] == 'approved')
                    IconButton(
                      tooltip: 'Widerrufen',
                      onPressed: acting ? null : () => decide(item, 'revoke'),
                      icon: const Icon(Icons.block),
                    ),
                ],
              ),
            ),
        if (items != null)
          Wrap(
            alignment: WrapAlignment.center,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              IconButton(
                tooltip: 'Vorherige Seite',
                onPressed: page > 1 && !loading && !acting
                    ? () {
                        setState(() {
                          page--;
                          items = null;
                        });
                        load();
                      }
                    : null,
                icon: const Icon(Icons.chevron_left),
              ),
              Text('Seite $page'),
              IconButton(
                tooltip: 'Nächste Seite',
                onPressed: hasMore && !loading && !acting
                    ? () {
                        setState(() {
                          page++;
                          items = null;
                        });
                        load();
                      }
                    : null,
                icon: const Icon(Icons.chevron_right),
              ),
            ],
          ),
        TextButton.icon(
          onPressed: loading || acting ? null : load,
          icon: const Icon(Icons.refresh),
          label: const Text('Aktualisieren'),
        ),
      ],
    );
  }
}
