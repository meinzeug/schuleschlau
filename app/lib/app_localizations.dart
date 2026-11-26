import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

// The product interface is currently German. Language-learning prompts and
// speech locales remain explicitly selected by their individual activities.
const supportedAppLocales = [Locale('de')];
const appLocalizationDelegates = [
  GlobalMaterialLocalizations.delegate,
  GlobalWidgetsLocalizations.delegate,
  GlobalCupertinoLocalizations.delegate,
];
