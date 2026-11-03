import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/notification_panel.dart';
import 'package:schulpilot/push_client.dart';
import 'package:schulpilot/ui.dart';

http.Response response(Object value) => http.Response(
  jsonEncode(value),
  200,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

class SettingsPush extends PushClient {
  SettingsPush(super.api);
  final saves = <Json>[];
  Completer<void>? pending;
  bool nativeSettings = false, failStatus = false;
  Json status = {};
  @override
  bool get canOpenSettings => nativeSettings;
  @override
  Future<Json> deviceStatus() async {
    if (failStatus) throw StateError('synthetic device failure');
    return status;
  }

  @override
  Future<Json> callStatus() async => {};
  @override
  Future<void> enable(
    Json preferences, {
    bool requestPermission = true,
    Future<bool?> Function(Future<bool> Function() request)? confirmPermission,
  }) async {
    saves.add(Json.from(preferences));
    await pending?.future;
  }

  @override
  Future<void> forget({int? expectedRevision}) async {}
}

class SettingsState extends AppState {
  late final SettingsPush settingsPush = SettingsPush(api);
  SettingsState(Api api) : super(api: api);
  @override
  PushClient get push => settingsPush;
}

class PreferencesFixture {
  int devicesGets = 0, configGets = 0, deletes = 0, testGets = 0, testPosts = 0;
  bool testAccess = false;
  Completer<http.Response>? testPending;
  bool reminders = true;
  Completer<http.Response>? configPending, deletePending;
  late final state = SettingsState(
    Api(
      base: 'https://example.invalid/api',
      client: MockClient((r) async {
        if (r.url.path.endsWith('/test') && r.method == 'POST') {
          testPosts++;
          return testPending?.future ?? response({'id': 'synthetic-test'});
        }
        if (r.url.path.endsWith('/tests')) {
          testGets++;
          return response({'allowed': true, 'results': []});
        }
        if (r.method == 'DELETE') {
          deletes++;
          return deletePending?.future ?? response({});
        }
        if (r.url.path.endsWith('/config')) {
          configGets++;
          return configPending?.future ??
              response({'available': true, 'test_access': testAccess});
        }
        if (r.url.path.endsWith('/devices')) {
          devicesGets++;
          return response([
            {
              'id': 'device',
              'current': true,
              'quiet_start': 20,
              'quiet_end': 8,
              'timezone': 'Europe/Berlin',
              'reminders': reminders,
              'help_requests': true,
              'summaries': false,
              'family_calls': false,
            },
          ]);
        }
        throw StateError('Unexpected synthetic request');
      }),
    ),
  )..user = {'id': 'synthetic', 'role': 'child'};
  Future<void> show(WidgetTester tester, {double scale = 1}) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context)
              .copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
        home: Scaffold(
          body: SingleChildScrollView(child: NotificationPanel(state)),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> expand(WidgetTester tester) async {
    await tester.ensureVisible(find.text('Zeiten & Auswahl'));
    await tester.tap(find.text('Zeiten & Auswahl'));
    await tester.pumpAndSettle();
  }

  Future<void> close(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox());
    state.settingsPush.dispose();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  testWidgets(
    'stale child device controls cannot change a rotated session draft',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      await f.expand(tester);
      final reminder = find.widgetWithText(
        SwitchListTile,
        'Fertige Lernrunden & Lernzeit',
      );
      final help = find.widgetWithText(
        SwitchListTile,
        'Wenn meine Eltern antworten',
      );
      final oldReminder = tester.widget<SwitchListTile>(reminder).onChanged!;
      final oldHelp = tester.widget<SwitchListTile>(help).onChanged!;
      final times = find.byType(DropdownButtonFormField<int>);
      final oldStart = tester
          .widget<DropdownButtonFormField<int>>(times.at(0))
          .onChanged!;
      final oldEnd = tester
          .widget<DropdownButtonFormField<int>>(times.at(1))
          .onChanged!;
      f.state.api.token = 'synthetic-replacement-session';
      oldReminder(false);
      oldHelp(false);
      oldStart(3);
      oldEnd(4);
      await tester.pump();
      expect(tester.widget<SwitchListTile>(reminder).value, isTrue);
      expect(tester.widget<SwitchListTile>(help).value, isTrue);
      expect(find.text('Ruhezeit: 20:00–08:00'), findsWidgets);
      expect(find.text('Noch nicht gespeichert'), findsNothing);
      expect(f.state.settingsPush.saves, isEmpty);
      await f.close(tester);
    },
  );
  testWidgets(
    'stale parent device controls cannot change a rotated session draft',
    (tester) async {
      final f = PreferencesFixture();
      f.state.user = {'id': 'synthetic-parent', 'role': 'parent'};
      f.state.settingsPush.nativeSettings = true;
      await f.show(tester);
      await f.expand(tester);
      final calls = find.widgetWithText(
        SwitchListTile,
        'Familienanrufe auf diesem Gerät',
      );
      final summaries = find.widgetWithText(SwitchListTile, 'Tagesüberblick');
      final oldCalls = tester.widget<SwitchListTile>(calls).onChanged!;
      final oldSummaries = tester.widget<SwitchListTile>(summaries).onChanged!;
      f.state.api.token = 'synthetic-replacement-session';
      oldCalls(true);
      oldSummaries(true);
      await tester.pump();
      expect(tester.widget<SwitchListTile>(calls).value, isFalse);
      expect(tester.widget<SwitchListTile>(summaries).value, isFalse);
      expect(find.text('Noch nicht gespeichert'), findsNothing);
      expect(f.state.settingsPush.saves, isEmpty);
      await f.close(tester);
    },
  );
  testWidgets(
    'old controls cannot change another account after a real account switch',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      await f.expand(tester);
      final reminder = find.widgetWithText(
        SwitchListTile,
        'Fertige Lernrunden & Lernzeit',
      );
      final oldReminder = tester.widget<SwitchListTile>(reminder).onChanged!;
      final times = find.byType(DropdownButtonFormField<int>);
      final oldStart = tester
          .widget<DropdownButtonFormField<int>>(times.first)
          .onChanged!;
      f.state.user = {'id': 'other-synthetic-child', 'role': 'child'};
      f.state.notifyListeners();
      await tester.pumpAndSettle();
      await f.expand(tester);
      oldReminder(false);
      oldStart(3);
      await tester.pump();
      expect(tester.widget<SwitchListTile>(reminder).value, isTrue);
      expect(find.text('Ruhezeit: 20:00–08:00'), findsWidgets);
      expect(find.text('Noch nicht gespeichert'), findsNothing);
      expect(f.state.settingsPush.saves, isEmpty);
      await f.close(tester);
    },
  );
  testWidgets(
    'controls from a covered route or pending save cannot alter the draft',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      await f.expand(tester);
      final reminder = find.widgetWithText(
        SwitchListTile,
        'Fertige Lernrunden & Lernzeit',
      );
      final oldReminder = tester.widget<SwitchListTile>(reminder).onChanged!;
      final navigator = tester.state<NavigatorState>(
        find.byType(Navigator).first,
      );
      unawaited(
        navigator.push(
          MaterialPageRoute<void>(
            builder: (_) => const Scaffold(body: Text('Andere Seite')),
          ),
        ),
      );
      await tester.pumpAndSettle();
      oldReminder(false);
      await tester.pump();
      navigator.pop();
      await tester.pumpAndSettle();
      expect(tester.widget<SwitchListTile>(reminder).value, isTrue);
      f.state.settingsPush.pending = Completer<void>();
      final save = find.widgetWithText(ActionButton, 'Änderungen speichern');
      await tester.ensureVisible(save);
      await tester.tap(save);
      await tester.pump();
      oldReminder(false);
      await tester.pump();
      expect(f.state.settingsPush.saves.single['reminders'], isTrue);
      expect(find.text('Noch nicht gespeichert'), findsNothing);
      f.state.settingsPush.pending!.complete();
      await tester.pumpAndSettle();
      await f.expand(tester);
      expect(tester.widget<SwitchListTile>(reminder).value, isTrue);
      await f.close(tester);
    },
  );
  testWidgets(
    'device edits survive resume while a clean view refreshes server preferences',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      await f.expand(tester);
      await tester.tap(find.text('Fertige Lernrunden & Lernzeit'));
      await tester.pump();
      expect(find.text('Noch nicht gespeichert'), findsOneWidget);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      await f.expand(tester);
      final reminder = find.widgetWithText(
        SwitchListTile,
        'Fertige Lernrunden & Lernzeit',
      );
      expect(tester.widget<SwitchListTile>(reminder).value, isFalse);
      await f.close(tester);
      final g = PreferencesFixture();
      await g.show(tester);
      g.reminders = false;
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      await g.expand(tester);
      expect(tester.widget<SwitchListTile>(reminder).value, isFalse);
      await g.close(tester);
    },
  );
  testWidgets(
    'one device save freezes its draft and excludes a parallel disable',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      await f.expand(tester);
      f.state.settingsPush.pending = Completer<void>();
      final save = find.widgetWithText(ActionButton, 'Änderungen speichern');
      await tester.ensureVisible(save);
      await tester.tap(save);
      await tester.pump();
      expect(f.state.settingsPush.saves.length, 1);
      expect(
        find.text('Geräteeinstellungen werden gespeichert …'),
        findsOneWidget,
      );
      expect(
        tester
            .widget<SwitchListTile>(
              find.widgetWithText(
                SwitchListTile,
                'Fertige Lernrunden & Lernzeit',
              ),
            )
            .onChanged,
        isNull,
      );
      final off = tester.widget<ActionButton>(
        find.widgetWithText(ActionButton, 'Auf diesem Gerät ausschalten'),
      );
      expect(off.enabled, isFalse);
      await off.onPressed();
      expect(f.deletes, 0);
      expect(f.state.settingsPush.saves.single['quiet_start'], 20);
      f.state.settingsPush.pending!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Noch nicht gespeichert'), findsNothing);
      await f.close(tester);
    },
  );
  testWidgets(
    'same-id new session stops an old device load before its next request',
    (tester) async {
      final f = PreferencesFixture();
      f.configPending = Completer<http.Response>();
      await tester.pumpWidget(
        MaterialApp(home: Scaffold(body: NotificationPanel(f.state))),
      );
      await tester.pump();
      expect(f.configGets, 1);
      final old = f.configPending!;
      f.configPending = null;
      f.state.user = Json.from(f.state.user!);
      f.state.notifyListeners();
      await tester.pumpAndSettle();
      expect(f.devicesGets, 1);
      old.complete(response({'available': true}));
      await tester.pumpAndSettle();
      expect(f.devicesGets, 1);
      await f.close(tester);
    },
  );
  testWidgets(
    'pending device disable blocks a saved enable callback and announces completion',
    (tester) async {
      final f = PreferencesFixture();
      await f.show(tester);
      f.deletePending = Completer<http.Response>();
      final save = tester
          .widget<ActionButton>(
            find.widgetWithText(ActionButton, 'Änderungen speichern'),
          )
          .onPressed;
      final off = find.widgetWithText(
        ActionButton,
        'Auf diesem Gerät ausschalten',
      );
      await tester.ensureVisible(off);
      await tester.tap(off);
      await tester.pump();
      await save();
      expect(f.state.settingsPush.saves, isEmpty);
      expect(f.deletes, 1);
      f.deletePending!.complete(response({}));
      await tester.pumpAndSettle();
      expect(
        find.text('Benachrichtigungen für dieses Gerät sind ausgeschaltet.'),
        findsOneWidget,
      );
      await f.close(tester);
    },
  );
  testWidgets(
    'a synthetic notification test stops polling after replacement login',
    (tester) async {
      final f = PreferencesFixture();
      f.testAccess = true;
      f.testPending = Completer<http.Response>();
      await f.show(tester);
      final send = find.widgetWithText(
        ActionButton,
        'Test an dieses Gerät senden',
      );
      await tester.ensureVisible(send);
      await tester.tap(send);
      await tester.pump();
      expect(f.testPosts, 1);
      f.testAccess = false;
      f.state.user = Json.from(f.state.user!);
      f.state.notifyListeners();
      await tester.pumpAndSettle();
      final before = f.testGets;
      f.testPending!.complete(response({'id': 'synthetic-test'}));
      await tester.pump(const Duration(seconds: 3));
      await tester.pumpAndSettle();
      expect(f.testGets, before);
      expect(f.testPosts, 1);
      await f.close(tester);
    },
  );
  for (final failed in [false, true]) {
    testWidgets(
      'unknown native permission is not a delivery claim, thrown: $failed',
      (tester) async {
        final f = PreferencesFixture();
        f.state.settingsPush.nativeSettings = true;
        f.state.settingsPush.failStatus = failed;
        await f.show(tester);
        expect(find.text('Für dieses Gerät eingeschaltet.'), findsNothing);
        expect(
          find.textContaining('Berechtigung konnte gerade nicht geprüft'),
          findsOneWidget,
        );
        expect(find.textContaining('synthetic device failure'), findsNothing);
        f.state.settingsPush.failStatus = false;
        f.state.settingsPush.status = {'permission': true, 'channel': true};
        final before = f.configGets;
        await tester.tap(find.text('Gerätestatus erneut prüfen'));
        await tester.pumpAndSettle();
        expect(f.configGets, before + 1);
        expect(f.state.settingsPush.saves, isEmpty);
        expect(find.text('Für dieses Gerät eingeschaltet.'), findsOneWidget);
        await f.close(tester);
      },
    );
  }
  testWidgets(
    'browser permission does not require an Android channel but Android does',
    (tester) async {
      final f = PreferencesFixture();
      f.state.settingsPush.status = {'permission': true};
      await f.show(tester);
      expect(find.text('Für dieses Gerät eingeschaltet.'), findsOneWidget);
      await f.close(tester);
      final g = PreferencesFixture();
      g.state.settingsPush.nativeSettings = true;
      g.state.settingsPush.status = {'permission': true};
      await g.show(tester);
      expect(find.text('Für dieses Gerät eingeschaltet.'), findsNothing);
      expect(find.text('Gerätestatus erneut prüfen'), findsOneWidget);
      await g.close(tester);
    },
  );
}
