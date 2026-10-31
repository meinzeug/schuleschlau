import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'child_photos_day_ux90_test.dart' as view;
import 'school_day_background_test.dart' as fixture;

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets(
    'Empty photo entry keeps the next action and privacy guidance clear',
    (tester) async {
      final server = fixture.PreparationServer(pages: [])..realUploads = true;
      await view.showDay(tester, server.state(), scale: 2);

      expect(find.text('Erste Seite fotografieren'), findsOneWidget);
      expect(find.text('Fotos abgeben'), findsNothing);
      expect(find.textContaining('Namen abschneiden'), findsOneWidget);
      expect(find.textContaining('0 neue Seiten'), findsNothing);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Collected pages lead to explicit handoff and later text review',
    (tester) async {
      final server = fixture.PreparationServer(
        pages: [fixture.source(1, status: 'uploaded')],
      )..realUploads = true;
      final state = server.state();
      await state.pendingUploads.add('kid', 'child', 'day', view.bytes(2));
      await view.showDay(tester, state);

      expect(find.text('Fotos abgeben'), findsOneWidget);
      expect(
        find.text('Danach kannst du den Text und unklare Stellen ansehen.'),
        findsOneWidget,
      );
      expect(find.text('2 neue Seiten · 22 Plätze frei'), findsOneWidget);
      expect(find.text('Deine neuen Fotos'), findsOneWidget);
      expect(find.textContaining('noch auf diesem Gerät'), findsOneWidget);
      expect(server.submissions, 0);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
    },
  );

  testWidgets('Full page count uses the actual limit and keeps handoff', (
    tester,
  ) async {
    final server = fixture.PreparationServer(
      pages: [fixture.source(1), fixture.source(2)],
    )..realUploads = true;
    server.todayOverride = {...server.day, 'max_pages': 2};
    await view.showDay(tester, server.state());

    expect(find.text('2 neue Seiten · 0 Plätze frei'), findsOneWidget);
    expect(
      find.textContaining('Alle 2 Plätze für heute sind belegt.'),
      findsOneWidget,
    );
    expect(find.text('Fotos abgeben'), findsOneWidget);
    expect(find.text('Noch eine Seite fotografieren'), findsNothing);
    expect(server.submissions, 0);
  });

  testWidgets('Read-only day never claims that unused photo slots are full', (
    tester,
  ) async {
    final server =
        fixture.PreparationServer(
            pages: [fixture.source(1, status: 'uploaded')],
          )
          ..archived = true
          ..realUploads = true;
    await view.showDay(tester, server.state());

    expect(find.textContaining('Plätze für heute sind belegt'), findsNothing);
    expect(
      find.text(
        'Gespeicherter Tag · neue Fotos gehören zum heutigen Schultag.',
      ),
      findsOneWidget,
    );
    expect(
      server.requests.every((request) => request.startsWith('GET ')),
      isTrue,
    );
    expect(tester.takeException(), isNull);
  });
}
