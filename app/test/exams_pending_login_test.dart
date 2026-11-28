import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'exams_screen_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  for (final role in ['child', 'parent']) {
    for (final tab in ['prepare', 'review']) {
      testWidgets('opening $tab as $role during login does not read exams', (
        tester,
      ) async {
        final example = fixture.Fixture(role: role);
        final intent = example.state.beginAuthentication();
        await example.mount(tester, selected: 'exam', tab: tab);
        expect(
          example.calls.where((r) => r.url.path.contains('/exams')),
          isEmpty,
        );
        expect(find.text('Anmeldung läuft …'), findsOneWidget);
        expect(find.text('Zur Übersicht'), findsNothing);
        expect(example.writes, isEmpty);
        example.state.cancelAuthentication(intent);
        await tester.pumpAndSettle();
        expect(
          find.text('Öffne Klassenarbeiten bitte erneut.'),
          findsOneWidget,
        );
        expect(
          example.calls.where((r) => r.url.path.contains('/exams')),
          isEmpty,
        );
        expect(example.writes, isEmpty);
        await fixture.tap(tester, find.text('Zur Übersicht'));
        expect(find.text('Übersicht'), findsOneWidget);
      });
    }
  }
}
