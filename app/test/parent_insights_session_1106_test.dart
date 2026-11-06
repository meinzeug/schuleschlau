import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/parent_insights_panel.dart';
import 'package:schulpilot/ui.dart';

import 'parent_insights_test.dart' show account, insight, response;

Future<void> mount(WidgetTester tester, AppState state) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(),
      home: Scaffold(
        body: SingleChildScrollView(
          child: ParentInsightsPanel(state, childId: 'child'),
        ),
      ),
    ),
  );
  await tester.pump();
  await tester.pump();
}

void main() {
  testWidgets('late report and old actions are rejected on token change', (
    tester,
  ) async {
    final delayed = Completer<http.Response>();
    var reads = 0, writes = 0;
    final state = account(
      MockClient((r) async {
        if (r.method != 'GET') {
          writes++;
          return response({});
        }
        if (++reads == 1) return response(insight());
        return delayed.future;
      }),
    );
    state.api.token = 'old';
    await mount(tester, state);
    expect(find.text('KI-Lernkompass'), findsOneWidget);
    await tester.tap(find.byTooltip('Lernkompass neu laden'));
    await tester.pump();
    state.api.token = 'new';
    state.notifyListeners();
    await tester.pump();
    expect(find.text('KI-Lernkompass'), findsNothing);
    delayed.complete(response(insight()));
    await tester.pump();
    await tester.pump();
    expect(find.text('KI-Lernkompass'), findsNothing);
    expect(writes, 0);
  });

  testWidgets('a new authentication intent blocks the old review action', (
    tester,
  ) async {
    var writes = 0;
    final state = account(
      MockClient((r) async {
        if (r.method != 'GET') writes++;
        return response(insight());
      }),
    );
    await mount(tester, state);
    final button = find.text('Jetzt mit KI auswerten');
    await tester.ensureVisible(button);
    await tester.pump();
    state.beginAuthentication();
    await tester.tap(button);
    await tester.pump();
    expect(writes, 0);
  });

  testWidgets(
    'a completed review request does not refresh after login starts',
    (tester) async {
      final delayed = Completer<http.Response>();
      var reads = 0, writes = 0;
      final state = account(
        MockClient((r) async {
          if (r.method == 'GET') {
            reads++;
            return response(insight());
          }
          writes++;
          return delayed.future;
        }),
      );
      await mount(tester, state);
      final button = find.text('Jetzt mit KI auswerten');
      await tester.ensureVisible(button);
      await tester.pump();
      await tester.tap(button);
      await tester.pump();
      expect(writes, 1);
      state.beginAuthentication();
      delayed.complete(response({}));
      await tester.pump();
      await tester.pump();
      expect(reads, 1);
    },
  );

  testWidgets('a delayed read is ignored after login starts', (tester) async {
    final delayed = Completer<http.Response>();
    var reads = 0;
    final state = account(
      MockClient((r) async {
        if (++reads == 1) return response(insight());
        return delayed.future;
      }),
    );
    await mount(tester, state);
    await tester.tap(find.byTooltip('Lernkompass neu laden'));
    await tester.pump();
    state.beginAuthentication();
    final changed = insight();
    changed['topics'] = [
      {
        'ref': 't',
        'subject': 'Künstlich',
        'topic': 'Veraltetes Ergebnis',
        'assisted_tasks': 1,
      },
    ];
    delayed.complete(response(changed));
    await tester.pump();
    await tester.pump();
    expect(find.textContaining('Veraltetes Ergebnis'), findsNothing);
  });

  testWidgets(
    'revoked access clears a previously saved report after an action',
    (tester) async {
      final state = account(
        MockClient((r) async {
          if (r.method == 'GET') return response(insight());
          return response({'detail': 'Zugriff entzogen'}, 403);
        }),
      );
      await mount(tester, state);
      expect(find.textContaining('Bruchaddition'), findsWidgets);
      final button = find.text('Jetzt mit KI auswerten');
      await tester.ensureVisible(button);
      await tester.pump();
      await tester.tap(button);
      await tester.pump();
      await tester.pump();
      expect(find.textContaining('Bruchaddition'), findsNothing);
      expect(find.text('Zugriff entzogen'), findsOneWidget);
      expect(find.text('Jetzt mit KI auswerten'), findsNothing);
    },
  );

  testWidgets(
    'a late refresh cannot restore a report after access is revoked',
    (tester) async {
      final post = Completer<http.Response>();
      final refresh = Completer<http.Response>();
      var reads = 0;
      final state = account(
        MockClient((r) async {
          if (r.method != 'GET') return post.future;
          if (++reads == 1) return response(insight());
          return refresh.future;
        }),
      );
      await mount(tester, state);
      final button = find.text('Jetzt mit KI auswerten');
      await tester.ensureVisible(button);
      await tester.pump();
      await tester.tap(button);
      await tester.pump();
      await tester.ensureVisible(find.byTooltip('Lernkompass neu laden'));
      await tester.pump();
      await tester.tap(find.byTooltip('Lernkompass neu laden'));
      await tester.pump();
      expect(reads, 2);
      post.complete(response({'detail': 'Zugriff entzogen'}, 403));
      await tester.pump();
      await tester.pump();
      refresh.complete(response(insight()));
      await tester.pump();
      await tester.pump();
      expect(find.textContaining('Bruchaddition'), findsNothing);
      expect(find.text('Zugriff entzogen'), findsOneWidget);
    },
  );

  testWidgets(
    'replacing AppState loads the new account and ignores the old response',
    (tester) async {
      final delayed = Completer<http.Response>();
      final first = account(MockClient((r) => delayed.future));
      final second = account(MockClient((r) async => response(insight())));
      await mount(tester, first);
      await mount(tester, second);
      expect(find.text('KI-Lernkompass'), findsOneWidget);
      expect(find.textContaining('Bruchaddition'), findsWidgets);
      delayed.complete(response({...insight(), 'topics': []}));
      await tester.pump();
      await tester.pump();
      expect(find.textContaining('Bruchaddition'), findsWidgets);
    },
  );
}
