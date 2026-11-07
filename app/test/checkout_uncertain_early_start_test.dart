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
        var catalogReads = 0;
        var catalogRevision = 7;
        var catalogPrice = 990;
        final state =
            AppState(
                api: Api(
                  base: 'https://example.invalid/api',
                  client: MockClient((request) {
                    if (request.url.path.endsWith('/store/catalog')) {
                      catalogReads++;
                      return Future.value(
                        http.Response(
                          jsonEncode({
                            'enabled': true,
                            'revision': catalogRevision,
                            'tax_notice': 'Endpreis',
                            'terms': 'Synthetische Vertragsfassung',
                            'plans': [
                              {
                                'id': 'start',
                                'name': 'Start',
                                'price_cents': catalogPrice,
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
        final originalTerms = tester.widget<CheckboxListTile>(terms).onChanged!;
        final originalEarly = tester.widget<CheckboxListTile>(early).onChanged!;
        if (responseStatus == 503) {
          originalTerms(true);
          originalEarly(true);
        } else {
          originalEarly(true);
          originalTerms(true);
        }
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isTrue);
        expect(tester.widget<CheckboxListTile>(early).value, isTrue);
        // Each field invalidates its own old callback, even though an
        // independent choice from the same rendered frame remains valid.
        originalTerms(false);
        originalEarly(false);
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isTrue);
        expect(tester.widget<CheckboxListTile>(early).value, isTrue);
        final currentTerms = tester.widget<CheckboxListTile>(terms).onChanged!;
        final currentEarly = tester.widget<CheckboxListTile>(early).onChanged!;
        currentEarly(false);
        currentTerms(false);
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isFalse);
        expect(tester.widget<CheckboxListTile>(early).value, isFalse);
        final capturedEarlyChange = tester
            .widget<CheckboxListTile>(early)
            .onChanged!;
        final oldConsent = tester.widget<CheckboxListTile>(terms).onChanged!;
        await tester.ensureVisible(terms);
        await tester.tap(terms);
        await tester.pump();
        await tester.tap(terms);
        await tester.pump();
        oldConsent(true);
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isFalse);
        await tester.tap(terms);
        await tester.pump();
        final staleConsentBuy = tester.widget<FilledButton>(buy).onPressed!;
        await tester.tap(terms);
        await tester.pump();
        await tester.tap(terms);
        await tester.pump();
        staleConsentBuy();
        await tester.pump();
        expect(submissions, isEmpty);
        final staleStartBuy = tester.widget<FilledButton>(buy).onPressed!;
        await tester.ensureVisible(early);
        await tester.tap(early);
        await tester.pump();
        await tester.tap(early);
        await tester.pump();
        staleStartBuy();
        await tester.pump();
        expect(submissions, isEmpty);
        final beforeSubmitConsent = tester
            .widget<CheckboxListTile>(terms)
            .onChanged!;
        final alreadyUsedBuy = tester.widget<FilledButton>(buy).onPressed!;
        await tester.ensureVisible(buy);
        await tester.tap(buy);
        await tester.pump();
        expect(submissions, hasLength(1));
        expect(submissions.first['early_start'], false);
        beforeSubmitConsent(false);
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isTrue);
        firstReply.complete(
          http.Response('{"detail":"synthetic response"}', responseStatus),
        );
        await tester.pumpAndSettle();
        alreadyUsedBuy();
        await tester.pump();
        expect(submissions, hasLength(1));
        final toggle = tester.widget<CheckboxListTile>(early);
        expect(toggle.value, isFalse);
        final consentBeforeRevocation = tester
            .widget<CheckboxListTile>(terms)
            .onChanged!;
        await tester.ensureVisible(terms);
        await tester.tap(terms);
        await tester.pump();
        consentBeforeRevocation(true);
        await tester.pump();
        expect(tester.widget<CheckboxListTile>(terms).value, isFalse);
        await tester.tap(terms);
        await tester.pump();
        if (responseStatus == 503) {
          expect(toggle.onChanged, isNull);
          capturedEarlyChange(true);
          await tester.pump();
          expect(tester.widget<CheckboxListTile>(early).value, isFalse);
          expect(
            tester
                .widget<OutlinedButton>(
                  find.widgetWithText(
                    OutlinedButton,
                    'Aktuelle Tarife erneut prüfen',
                  ),
                )
                .onPressed,
            isNull,
          );
          expect(catalogReads, 1);
          await tester.ensureVisible(buy);
          await tester.tap(buy);
          await tester.pumpAndSettle();
          expect(submissions, hasLength(2));
          expect(submissions.last, submissions.first);
        } else {
          expect(toggle.onChanged, isNotNull);
          final capturedReload = tester
              .widget<OutlinedButton>(
                find.widgetWithText(
                  OutlinedButton,
                  'Aktuelle Tarife erneut prüfen',
                ),
              )
              .onPressed!;
          await tester.ensureVisible(early);
          await tester.tap(early);
          await tester.pumpAndSettle();
          expect(tester.widget<CheckboxListTile>(early).value, isTrue);
          expect(submissions, hasLength(1));
          await tester.ensureVisible(buy);
          await tester.tap(buy);
          await tester.pumpAndSettle();
          expect(submissions, hasLength(2));
          expect(submissions.last['early_start'], isTrue);
          catalogRevision = 8;
          catalogPrice = 1490;
          capturedReload();
          await tester.pumpAndSettle();
          expect(catalogReads, 1);
          expect(find.text('Gesamtpreis: 9,90 €'), findsOneWidget);
        }
        expect(tester.takeException(), isNull);
        await tester.pumpWidget(const SizedBox());
      },
    );
  }
}
