import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/ideas100_source_tools.dart';

import 'child_local_tools_ux88_test.dart' as host;
import 'material_confirmed_uncertainties_124_test.dart' as fixture;

void main() {
  testWidgets('Unsichere Textstelle bleibt vor Bestätigung sichtbar', (
    tester,
  ) async {
    final value = fixture.Fixture();
    value.data['confirmed'] = false;
    value.data['status'] = 'review';
    value.data['uncertainties'] = [];
    value.data['source_blocks'] = [
      {
        'kind': 'paragraph',
        'text': value.data['content'],
        'reading_uncertainties': [fixture.blockWarning],
      },
    ];
    await value.mount(tester, size: const Size(320, 568), scale: 2);
    expect(find.text('Hier bitte genau hinschauen:'), findsOneWidget);
    expect(find.text(fixture.blockWarning), findsOneWidget);
    expect(find.text('Stimmt, weiter'), findsOneWidget);
    expect(value.writes, isEmpty);

    await host.tap(tester, find.text('Text öffnen'));
    final reader = tester.widget<Ideas100SourceReader>(
      find.byType(Ideas100SourceReader),
    );
    expect(reader.uncertainties, [fixture.blockWarning]);
    expect(value.writes, isEmpty);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Gleiche Unsicherheit erscheint nur einmal vor der Bestätigung', (
    tester,
  ) async {
    final value = fixture.Fixture();
    value.data['confirmed'] = false;
    value.data['status'] = 'review';
    value.data['uncertainties'] = [
      fixture.pageWarning,
      42,
      {'stelle': 'unscharf'},
    ];
    value.data['source_blocks'] = [
      {
        'kind': 'paragraph',
        'text': value.data['content'],
        'reading_uncertainties': [
          fixture.pageWarning,
          fixture.blockWarning,
          84,
        ],
      },
    ];
    await value.mount(tester);
    expect(find.text(fixture.pageWarning), findsOneWidget);
    expect(find.text(fixture.blockWarning), findsOneWidget);
    expect(find.text('42'), findsOneWidget);
    expect(find.text('{stelle: unscharf}'), findsOneWidget);
    expect(find.text('84'), findsOneWidget);
    expect(value.writes, isEmpty);
    await host.tap(tester, find.text('Stimmt, weiter'));
    final writes = value.writes.toList();
    expect(writes, hasLength(1));
    expect(writes.single.method, 'PUT');
    final body = jsonDecode(writes.single.body) as Map;
    expect(body['content'], value.data['content']);
    expect(body['revision'], value.data['revision']);
    expect(body['uncertainties_resolved'], true);
  });
}
