import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
// Inspect only the pinned plugin's synthetic host request, never write a file.
// ignore: implementation_imports
import 'package:file_saver/src/messages.g.dart'
    show FileSaverHostApi, SaveRequest;
import 'package:schulpilot/parent_plan_screen.dart';
import 'package:schulpilot/parent_deadlines_dialog.dart';

import 'parent_saved_tools_ux90_test.dart' as saved;
import 'parent_insights_test.dart' as fixture;
import 'parent_messages_ux88_test.dart' show tap;

void main() {
  testWidgets('calendar bytes arriving after login do not open a file save', (
    t,
  ) async {
    final f = saved.Fixture();
    final response = Completer<http.Response>();
    f.respond = (r) => r.url.path.endsWith('.ics')
        ? response.future
        : Future.value(
            fixture.response({
              'child_name': 'Künstliches Kind',
              'start': '2026-10-22',
              'end': '2026-11-20',
              'total': 1,
              'items': [
                {
                  'id': 'goal',
                  'subject': 'Mathematik',
                  'topic': 'Brüche',
                  'due': '2026-10-23',
                  'mandatory': true,
                },
              ],
            }),
          );
    var saves = 0;
    const channel = BasicMessageChannel<Object?>(
      'dev.flutter.pigeon.file_saver.FileSaverHostApi.saveAs',
      FileSaverHostApi.pigeonChannelCodec,
    );
    t.binding.defaultBinaryMessenger.setMockDecodedMessageHandler<Object?>(
      channel,
      (_) async {
        saves++;
        return ['synthetic-memory-only'];
      },
    );
    addTearDown(
      () => t.binding.defaultBinaryMessenger
          .setMockDecodedMessageHandler<Object?>(channel, null),
    );
    await f.mount(
      t,
      (c) => TextButton(
        onPressed: () => showParentDeadlines(c, f.state, 'child'),
        child: const Text('Öffnen'),
      ),
    );
    await tap(t, find.text('Öffnen'));
    await t.tap(find.text('Kalenderdatei speichern'));
    await t.pump();
    expect(f.requests, hasLength(2));
    final intent = f.state.beginAuthentication();
    response.complete(
      http.Response(
        'BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n',
        200,
        headers: {'content-type': 'text/calendar'},
      ),
    );
    await t.pumpAndSettle();
    f.state.cancelAuthentication(intent);
    await t.pumpAndSettle();
    expect(saves, 0);
    expect(f.requests, hasLength(2));
  }, skip: kIsWeb);

  testWidgets('calendar export and its old button stop at a new login intent', (
    t,
  ) async {
    final f = saved.Fixture();
    f.respond = (r) async => fixture.response({
      'child_name': 'Künstliches Kind',
      'start': '2026-10-22',
      'end': '2026-11-20',
      'total': 1,
      'items': [
        {
          'id': 'goal',
          'subject': 'Mathematik',
          'topic': 'Brüche',
          'due': '2026-10-23',
          'mandatory': true,
        },
      ],
    });
    await f.mount(
      t,
      (c) => TextButton(
        onPressed: () => showParentDeadlines(c, f.state, 'child'),
        child: const Text('Öffnen'),
      ),
    );
    await tap(t, find.text('Öffnen'));
    final stale = t
        .widget<FilledButton>(
          find.ancestor(
            of: find.text('Kalenderdatei speichern'),
            matching: find.byType(FilledButton),
          ),
        )
        .onPressed!;
    final intent = f.state.beginAuthentication();
    stale();
    await t.pumpAndSettle();
    expect(find.text('Gespeicherte Termine'), findsNothing);
    expect(f.requests, hasLength(1));
    f.state.cancelAuthentication(intent);
    await t.pumpAndSettle();
    expect(f.requests, hasLength(1));
  });

  testWidgets('late calendar data does not reappear after a login intent', (
    t,
  ) async {
    final f = saved.Fixture();
    final response = Completer<http.Response>();
    f.respond = (_) => response.future;
    await f.mount(
      t,
      (c) => TextButton(
        onPressed: () => showParentDeadlines(c, f.state, 'child'),
        child: const Text('Öffnen'),
      ),
    );
    await t.tap(find.text('Öffnen'));
    await t.pump();
    final intent = f.state.beginAuthentication();
    response.complete(
      fixture.response({
        'child_name': 'Künstliches Kind',
        'start': '2026-10-22',
        'end': '2026-11-20',
        'total': 0,
        'items': [],
      }),
    );
    await t.pumpAndSettle();
    f.state.cancelAuthentication(intent);
    await t.pumpAndSettle();
    expect(find.textContaining('Termine von Künstliches Kind'), findsNothing);
    expect(f.requests, hasLength(1));
  });
  testWidgets(
    'PK036 only explicit supported overview criteria initialize parent goal selection',
    (t) async {
      final f = saved.Fixture();
      f.respond = (r) async => fixture.response({
        ...fixture.plan(),
        'filters': {...r.url.queryParameters},
      });
      await f.mount(
        t,
        (_) => ParentPlanScreen(
          f.state,
          childId: 'child',
          initialSection: 'topics',
          initialFilters: const {
            'source': 'confirmed',
            'obligation': 'mandatory',
            'q': 'Brüche',
            'unsupported': 'ignored',
          },
        ),
      );
      expect(f.requests.single.url.queryParameters['source'], 'confirmed');
      expect(f.requests.single.url.queryParameters['obligation'], 'mandatory');
      expect(f.requests.single.url.queryParameters['q'], 'Brüche');
      expect(
        f.requests.single.url.queryParameters.containsKey('unsupported'),
        isFalse,
      );
      expect(f.requests.single.method, 'GET');
    },
  );
  testWidgets(
    'PK036 invalid route criterion cannot replace known parent filter meaning',
    (t) async {
      final f = saved.Fixture();
      f.respond = (r) async => fixture.response({
        ...fixture.plan(),
        'filters': {...r.url.queryParameters},
      });
      await f.mount(
        t,
        (_) => ParentPlanScreen(
          f.state,
          childId: 'child',
          initialSection: 'topics',
          initialFilters: const {
            'source': 'arbitrary',
            'obligation': 'mandatory',
          },
        ),
      );
      expect(
        f.requests.single.url.queryParameters.containsKey('source'),
        isFalse,
      );
      expect(f.requests.single.url.queryParameters['obligation'], 'mandatory');
      expect(f.requests.single.method, 'GET');
    },
  );
  testWidgets(
    'PK039 calendar export uses the reviewed actual interval and explicit file action',
    (t) async {
      final f = saved.Fixture();
      f.respond = (r) async => r.url.path.endsWith('.ics')
          ? http.Response(
              'BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n',
              200,
              headers: {'content-type': 'text/calendar'},
            )
          : fixture.response({
              'child_name': 'Künstliches Kind',
              'start': '2026-10-22',
              'end': '2026-11-20',
              'total': 1,
              'items': [
                {
                  'id': 'goal',
                  'subject': 'Mathematik',
                  'topic': 'Brüche',
                  'due': '2026-10-23',
                  'mandatory': true,
                },
              ],
            });
      SaveRequest? output;
      const channel = BasicMessageChannel<Object?>(
        'dev.flutter.pigeon.file_saver.FileSaverHostApi.saveAs',
        FileSaverHostApi.pigeonChannelCodec,
      );
      t.binding.defaultBinaryMessenger.setMockDecodedMessageHandler<Object?>(
        channel,
        (request) async {
          output = (request as List).single as SaveRequest;
          return ['synthetic-memory-only'];
        },
      );
      addTearDown(
        () => t.binding.defaultBinaryMessenger
            .setMockDecodedMessageHandler<Object?>(channel, null),
      );
      await f.mount(
        t,
        (c) => TextButton(
          onPressed: () => showParentDeadlines(c, f.state, 'child'),
          child: const Text('Öffnen'),
        ),
      );
      await tap(t, find.text('Öffnen'));
      expect(f.requests, hasLength(1));
      expect(output, isNull);
      await tap(t, find.text('Kalenderdatei speichern'));
      expect(f.requests, hasLength(2));
      expect(f.requests.last.method, 'GET');
      expect(f.requests.last.url.queryParameters, {
        'start': '2026-10-22',
        'end': '2026-11-20',
      });
      expect(output!.mimeType, 'text/calendar');
      expect(utf8.decode(output!.bytes!), contains('BEGIN:VCALENDAR'));
      expect(output!.fileExtension, '.ics');
    },
    skip: kIsWeb,
  );
}
