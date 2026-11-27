import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image/image.dart' as image;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/material_screen.dart';
import 'package:schulpilot/ui.dart';

import 'child_sources_input_ux87_test.dart' as source;

class Fixture {
  final calls = <http.Request>[];
  Future<http.Response> Function(http.Request)? materialHandler;
  Json material = {
    ...source.page('page'),
    'synthetic': false,
    'has_image': true,
  };
  late final state =
      AppState(
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((request) async {
              calls.add(request);
              if (request.url.path.endsWith('/image')) {
                return http.Response.bytes(
                  image.encodePng(image.Image(width: 4, height: 4)),
                  200,
                  headers: {'content-type': 'image/png'},
                );
              }
              if (request.method != 'GET') {
                throw StateError('No write expected');
              }
              if (materialHandler != null) return materialHandler!(request);
              return http.Response(
                jsonEncode(material),
                200,
                headers: {'content-type': 'application/json'},
              );
            }),
          ),
        )
        ..familyId = 'family'
        ..user = {
          'id': 'synthetic-parent',
          'role': 'parent',
          'families': [
            {'id': 'family', 'permission': 'owner'},
          ],
        };
  late final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, _) => MaterialScreen(state, materialId: 'page'),
      ),
    ],
  );

  Future<void> mount(WidgetTester tester, {bool settle = true}) async {
    addTearDown(() async {
      await tester.pumpWidget(const SizedBox.shrink());
      router.dispose();
      state.dispose();
    });
    await tester.pumpWidget(
      MaterialApp.router(theme: appTheme(), routerConfig: router),
    );
    if (settle) {
      await tester.pumpAndSettle();
    } else {
      await tester.pump();
    }
  }
}

Future<void> tap(WidgetTester tester, Finder target) async {
  await tester.ensureVisible(target);
  await tester.pumpAndSettle();
  await tester.tap(target);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'draft remains private through login and restores after deliberate reload',
    (tester) async {
      final fixture = Fixture();
      await fixture.mount(tester);
      await tap(tester, find.text('Erkannten Text verbessern'));
      final field = find.widgetWithText(
        TextField,
        'Erkannter Unterrichtsstoff',
      );
      await tester.enterText(field, 'Mein künstlicher Korrekturentwurf.');
      await tester.pump();
      final staleSave = tester
          .widget<ActionButton>(
            find.widgetWithText(ActionButton, 'Stimmt, weiter'),
          )
          .onPressed;
      final revision = fixture.state.beginAuthentication();
      await staleSave();
      await tester.pumpAndSettle();
      expect(find.text('Mein künstlicher Korrekturentwurf.'), findsNothing);
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Heftseite neu laden'),
            )
            .onPressed,
        isNull,
      );
      final before = fixture.calls.length;
      fixture.state.cancelAuthentication(revision);
      await tester.pumpAndSettle();
      expect(fixture.calls.length, before);
      await tap(tester, find.text('Heftseite neu laden'));
      expect(find.text('Mein künstlicher Korrekturentwurf.'), findsOneWidget);
      expect(fixture.calls.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('changed page keeps draft as a conflict after login recovery', (
    tester,
  ) async {
    final fixture = Fixture();
    await fixture.mount(tester);
    await tap(tester, find.text('Erkannten Text verbessern'));
    await tester.enterText(
      find.widgetWithText(TextField, 'Erkannter Unterrichtsstoff'),
      'Mein eigener ungeprüfter Entwurf.',
    );
    await tester.pump();
    final revision = fixture.state.beginAuthentication();
    await tester.pumpAndSettle();
    fixture.material = {
      ...fixture.material,
      'revision': 2,
      'content': 'Neu gelesener künstlicher Text.',
    };
    fixture.state.cancelAuthentication(revision);
    await tester.pumpAndSettle();
    await tap(tester, find.text('Heftseite neu laden'));
    expect(
      find.textContaining('Diese Heftseite wurde inzwischen geändert'),
      findsOneWidget,
    );
    expect(find.text('Mein eigener ungeprüfter Entwurf.'), findsOneWidget);
    expect(fixture.calls.every((request) => request.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('late old material cannot replace an explicitly reloaded page', (
    tester,
  ) async {
    final fixture = Fixture();
    final pending = Completer<http.Response>();
    var reads = 0;
    fixture.materialHandler = (_) async {
      reads++;
      if (reads == 1) return pending.future;
      return http.Response(
        jsonEncode({...fixture.material, 'content': 'Neue künstliche Seite.'}),
        200,
        headers: {'content-type': 'application/json'},
      );
    };
    await fixture.mount(tester, settle: false);
    expect(reads, 1);
    final revision = fixture.state.beginAuthentication();
    await tester.pump();
    fixture.state.cancelAuthentication(revision);
    await tester.pump();
    await tap(tester, find.text('Heftseite neu laden'));
    expect(find.textContaining('Neue künstliche Seite.'), findsOneWidget);
    pending.complete(
      http.Response(
        jsonEncode({...fixture.material, 'content': 'Alte künstliche Seite.'}),
        200,
        headers: {'content-type': 'application/json'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('Alte künstliche Seite.'), findsNothing);
    expect(find.textContaining('Neue künstliche Seite.'), findsOneWidget);
    expect(reads, 2);
    expect(fixture.calls.every((request) => request.method == 'GET'), isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    'opening a material during login does not read it automatically',
    (tester) async {
      final fixture = Fixture();
      final revision = fixture.state.beginAuthentication();
      await fixture.mount(tester);
      expect(fixture.calls, isEmpty);
      expect(
        tester
            .widget<OutlinedButton>(
              find.widgetWithText(OutlinedButton, 'Heftseite neu laden'),
            )
            .onPressed,
        isNull,
      );
      fixture.state.cancelAuthentication(revision);
      await tester.pumpAndSettle();
      expect(fixture.calls, isEmpty);
      await tap(tester, find.text('Heftseite neu laden'));
      expect(
        fixture.calls.where(
          (request) => request.url.path == '/api/materials/page',
        ),
        hasLength(1),
      );
      expect(fixture.calls.every((request) => request.method == 'GET'), isTrue);
      expect(tester.takeException(), isNull);
    },
  );
}
