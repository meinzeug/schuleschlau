import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

/// Family chooser only: reading this page never plans or starts child work.
class ExamLandingScreen extends StatelessWidget {
  final AppState state;
  const ExamLandingScreen(this.state, {super.key});

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: state,
    builder: (context, _) {
      final account = state.user;
      final familyId = state.familyId;
      final token = state.api.token;
      bool current((Object?, String?, int?) identity) =>
          context.mounted &&
          identical(account, state.user) &&
          familyId == state.familyId &&
          token == state.api.token &&
          state.api.ownsRequest(identity) &&
          ModalRoute.of(context)?.isCurrent != false;
      return PageFrame(
        state: state,
        title: 'Klassenarbeiten',
        child: !state.isParent || familyId == null
            ? const Notice('Wähle zuerst deinen Familienzugang aus.')
            : LoadView<(Json, (Object?, String?, int?))>(
                key: ValueKey((ObjectKey(account), familyId, token)),
                load: () async {
                  final identity = state.api.requestIdentity();
                  try {
                    final family = await state.api.get('/families/$familyId');
                    if (!current(identity)) {
                      throw ApiError('Bitte lade die Familienauswahl erneut.');
                    }
                    return (family, identity);
                  } catch (_) {
                    if (!current(identity)) {
                      throw ApiError('Bitte lade die Familienauswahl erneut.');
                    }
                    rethrow;
                  }
                },
                builder: (result, _) => Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text('Gemeinsam vorbereiten und nacharbeiten.'),
                    const SizedBox(height: 16),
                    for (final child in result.$1['children'] as List? ?? [])
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Panel(
                          child: ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              Icons.assignment_turned_in_outlined,
                              color: context.palette.cyanInk,
                            ),
                            title: Text(
                              '${child['display_name'] ?? 'Kinderzugang'}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            subtitle: const Text(
                              'Lerntermine · geschriebene Arbeiten',
                            ),
                            trailing: const Icon(Icons.chevron_right_rounded),
                            onTap: () {
                              if (current(result.$2)) {
                                openRoute(context, '/exams/${child['id']}');
                              }
                            },
                          ),
                        ),
                      ),
                    if ((result.$1['children'] as List? ?? []).isEmpty)
                      const Notice(
                        'Lege zuerst einen Kinderzugang in deiner Familie an.',
                      ),
                  ],
                ),
              ),
      );
    },
  );
}
