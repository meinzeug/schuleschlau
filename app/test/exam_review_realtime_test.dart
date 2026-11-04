import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'exams_screen_test.dart' as fixture;

class ReadFixture extends fixture.Fixture {
  int? nextFailure;
  @override
  Future<http.Response> handle(http.Request request) async {
    if (request.method == 'GET' &&
        request.url.path.endsWith('/exams/exam/review') &&
        nextFailure != null) {
      calls.add(request);
      final code = nextFailure!;
      nextFailure = null;
      return fixture.reply({'detail': 'Künstlicher Lesefehler'}, code);
    }
    return super.handle(request);
  }

  int get reviewReads => calls
      .where(
        (r) => r.method == 'GET' && r.url.path.endsWith('/exams/exam/review'),
      )
      .length;
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final code in [403, 404, 429]) {
    testWidgets(
      'review HTTP $code stops automatic reads and allows explicit retry',
      (tester) async {
        final f = ReadFixture();
        await f.mount(tester, selected: 'exam', tab: 'review');
        final field = find.widgetWithText(
          TextField,
          'Dein Verbesserungsversuch',
        );
        await tester.ensureVisible(field);
        await tester.enterText(field, 'Mein eigener Versuch');
        f.nextFailure = code;
        await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
        expect(find.text('Künstlicher Lesefehler'), findsOneWidget);
        if (code != 429) {
          expect(field, findsNothing);
        } else {
          expect(
            tester.widget<TextField>(field).controller!.text,
            'Mein eigener Versuch',
          );
        }
        final readsAfterFailure = f.reviewReads;
        await fixture.pause(tester);
        await fixture.resume(tester);
        await tester.pump(const Duration(seconds: 4));
        expect(f.reviewReads, readsAfterFailure);
        await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
        expect(f.reviewReads, readsAfterFailure + 1);
        expect(
          tester.widget<TextField>(field).controller!.text,
          'Mein eigener Versuch',
        );
        expect(f.writes, isEmpty);
        expect(tester.takeException(), isNull);
      },
    );
  }
  testWidgets('repeated denied reads retain the original draft and context', (
    tester,
  ) async {
    final f = ReadFixture();
    await f.mount(tester, selected: 'exam', tab: 'review');
    final field = find.widgetWithText(TextField, 'Dein Verbesserungsversuch');
    await tester.ensureVisible(field);
    await tester.enterText(field, 'Diesen Versuch behalten');
    for (var index = 0; index < 2; index++) {
      f.nextFailure = 403;
      await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
      expect(field, findsNothing);
    }
    await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
    expect(
      tester.widget<TextField>(field).controller!.text,
      'Diesen Versuch behalten',
    );
    expect(f.writes, isEmpty);
  });

  testWidgets('source change while access is denied keeps draft separate', (
    tester,
  ) async {
    final f = ReadFixture();
    await f.mount(tester, selected: 'exam', tab: 'review');
    final field = find.widgetWithText(TextField, 'Dein Verbesserungsversuch');
    await tester.ensureVisible(field);
    await tester.enterText(field, 'Nicht übernommener Versuch');
    f.nextFailure = 403;
    await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
    f.report = {
      ...f.report,
      'context_revision': 'b' * 64,
      'analysis_id': 'new-analysis',
    };
    await fixture.tap(tester, find.text('Gespeicherten Stand laden'));
    expect(
      find.text('Dein vorheriger Entwurf · Quelle geändert, nicht übernommen'),
      findsOneWidget,
    );
    expect(tester.widget<TextField>(field).controller!.text, isEmpty);
    expect(find.text('Nicht übernommener Versuch'), findsOneWidget);
    expect(f.writes, isEmpty);
  });
}
