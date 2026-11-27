import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/child_photo_preview.dart';
import 'package:schulpilot/ui.dart';

void main() {
  testWidgets('local photo viewer uses simple labels and never sends photos', (
    tester,
  ) async {
    var requests = 0;
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) async {
          requests++;
          throw StateError('The local viewer must not contact the server.');
        }),
      ),
    )..user = {'id': 'synthetic-child', 'role': 'child'};
    final image = base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
    );
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () =>
                  showChildPhotoPreview(context, state, photos: [image, image]),
              child: const Text('Fotos öffnen'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Fotos öffnen'));
    await tester.pumpAndSettle();
    expect(find.text('Deine Fotos'), findsOneWidget);
    expect(
      find.text('Nur auf diesem Gerät · noch nicht abgegeben'),
      findsOneWidget,
    );
    expect(find.byTooltip('Vorheriges Foto'), findsOneWidget);
    expect(find.byTooltip('Nächstes Foto'), findsOneWidget);
    expect(find.byTooltip('Foto vergrößern'), findsOneWidget);
    await tester.tap(find.byTooltip('Nächstes Foto'));
    await tester.pumpAndSettle();
    expect(find.text('2 von 2'), findsOneWidget);
    await tester.tap(find.byTooltip('Foto vergrößern'));
    await tester.pumpAndSettle();
    expect(requests, 0);
    await tester.pumpWidget(const SizedBox.shrink());
    state.inbox.dispose();
    state.dispose();
  });
}
