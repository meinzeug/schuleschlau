import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'child_photos_day_ux90_test.dart' as photo;
import 'school_day_background_test.dart' as day;

class PhotoServer extends day.PreparationServer {
  PhotoServer({required super.pages}) {
    realUploads = true;
  }

  @override
  Future<http.Response> handle(http.Request request) {
    if (request.method == 'GET' &&
        request.url.path.startsWith('/api/materials/') &&
        request.url.path.endsWith('/image')) {
      requests.add('GET ${request.url.path}');
      return Future.value(
        http.Response.bytes(
          photo.bytes(10),
          200,
          headers: {'content-type': 'image/png'},
        ),
      );
    }
    return super.handle(request);
  }
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  for (final scale in [1.0, 2.0]) {
    testWidgets('Unreadable photo opens directly without changes at $scale×', (
      tester,
    ) async {
      final page = day.source(1, status: 'unreadable')
        ..['synthetic'] = false
        ..['has_image'] = true;
      final server = PhotoServer(pages: [page]);
      await photo.showDay(tester, server.state(), scale: scale);
      final initialError = tester.takeException();
      expect(initialError, isNull, reason: 'initial screen');
      final preview = find.byTooltip('Foto 1 ansehen');
      await tester.ensureVisible(preview);
      await tester.pumpAndSettle();
      expect(preview.hitTestable(), findsOneWidget);
      await tester.tap(preview);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: 'opened photo');
      expect(find.text('Heftfoto'), findsOneWidget);
      expect(server.pages, hasLength(1));
      expect(server.requests.where((r) => !r.startsWith('GET ')), isEmpty);
      await tester.tap(find.byTooltip('Schließen'));
      await tester.pumpAndSettle();
      expect(find.text('Ersetzen'), findsOneWidget);
      expect(find.byTooltip('Foto 1 entfernen').hitTestable(), findsOneWidget);
      expect(server.requests.where((r) => !r.startsWith('GET ')), isEmpty);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    });
  }

  testWidgets('A page without an image does not offer a broken photo preview', (
    tester,
  ) async {
    final page = day.source(1, status: 'unreadable')
      ..['synthetic'] = false
      ..['has_image'] = false;
    final server = PhotoServer(pages: [page]);
    await photo.showDay(tester, server.state());
    expect(find.byTooltip('Foto 1 ansehen'), findsNothing);
    expect(find.text('Ersetzen'), findsOneWidget);
    expect(server.requests.where((r) => r.endsWith('/image')), isEmpty);
    expect(server.requests.where((r) => !r.startsWith('GET ')), isEmpty);
    await tester.pumpWidget(const SizedBox());
  });

  for (final login in [true, false]) {
    testWidgets(
      'A stale photo callback is inert after ${login ? 'login intent and cancellation' : 'account switch'}',
      (tester) async {
        final page = day.source(1, status: 'unreadable')
          ..['synthetic'] = false
          ..['has_image'] = true;
        final server = PhotoServer(pages: [page]);
        final state = server.state();
        await photo.showDay(tester, state);
        final preview = find.byTooltip('Foto 1 ansehen');
        final ink = tester.widget<InkWell>(
          find.descendant(of: preview, matching: find.byType(InkWell)).first,
        );
        final oldTap = ink.onTap!;
        final before = server.requests.length;
        if (login) {
          final intent = state.beginAuthentication();
          oldTap();
          state.cancelAuthentication(intent);
          oldTap();
        } else {
          state.user = {
            'id': 'another-child',
            'role': 'child',
            'child_id': 'other',
          };
          oldTap();
        }
        await tester.pumpAndSettle();
        expect(find.text('Heftfoto'), findsNothing);
        expect(server.requests.length, before);
        expect(server.pages, hasLength(1));
        expect(tester.takeException(), isNull);
        if (login) {
          await day.tapText(tester, 'Erneut laden');
          final afterReload = server.requests.length;
          oldTap();
          await tester.pumpAndSettle();
          expect(find.text('Heftfoto'), findsNothing);
          expect(server.requests.length, afterReload);
          expect(tester.takeException(), isNull);
        }
        await tester.pumpWidget(const SizedBox());
      },
    );
  }
}
