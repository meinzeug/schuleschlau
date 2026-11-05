import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';

import 'fixtures/child_home_encoded.dart';

void main() {
  test(
    'generated browser fixture exactly matches canonical synthetic JSON',
    () {
      expect(
        base64Decode(syntheticChildHomeBase64),
        File('test/fixtures/child_home.json').readAsBytesSync(),
        reason: 'Run scripts/generate_child_home_fixture.py after editing the JSON.',
      );
    },
    skip: kIsWeb
        ? 'Fixture file consistency is checked by the VM test.'
        : false,
  );
}
