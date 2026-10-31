import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'schulbuddy_test.dart' as f;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  const technical =
      'Schulbuddy ist noch nicht mit der ausdrücklich gewählten Luna/high-Route eingerichtet.';
  const childMessage =
      'Schulbuddy ist gerade nicht verfügbar. Schau später noch einmal nach.';

  for (final parent in [false, true]) {
    testWidgets(
      'Providerhinweis bleibt für Eltern technisch, für Kinder verständlich: $parent',
      (tester) async {
        final h = await f.open(
          tester,
          parent: parent,
          width: 320,
          height: 568,
          scale: 2,
          respond: (_) async => f.reply({
            ...f.contextResult('today', available: false),
            'notice': technical,
          }),
        );
        addTearDown(() async => tester.pumpWidget(const SizedBox.shrink()));
        await f.tap(tester, find.text('Buddy öffnen'));
        expect(find.text(parent ? technical : childMessage), findsOneWidget);
        expect(find.text(parent ? childMessage : technical), findsNothing);
        expect(tester.widget<TextField>(f.field()).enabled, isFalse);
        expect(h.calls.every((request) => request.method == 'GET'), isTrue);
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('Providerfehler beim Senden erhält die Kinderfrage', (
    tester,
  ) async {
    final h = await f.open(
      tester,
      respond: (request) async => request.method == 'GET'
          ? f.reply(f.contextResult('today'))
          : f.reply({'detail': technical}, 503),
    );
    addTearDown(() async => tester.pumpWidget(const SizedBox.shrink()));
    await f.tap(tester, find.text('Buddy öffnen'));
    await tester.ensureVisible(f.field());
    await tester.enterText(f.field(), 'Wie geht das?');
    await f.tap(tester, find.text('Frage senden'));
    expect(find.text(childMessage), findsOneWidget);
    expect(find.text(technical), findsNothing);
    expect(
      tester.widget<TextField>(f.field()).controller!.text,
      'Wie geht das?',
    );
    expect(h.calls.where((request) => request.method == 'POST'), hasLength(1));
    expect(tester.takeException(), isNull);
  });

  for (final size in [(390.0, 844.0, 1.0), (320.0, 568.0, 2.0)]) {
    testWidgets('Frageideen bleiben auf $size erreichbar und senden bewusst', (
      tester,
    ) async {
      final h = await f.open(
        tester,
        width: size.$1,
        height: size.$2,
        scale: size.$3,
        respond: (request) async => request.method == 'GET'
            ? f.reply(f.contextResult('today'))
            : f.reply(f.turn(key: request.headers['Idempotency-Key'])),
      );
      addTearDown(() async => tester.pumpWidget(const SizedBox.shrink()));
      await f.tap(tester, find.text('Buddy öffnen'));
      expect(find.byType(ActionChip), findsNWidgets(2));
      expect(find.text('Worauf sollte ich achten?'), findsNothing);
      expect(h.calls.every((request) => request.method == 'GET'), isTrue);
      await f.tap(tester, find.text('Weitere Frageideen'));
      expect(find.byType(ActionChip), findsNWidgets(3));
      await tester.ensureVisible(f.field());
      await tester.enterText(f.field(), 'Mein eigener Entwurf');
      await f.tap(tester, find.text('Worauf sollte ich achten?'));
      final posts = h.calls.where((request) => request.method == 'POST');
      expect(posts, hasLength(1));
      expect(
        jsonDecode(posts.single.body)['question'],
        'Worauf sollte ich achten?',
      );
      expect(
        tester.widget<TextField>(f.field()).controller!.text,
        'Mein eigener Entwurf',
      );
      expect(find.byType(ActionChip), findsNothing);
      expect(find.text('Betrachte zuerst, was gesucht ist.'), findsOneWidget);
      await f.tap(tester, find.text('Frageideen anzeigen'));
      expect(find.byType(ActionChip), findsNWidgets(3));
      await f.tap(tester, find.text('Frageideen ausblenden'));
      expect(find.byType(ActionChip), findsNothing);
      expect(
        h.calls.where((request) => request.method == 'POST'),
        hasLength(1),
      );
      expect(tester.takeException(), isNull);
    });
  }
}
