import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'commerce_payments_test.dart' as payments;
import 'commerce_trial_launch_test.dart' as trial;

void main() {
  testWidgets(
    'new sign-in clears secret, hides configuration and invalidates captured save',
    (tester) async {
      final f = payments.Fixture();
      await f.mount(tester);
      await payments.tap(tester, find.text('PayPal und Google Pay einrichten'));
      final secret = payments.field(
        'Neues Client-Secret (leer = gespeichertes behalten)',
      );
      await tester.enterText(secret, 'synthetic-secret-only');
      await tester.pump();
      final controller = tester.widget<TextField>(secret).controller!;
      final save = tester
          .widget<FilledButton>(
            find.widgetWithText(FilledButton, 'Zahlungsangaben speichern'),
          )
          .onPressed!;
      final load = tester
          .widget<OutlinedButton>(
            find.widgetWithText(
              OutlinedButton,
              'Gespeicherten Zahlungsstand laden',
            ),
          )
          .onPressed!;
      final intent = f.state.beginAuthentication();
      await tester.pumpAndSettle();
      expect(controller.text, isEmpty);
      expect(find.text('PayPal und Google Pay einrichten'), findsNothing);
      save();
      load();
      f.state.cancelAuthentication(intent);
      save();
      load();
      await tester.pumpAndSettle();
      expect(f.requests.where((r) => r.method == 'PUT'), isEmpty);
      expect(f.requests.where((r) => r.method == 'GET'), hasLength(1));
      expect(find.text('PayPal und Google Pay einrichten'), findsNothing);
    },
  );

  for (final status in [200, 503]) {
    testWidgets(
      'late payment save $status cannot restore old configuration or secret',
      (tester) async {
        final f = payments.Fixture();
        final pending = Completer<http.Response>();
        f.intercept = (request) => request.method == 'PUT'
            ? pending.future
            : Future.value(trial.reply(payments.config()));
        await f.mount(tester);
        await payments.tap(
          tester,
          find.text('PayPal und Google Pay einrichten'),
        );
        final secret = payments.field(
          'Neues Client-Secret (leer = gespeichertes behalten)',
        );
        await tester.enterText(secret, 'synthetic-secret-only');
        await tester.pump();
        final controller = tester.widget<TextField>(secret).controller!;
        await tester.ensureVisible(find.text('Zahlungsangaben speichern'));
        await tester.tap(find.text('Zahlungsangaben speichern'));
        await tester.pump();
        expect(f.requests.where((r) => r.method == 'PUT'), hasLength(1));
        final intent = f.state.beginAuthentication();
        pending.complete(
          status == 200
              ? trial.reply(payments.config(revision: 2))
              : trial.reply({'detail': 'Synthetischer Fehler'}, 503),
        );
        await tester.pumpAndSettle();
        expect(controller.text, isEmpty);
        expect(
          find.textContaining('Zahlungsangaben gespeichert'),
          findsNothing,
        );
        expect(find.textContaining('Synthetischer Fehler'), findsNothing);
        f.state.cancelAuthentication(intent);
        await tester.pumpAndSettle();
        expect(find.text('PayPal und Google Pay einrichten'), findsNothing);
        expect(f.requests.where((r) => r.method == 'PUT'), hasLength(1));
      },
    );
  }

  testWidgets(
    'payment settings opened during an authentication intent issue no request',
    (tester) async {
      final f = payments.Fixture();
      final intent = f.state.beginAuthentication();
      await f.mount(tester);
      expect(f.requests, isEmpty);
      expect(find.text('PayPal und Google Pay einrichten'), findsNothing);
      f.state.cancelAuthentication(intent);
      await tester.pumpAndSettle();
      expect(f.requests, isEmpty);
      expect(find.text('PayPal und Google Pay einrichten'), findsNothing);
    },
  );
}
