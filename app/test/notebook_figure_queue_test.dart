import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:image/image.dart' as image;
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notebook_photo.dart';

http.Response picture() => http.Response.bytes(
  image.encodePng(image.Image(width: 4, height: 4)),
  200,
  headers: {'content-type': 'image/png'},
);

http.Response problem(int code) => http.Response(
  jsonEncode({'detail': 'Die Abbildung ist gerade beschäftigt.'}),
  code,
  headers: {'content-type': 'application/json'},
);

AppState account(MockClient client) =>
    AppState(
        api: Api(base: 'https://example.invalid/api', client: client),
      )
      ..user = {'id': 'synthetic-child', 'role': 'child'}
      ..familyId = 'family';

Widget screen(AppState state, int count) => MaterialApp(
  home: Scaffold(
    body: Column(
      children: [
        for (var index = 0; index < count; index++)
          SizedBox(
            height: 180,
            child: NotebookPhoto(
              state,
              materialId: 'page',
              figureIndex: index,
              revision: 1,
            ),
          ),
      ],
    ),
  ),
);

void main() {
  testWidgets('three private figures load one after another', (tester) async {
    final pending = List.generate(3, (_) => Completer<http.Response>());
    final paths = <String>[];
    final state = account(
      MockClient((request) {
        final index = paths.length;
        paths.add(request.url.path);
        return pending[index].future;
      }),
    );
    await tester.pumpWidget(screen(state, 3));
    await tester.pump();
    expect(paths, ['/api/materials/page/figures/0']);
    pending[0].complete(picture());
    await tester.pump();
    await tester.pump();
    expect(paths, [
      '/api/materials/page/figures/0',
      '/api/materials/page/figures/1',
    ]);
    pending[1].complete(picture());
    await tester.pump();
    await tester.pump();
    expect(paths.last, '/api/materials/page/figures/2');
    pending[2].complete(picture());
    await tester.pumpAndSettle();
    expect(find.text('Foto erneut laden'), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('a temporary busy response is retried at most twice', (
    tester,
  ) async {
    var calls = 0;
    final state = account(
      MockClient((_) async {
        calls++;
        return calls < 3 ? problem(503) : picture();
      }),
    );
    await tester.pumpWidget(screen(state, 1));
    await tester.pump();
    expect(calls, 1);
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    expect(calls, 2);
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(calls, 3);
    expect(find.text('Foto erneut laden'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('a permanent busy response stops and offers a manual reload', (
    tester,
  ) async {
    var calls = 0;
    final state = account(
      MockClient((_) async {
        calls++;
        return calls <= 3 ? problem(503) : picture();
      }),
    );
    await tester.pumpWidget(screen(state, 1));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(calls, 3);
    expect(find.text('Foto erneut laden'), findsOneWidget);
    await tester.pump(const Duration(seconds: 10));
    expect(calls, 3);
    await tester.tap(find.text('Foto erneut laden'));
    await tester.pumpAndSettle();
    expect(calls, 4);
    expect(find.text('Foto erneut laden'), findsNothing);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('a different error is not retried', (tester) async {
    var calls = 0;
    final state = account(
      MockClient((_) async {
        calls++;
        return problem(403);
      }),
    );
    await tester.pumpWidget(screen(state, 1));
    await tester.pumpAndSettle();
    expect(calls, 1);
    expect(find.text('Foto erneut laden'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('switching account cancels queued figures before any GET', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    var calls = 0;
    final state = account(
      MockClient((_) {
        calls++;
        return pending.future;
      }),
    );
    await tester.pumpWidget(screen(state, 2));
    await tester.pump();
    expect(calls, 1);
    state.beginAuthentication();
    pending.complete(picture());
    await tester.pumpAndSettle();
    expect(calls, 1);
    expect(find.byType(Image), findsNothing);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('switching account cancels a busy retry', (tester) async {
    var calls = 0;
    final state = account(
      MockClient((_) async {
        calls++;
        return problem(503);
      }),
    );
    await tester.pumpWidget(screen(state, 1));
    await tester.pump();
    expect(calls, 1);
    state.beginAuthentication();
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(calls, 1);
    await tester.pumpWidget(const SizedBox());
    state.dispose();
  });

  testWidgets('closing the page cancels figures still waiting in the queue', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    var calls = 0;
    final state = account(
      MockClient((_) {
        calls++;
        return pending.future;
      }),
    );
    await tester.pumpWidget(screen(state, 2));
    await tester.pump();
    expect(calls, 1);
    await tester.pumpWidget(const SizedBox());
    pending.complete(picture());
    await tester.pumpAndSettle();
    expect(calls, 1);
    expect(tester.takeException(), isNull);
    state.dispose();
  });
}
