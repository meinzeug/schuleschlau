import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../qa/schulbuddy_device_main.dart' as fixture;

void main() {
  testWidgets('offline device fixture opens its synthetic buddy', (
    tester,
  ) async {
    fixture.main();
    await tester.pumpAndSettle();
    expect(find.text('Künstlicher Gerätetest'), findsOneWidget);
    await tester.tap(find.text('Schulbuddy öffnen'));
    await tester.pumpAndSettle();
    expect(find.text('Gespräch: Künstlicher Test'), findsOneWidget);
    expect(find.byType(TextField), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
