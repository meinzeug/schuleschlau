import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/knowledge_sheet.dart';

import 'child_local_tools_ux88_test.dart' as f;
import 'knowledge_sheet_test.dart' as fixtures;

void main() {
  testWidgets(
    'new authentication closes private learning details and old refresh cannot run',
    (tester) async {
      final requests = <http.Request>[];
      final state = await fixtures.open(tester, (request) async {
        requests.add(request);
        return f.reply(fixtures.knowledge());
      });
      expect(find.text('Brüche addieren'), findsOneWidget);
      final refresh = tester
          .widget<TextButton>(
            find.widgetWithText(
              TextButton,
              'Gespeicherten Stand aktualisieren',
            ),
          )
          .onPressed!;
      final search = tester
          .widget<TextField>(find.byType(TextField))
          .onChanged!;
      final filter = tester
          .widget<DropdownButtonFormField<String>>(
            find.byType(DropdownButtonFormField<String>),
          )
          .onChanged!;
      final intent = state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(find.text('Vorwissen & Lernziele'), findsNothing);
      expect(find.text('Brüche addieren'), findsNothing);
      refresh();
      search('old');
      filter('initial_evidence');
      state.cancelAuthentication(intent);
      refresh();
      search('old');
      filter('initial_evidence');
      await tester.pumpAndSettle();
      expect(requests, hasLength(1));
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );

  for (final status in [200, 503]) {
    testWidgets('late learning knowledge $status is discarded after sign-in', (
      tester,
    ) async {
      final delayed = Completer<http.Response>();
      final requests = <http.Request>[];
      final state = f.account((r) {
        requests.add(r);
        return delayed.future;
      });
      await f.show(
        tester,
        Builder(
          builder: (ctx) => TextButton(
            onPressed: () => showKnowledgeSheet(ctx, state, unitId: 'unit'),
            child: const Text('Lernziele öffnen'),
          ),
        ),
      );
      await tester.tap(find.text('Lernziele öffnen'));
      await tester.pump();
      expect(requests, hasLength(1));
      final intent = state.beginAuthentication();
      delayed.complete(
        status == 200
            ? f.reply(fixtures.knowledge())
            : http.Response('{"detail":"Synthetischer Fehler"}', 503),
      );
      await tester.pumpAndSettle();
      expect(find.text('Vorwissen & Lernziele'), findsNothing);
      expect(find.text('Brüche addieren'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      expect(requests, hasLength(1));
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    });
  }

  testWidgets(
    'opening while authentication is pending does not read or show knowledge',
    (tester) async {
      final requests = <http.Request>[];
      final state = f.account((r) async {
        requests.add(r);
        return f.reply(fixtures.knowledge());
      });
      await f.show(
        tester,
        Builder(
          builder: (ctx) => TextButton(
            onPressed: () => showKnowledgeSheet(ctx, state, unitId: 'unit'),
            child: const Text('Lernziele öffnen'),
          ),
        ),
      );
      final intent = state.beginAuthentication();
      await f.tap(tester, find.text('Lernziele öffnen'));
      expect(requests, isEmpty);
      expect(find.text('Vorwissen & Lernziele'), findsNothing);
      state.cancelAuthentication(intent);
      await tester.pumpWidget(const SizedBox());
      state.dispose();
    },
  );
}
