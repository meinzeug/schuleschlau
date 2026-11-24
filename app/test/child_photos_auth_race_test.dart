import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:http/testing.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/child_account.dart';
import 'package:schulpilot/child_photo_preview.dart';
import 'package:schulpilot/pending_uploads.dart';
import 'package:schulpilot/ui.dart';

import 'child_photos_day_ux90_test.dart' as photo;
import 'child_local_tools_ux88_test.dart' as helpers;

class PausedStorage extends FlutterSecureStorage {
  bool pause = false;
  final entered = Completer<void>();
  final resume = Completer<void>();
  @override
  Future<String?> read({
    required String key,
    AppleOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    AppleOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (pause && key == PendingUploads.storageKey) {
      pause = false;
      entered.complete();
      await resume.future;
    }
    return super.read(key: key);
  }
}

AppState account(FlutterSecureStorage storage) {
  final state =
      AppState(
          storage: storage,
          api: Api(
            base: 'https://example.invalid/api',
            client: MockClient((_) async => helpers.reply([])),
          ),
        )
        ..user = {
          'id': 'synthetic-owner',
          'role': 'child',
          'child_id': 'synthetic-child',
        };
  state.api.token = 'synthetic-session';
  state.collectionViews['child_account'] = {
    'account': state.user,
    'section': 'photos',
  };
  return state;
}

Future<void> mount(WidgetTester tester, AppState state) async {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(390, 844);
  final router = GoRouter(
    routes: [
      GoRoute(path: '/', builder: (_, _) => ChildAccount(state)),
      GoRoute(
        path: '/after-school/:id',
        builder: (_, _) => const Scaffold(body: Text('Testtag')),
      ),
    ],
  );
  addTearDown(() async {
    await tester.pumpWidget(const SizedBox.shrink());
    router.dispose();
    state.dispose();
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
  await tester.pumpWidget(
    MaterialApp.router(theme: appTheme(), routerConfig: router),
  );
  await tester.pump();
}

void main() {
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));
  testWidgets(
    'delayed local photos are discarded after a new login intent and can be reloaded',
    (tester) async {
      final storage = PausedStorage();
      final state = account(storage);
      await state.pendingUploads.add(
        'synthetic-owner',
        'synthetic-child',
        'synthetic-day',
        photo.bytes(2),
      );
      storage.pause = true;
      await mount(tester, state);
      await tester.runAsync(() => storage.entered.future);
      final intent = state.beginAuthentication();
      storage.resume.complete();
      await tester.pumpAndSettle();
      expect(find.text('Vorgemerktes Foto 1'), findsNothing);
      expect(find.text('Bitte lade die lokalen Fotos erneut.'), findsOneWidget);
      state.cancelAuthentication(intent);
      await helpers.tap(tester, find.text('Erneut laden'));
      expect(find.text('Vorgemerktes Foto 1'), findsOneWidget);
    },
  );
  testWidgets(
    'old photo actions do not open the image or day after a new login intent',
    (tester) async {
      const storage = FlutterSecureStorage();
      final state = account(storage);
      await state.pendingUploads.add(
        'synthetic-owner',
        'synthetic-child',
        'synthetic-day',
        photo.bytes(2),
      );
      await mount(tester, state);
      await tester.pumpAndSettle();
      state.beginAuthentication();
      await helpers.tap(tester, find.text('Foto ansehen'));
      expect(find.byType(InteractiveViewer), findsNothing);
      await helpers.tap(tester, find.text('Zum zugehörigen Tag'));
      expect(find.text('Testtag'), findsNothing);
      expect(
        (await state.pendingUploads.read('synthetic-owner')),
        hasLength(1),
      );
    },
  );
  testWidgets('preview closes on an action after login intent changes', (
    tester,
  ) async {
    final state = account(const FlutterSecureStorage());
    addTearDown(state.dispose);
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(390, 844);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => showChildPhotoPreview(
                context,
                state,
                photos: [photo.bytes(2), photo.bytes(3)],
              ),
              child: const Text('Öffnen'),
            ),
          ),
        ),
      ),
    );
    await helpers.tap(tester, find.text('Öffnen'));
    expect(find.text('1 von 2'), findsOneWidget);
    state.beginAuthentication();
    await helpers.tap(tester, find.byTooltip('Nächstes vorgemerktes Foto'));
    expect(find.byType(InteractiveViewer), findsNothing);
    expect(find.text('2 von 2'), findsNothing);
  });
}
