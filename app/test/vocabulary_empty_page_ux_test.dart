import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/ui.dart';

import 'vocabulary_test.dart' as words;

void main() {
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    testWidgets(
      'An empty later word page has an honest way back at $width and $scale×',
      (tester) async {
        final requests = <http.Request>[];
        var firstReads = 0;
        await words.open(
          tester,
          requests,
          width: width,
          textScale: scale,
          openTools: false,
          cards: false,
          respond: (request) async {
            if (request.url.path.endsWith('/imports')) {
              return words.reply({'imports': []});
            }
            final page = request.url.queryParameters['page'];
            final result = words.listing();
            if (page == '2') {
              result['items'] = [];
              result['pagination'] = {'page': 2, 'page_size': 15, 'total': 15};
            } else {
              firstReads++;
              result['pagination'] = {
                'page': 1,
                'page_size': 15,
                'total': firstReads == 1 ? 16 : 15,
              };
            }
            return words.reply(result);
          },
        );
        await words.tap(tester, find.byTooltip('Nächste Wortseite'));
        expect(
          find.text('Auf dieser Seite sind keine Wörter.'),
          findsOneWidget,
        );
        expect(
          find.textContaining('noch keine Wörter in dieser Sprache'),
          findsNothing,
        );
        expect(find.byTooltip('Vorherige Wortseite'), findsNothing);
        await words.tap(tester, find.text('Vorherige Seite'));
        expect(find.text('Apfel'), findsOneWidget);
        expect(firstReads, 2);
        expect(requests.every((r) => r.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox.shrink());
      },
    );
  }

  for (final login in [true, false]) {
    testWidgets(
      'An old empty-page action is inert after ${login ? 'a new sign-in' : 'account replacement'}',
      (tester) async {
        final requests = <http.Request>[];
        final (state, _) = await words.open(
          tester,
          requests,
          openTools: false,
          cards: false,
          respond: (request) async {
            if (request.url.path.endsWith('/imports')) {
              return words.reply({'imports': []});
            }
            final result = words.listing();
            if (request.url.queryParameters['page'] == '2') {
              result['items'] = [];
              result['pagination'] = {'page': 2, 'page_size': 15, 'total': 15};
            }
            return words.reply(result);
          },
        );
        await words.tap(tester, find.byTooltip('Nächste Wortseite'));
        final oldAction = tester
            .widget<ActionPanel>(
              find.byWidgetPredicate(
                (w) => w is ActionPanel && w.actionLabel == 'Vorherige Seite',
              ),
            )
            .onPressed!;
        final before = requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          oldAction();
          state.cancelAuthentication(intent);
        } else {
          state.user = {
            'id': 'another-account',
            'role': 'child',
            'child_id': 'other',
          };
        }
        oldAction();
        await tester.pumpAndSettle();
        expect(requests, hasLength(before));
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox.shrink());
      },
    );
  }
}
