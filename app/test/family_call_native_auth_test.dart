import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/family_call_native.dart';
import 'package:schulpilot/family_call_service.dart';

import 'family_call_test.dart'
    show FakeMedia, callId, makeState, metadata, response;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  test(
    'Late incoming Android notice is cancelled after sign-in starts',
    () async {
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      final started = Completer<void>(),
          release = Completer<void>(),
          cancelledTwice = Completer<void>();
      var cancels = 0, heartbeats = 0;
      messenger.setMockMethodCallHandler(FamilyCallNative.channel, (
        call,
      ) async {
        if (call.method == 'showIncoming') {
          started.complete();
          await release.future;
        }
        if (call.method == 'cancel') {
          expect((call.arguments as Map)['call_id'], callId);
          if (++cancels == 2) cancelledTwice.complete();
        }
        return null;
      });
      addTearDown(
        () =>
            messenger.setMockMethodCallHandler(FamilyCallNative.channel, null),
      );
      final state = makeState((request) async {
        if (request.url.path.endsWith('/active')) {
          return response({
            'calls': [metadata('ringing', role: 'parent')],
          });
        }
        if (request.url.path.endsWith('/heartbeat')) heartbeats++;
        return response(metadata('ringing', role: 'parent'));
      }, role: 'parent');
      final calls = FamilyCallService(state);
      calls.activate(state.user);
      await started.future.timeout(const Duration(seconds: 5));
      state.beginAuthentication();
      await Future<void>.delayed(Duration.zero);
      expect(cancels, 1);
      release.complete();
      await cancelledTwice.future.timeout(const Duration(seconds: 5));
      expect(heartbeats, 0);
      await calls.clear();
      calls.dispose();
    },
    skip: kIsWeb,
  );

  test('New sign-in stops a late Android capture service', () async {
    final channel =
        TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
    final pendingStart = Completer<void>();
    final methods = <String>[];
    channel.setMockMethodCallHandler(FamilyCallNative.channel, (call) async {
      methods.add(call.method);
      if (call.method == 'startMedia') await pendingStart.future;
      return null;
    });
    addTearDown(
      () => channel.setMockMethodCallHandler(FamilyCallNative.channel, null),
    );
    final fake = FakeMedia();
    final state = makeState((request) async {
      if (request.url.path.endsWith('/config')) {
        return response({'available': true});
      }
      if (request.url.path.endsWith('/active')) {
        return response({'calls': []});
      }
      return response(metadata('ringing'));
    });
    final calls = FamilyCallService(state, mediaFactory: () => fake);
    calls.activate(state.user);
    await Future<void>.delayed(Duration.zero);
    final starting = calls.start();
    await Future<void>.delayed(Duration.zero);
    expect(methods, contains('startMedia'));
    state.beginAuthentication();
    await Future<void>.delayed(Duration.zero);
    expect(fake.closed, isTrue);
    expect(methods, contains('stopMedia'));
    pendingStart.complete();
    await Future<void>.delayed(Duration.zero);
    await starting;
    expect(calls.media, isNull);
    expect(fake.connected, 0);
    final clearing = calls.clear();
    await Future<void>.delayed(Duration.zero);
    await clearing;
    calls.dispose();
  }, skip: kIsWeb);
}
