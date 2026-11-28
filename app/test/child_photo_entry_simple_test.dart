import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/ui.dart';

import 'child_photos_day_ux90_test.dart' as view;
import 'child_school_day_actions_ux88_test.dart' as actions;
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
      expect(find.text('2 neue Seiten · 22 Plätze frei'), findsOneWidget);
      expect(find.text('Deine Fotos'), findsOneWidget);
      expect(
        find.text('Nur auf diesem Gerät – noch nicht abgegeben.'),
        findsOneWidget,
      );
      expect(server.submissions, 0);
      expect(
        server.requests.every((request) => request.startsWith('GET ')),
        isTrue,
      );
    },
  );

  for (final width in [320.0, 390.0]) {
    testWidgets('Saved pages make continuing the primary action at $width px', (
      tester,
    ) async {
      final server = fixture.PreparationServer(
        pages: [fixture.source(1, confirmed: true)],
      )..realUploads = true;
      await view.showDay(tester, server.state(), width: width, scale: 2);

      expect(find.text('Deine Seiten sind gespeichert'), findsOneWidget);
      final next = find.text('Mit diesen Seiten weiter');
      final photo = find.text('Noch eine Seite fotografieren');
      expect(next, findsOneWidget);
      expect(photo, findsOneWidget);
      expect(tester.getTopLeft(next).dy, lessThan(tester.getTopLeft(photo).dy));
      final primary = tester.widget<ActionButton>(
        find.ancestor(of: next, matching: find.byType(ActionButton)),
      );
      final secondary = tester.widget<ActionButton>(
        find.ancestor(of: photo, matching: find.byType(ActionButton)),
      );
      expect(primary.secondary, isFalse);
      expect(secondary.secondary, isTrue);
      expect(find.textContaining('Namen abschneiden'), findsOneWidget);
      expect(find.text('1 gespeicherte Seite ansehen'), findsOneWidget);
      expect(server.requests.every((r) => r.startsWith('GET ')), isTrue);

      await actions.tap(tester, 'Mit diesen Seiten weiter');
      expect(
        server.requests.where((r) => r == 'PUT /api/school-days/day/stage'),
        hasLength(1),
      );
      expect(server.submissions, 0);
      expect(tester.takeException(), isNull);
    });
  }

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
