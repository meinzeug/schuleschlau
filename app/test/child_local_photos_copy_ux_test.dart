import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:schulpilot/child_account.dart';

import 'child_local_tools_ux88_test.dart' as fixture;
import 'child_photos_day_ux90_test.dart' as photos;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final (width, scale) in [(320.0, 1.0), (390.0, 1.0), (320.0, 2.0)]) {
    for (final hasPhoto in [false, true]) {
      testWidgets(
        'Local photo status is clear at $width / $scale× with photo=$hasPhoto',
        (tester) async {
          final requests = <http.Request>[];
          final state = fixture.account((request) async {
            requests.add(request);
            return fixture.reply([]);
          });
          if (hasPhoto) {
            await state.pendingUploads.add(
              'child-user',
              'child',
              'day',
              photos.bytes(3),
            );
          }
          await fixture.show(
            tester,
            ChildAccount(state),
            size: Size(width, 844),
            scale: scale,
          );
          await fixture.tap(tester, find.text('Lokale Fotos'));
          expect(
            find.text(
              'Nur auf diesem Gerät, höchstens 24 Stunden. Öffnen sendet kein Foto.',
            ),
            findsOneWidget,
          );
          if (hasPhoto) {
            expect(find.text('Foto 1 · noch nicht gesendet'), findsOneWidget);
            expect(
              find.text('1 Foto auf diesem Gerät · höchstens 8 Fotos möglich'),
              findsOneWidget,
            );
            expect(find.textContaining('Gespeichert am'), findsOneWidget);
            expect(find.text('Foto ansehen'), findsOneWidget);
            expect(find.text('Zum zugehörigen Tag'), findsOneWidget);
          } else {
            expect(
              find.textContaining('Hier warten keine Fotos auf das Senden.'),
              findsOneWidget,
            );
            expect(
              find.textContaining('0 Fotos auf diesem Gerät'),
              findsNothing,
            );
          }
          expect(requests.every((request) => request.method == 'GET'), isTrue);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
}
