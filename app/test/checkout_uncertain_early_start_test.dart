import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/store_screens.dart';
import 'package:schulpilot/ui.dart';

void main() {
  for (final responseStatus in [503, 409]) {
    testWidgets(
      'checkout start choice follows persisted intent after $responseStatus',
      (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final firstReply = Completer<http.Response>();
        final submissions = <Json>[];
        final state =
            AppState(
                api: Api(
                  base: 'https://example.invalid/api',
                  client: MockClient((request) {
                    if (request.url.path.endsWith('/store/catalog')) {
                      return Future.value(
                        http.Response(
                          jsonEncode({
                            'enabled': true,
                            'revision': 7,
                            'tax_notice': 'Endpreis',
                            'terms': 'Synthetische Vertragsfassung',
                            'plans': [
                              {
                                'id': 'start',
                                'name': 'Start',
                                'price_cents': 990,
                                'children': 1,
                                'calls': 300,
                              },
                            ],
                          }),
                          200,
                          headers: {
                            'content-type': 'application/json; charset=utf-8',
                          },
                        ),
                      );
                    }
                    if (request.method == 'POST' &&
                        request.url.path.endsWith('/families/family/orders')) {
                      submissions.add(Json.from(jsonDecode(request.body)));
                      if (submissions.length == 1) return firstReply.future;
                      return Future.value(
                        http.Response('{"detail":"temporary failure"}', 503),
                      );
                    }
                    throw StateError('Unexpected synthetic request');
                  }),
                ),
              )
              ..user = {
                'id': 'parent',
                'role': 'parent',
                'display_name': 'Testeltern',
                'families': [
                  {'id': 'family', 'name': 'Test', 'permission': 'owner'},
                ],
              }
              ..familyId = 'family';
        addTearDown(state.dispose);
        final router = GoRouter(
          initialLocation: '/bestellen/start',
          routes: [
            GoRoute(
              path: '/bestellen/:id',
              builder: (_, _) => CheckoutScreen(state, planId: 'start'),
            ),
          ],
        );
        addTearDown(router.dispose);
        await tester.pumpWidget(
          MaterialApp.router(theme: appTheme(), routerConfig: router),
        );
        await tester.pumpAndSettle();
        final terms = find.byType(CheckboxListTile).first;
        final early = find.byType(CheckboxListTile).at(1);
        final buy = find.widgetWithText(
          FilledButton,
          'Zahlungspflichtig bestellen',
        );
        await tester.ensureVisible(terms);
        await tester.tap(terms);
        await tester.pump();
        await tester.ensureVisible(buy);
        await tester.tap(buy);
        await tester.pump();
        expect(submissions, hasLength(1));
        expect(submissions.first['early_start'], false);
        firstReply.complete(
          http.Response('{"detail":"synthetic response"}', responseStatus),
        );
        await tester.pumpAndSettle();
        final toggle = tester.widget<CheckboxListTile>(early);
        expect(toggle.value, isFalse);
        if (responseStatus == 503) {
          expect(toggle.onChanged, isNull);
          await tester.ensureVisible(buy);
          await tester.tap(buy);
          await tester.pumpAndSettle();
          expect(submissions, hasLength(2));
          expect(submissions.last, submissions.first);
        } else {
          expect(toggle.onChanged, isNotNull);
          await tester.ensureVisible(early);
          await tester.tap(early);
          await tester.pumpAndSettle();
          expect(tester.widget<CheckboxListTile>(early).value, isTrue);
          expect(submissions, hasLength(1));
        }
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
      },
    );
  }
}
