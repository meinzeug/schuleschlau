import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/family_call_native.dart';
import 'package:schulpilot/family_call_service.dart';

import 'family_call_test.dart' show FakeMedia, makeState, metadata, response;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
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
