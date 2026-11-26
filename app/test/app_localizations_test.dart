import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/api.dart';
import 'package:schulpilot/brand_startup.dart';
import 'package:schulpilot/main.dart';

void main() {
  for (final deviceLocale in [
    const Locale('de', 'DE'),
    const Locale('en', 'US'),
  ]) {
    testWidgets('App-Systemtexte sind deutsch bei Gerät $deviceLocale', (
      tester,
    ) async {
      tester.platformDispatcher.localeTestValue = deviceLocale;
      addTearDown(tester.platformDispatcher.clearLocaleTestValue);
      await tester.pumpWidget(SchulpilotApp(AppState()));
      await tester.pumpAndSettle();
      final context = tester.element(find.byType(Scaffold).first);
      final material = MaterialLocalizations.of(context);
      expect(Localizations.localeOf(context).languageCode, 'de');
      expect(material.modalBarrierDismissLabel, 'Schließen');
      expect(material.cancelButtonLabel, 'Abbrechen');
      expect(material.remainingTextFieldCharacterCount(5), contains('Noch 5'));
      final semantics = tester.ensureSemantics();
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => const Scaffold(
            body: TextField(
              maxLength: 5,
              decoration: InputDecoration(labelText: 'Deine Antwort'),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.bySemanticsLabel(RegExp(r'Noch 5\s+Zeichen')),
        findsOneWidget,
      );
      semantics.dispose();
      await tester.pumpWidget(const SizedBox());
    });
  }

  testWidgets('Auch die Startansicht nutzt deutsche Systemtexte', (
    tester,
  ) async {
    await tester.pumpWidget(
      BrandStartup(application: (_) => const MaterialApp(home: SizedBox())),
    );
    final context = tester.element(find.byKey(const ValueKey('brand-startup')));
    expect(Localizations.localeOf(context).languageCode, 'de');
    expect(
      MaterialLocalizations.of(context).modalBarrierDismissLabel,
      'Schließen',
    );
    await tester.pumpWidget(const SizedBox());
  });
}
