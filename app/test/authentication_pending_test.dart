import 'dart:async';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:schulpilot/family_call_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:schulpilot/api.dart';

class NoopCalls extends FamilyCallService {
  NoopCalls(super.state) : super(nativeEnabled: false);
  @override
  Future<void> clear() async {}
}

class FailingCalls extends FamilyCallService {
  FailingCalls(super.state) : super(nativeEnabled: false);
  @override
  Future<void> clear() async => throw StateError('synthetic cleanup failure');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('only the current intent can clear a pending login', () {
    final state = AppState();
    final old = state.beginAuthentication();
    expect(state.authenticationPending, isTrue);
    final current = state.beginAuthentication();
    state.cancelAuthentication(old);
    expect(state.authenticationPending, isTrue);
    state.cancelAuthentication(current);
    expect(state.authenticationPending, isFalse);
    state.dispose();
  });
  test('accepting the current login settles authentication', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final state = AppState();
    final revision = state.beginAuthentication();
    await state.accept({
      'user': {'id': 'synthetic', 'role': 'parent', 'families': []},
    }, authenticationRevision: revision);
    expect(state.authenticationPending, isFalse);
    final settledRevision = state.api.requestIdentity().$3;
    state.cancelAuthentication(revision);
    expect(state.api.requestIdentity().$3, settledRevision);
    state.dispose();
  });
  test('failed login settles its own intent', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (_) async => http.Response('{"detail":"invalid"}', 401),
        ),
      ),
    );
    await expectLater(
      state.login('synthetic', 'synthetic'),
      throwsA(isA<ApiError>()),
    );
    expect(state.authenticationPending, isFalse);
    state.dispose();
  });
  test('failed old login does not settle a newer intent', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final entered = Completer<void>(), reply = Completer<http.Response>();
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient((_) {
          entered.complete();
          return reply.future;
        }),
      ),
    );
    final old = state.login('synthetic', 'synthetic');
    final expected = expectLater(old, throwsA(isA<ApiError>()));
    await entered.future;
    final newer = state.beginAuthentication();
    reply.complete(http.Response('{"detail":"invalid"}', 401));
    await expected;
    expect(state.authenticationPending, isTrue);
    state.cancelAuthentication(newer);
    state.dispose();
  });
  test('failed logout settles its own intent', () async {
    FlutterSecureStorage.setMockInitialValues({});
    final state = AppState(
      api: Api(
        base: 'https://example.invalid/api',
        client: MockClient(
          (_) async => http.Response('{"detail":"offline"}', 503),
        ),
      ),
      familyCallFactory: (s) => NoopCalls(s),
    )..user = {'id': 'synthetic', 'role': 'parent'};
    await expectLater(state.logout(), throwsA(isA<ApiError>()));
    expect(state.authenticationPending, isFalse);
    expect(state.user?['id'], 'synthetic');
    state.dispose();
  });
  test('invalid login response releases the active intent', () async {
    final state = AppState();
    final intent = state.beginAuthentication();
    await expectLater(
      state.accept({'user': {}}, authenticationRevision: intent),
      throwsA(isA<ApiError>()),
    );
    expect(state.authenticationPending, isFalse);
    state.dispose();
  });
  test('failed early cleanup releases its active intent', () async {
    final state = AppState(familyCallFactory: (s) => FailingCalls(s))
      ..user = {'id': 'synthetic', 'role': 'parent'};
    await expectLater(
      state.clear(expectedUser: state.user),
      throwsA(isA<StateError>()),
    );
    expect(state.authenticationPending, isFalse);
    expect(state.user?['id'], 'synthetic');
    state.dispose();
  });
}
