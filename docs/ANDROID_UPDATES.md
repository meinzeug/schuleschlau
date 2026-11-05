# Android-Updates

Die Download-APK prüft **bei jedem Start und bei jedem erneuten Öffnen aus dem Hintergrund** das öffentliche HTTPS-Release-Manifest. Keine Tagesfrist, keine Anmeldung und keine übermittelte Familienkennung. Eine bereits laufende Prüfung wird gemeinsam verwendet; es gibt keine parallelen Downloads. Fehler verhindern das Lernen nicht. Beim nächsten Öffnen erfolgt eine neue Prüfung.

## Direkte APK

Flavor `direct` lädt eine höhere Version automatisch vom festen Schulpilot-Downloadpfad. HTTPS ohne Weiterleitungen, höchstens 150 MiB, begrenzte Verbindungs-/Lese-/Gesamtdauer. Der Download bleibt im privaten App-Cache. Größe, SHA-256, Paketname, exakter Versionscode, Mindest-Android und derselbe Signierer wie bei der installierten App werden geprüft. Kein Downgrade, kein beliebiger Downloadpfad, kein Zugriff auf Account-Tokens. Abgebrochene Dateien werden verworfen; eine schon vollständig geprüfte Datei kann beim nächsten Start erneut geprüft und verwendet werden.

Nach erfolgreicher Prüfung wird die APK an Androids Installationsoberfläche übergeben. Ab Android 8 muss das Betriebssystem gegebenenfalls einmalig die Installation aus dieser App erlauben. Danach bestätigt der Nutzer das Update. Keine stille Installation und keine Erweiterung der Geräteverwaltung. Ablehnung und „Später“ bleiben möglich; die Lernfolge bleibt serverseitig gespeichert. Ein erneuter Start prüft den Server wieder. Erst der tatsächliche neue Versionscode belegt eine erfolgreiche Installation.

Nur der direkte Flavor enthält `REQUEST_INSTALL_PACKAGES` und den nicht exportierten, auf den Update-Cache beschränkten `FileProvider`. Diese reguläre Direct-APK wird über die Website verteilt.

## Google Play

Flavor `play` enthält weder die APK-Installationsberechtigung noch den direkten Download-/Installationscode. Er prüft bei jedem Start mit Googles `app-update:2.1.0` und verwendet die offizielle unmittelbare In-App-Aktualisierung. Eine begonnene Play-Aktualisierung wird wieder aufgenommen. Auch hier bleibt die Systembestätigung maßgeblich.

Ohne berechtigtes Play-Projekt, veröffentlichte Version und eine über Play installierte Testversion kann keine echte Play-Updatezustellung geprüft werden. Das gebaute AAB allein beweist diese Zustellung nicht. Play-App-Signing und direkte APKs können unterschiedliche Signierer haben; die Verteilungswege nicht durch eine unsignierte oder anders signierte APK vermischen.

## Reproduzierbarer Build

```bash
scripts/build_release.sh
```

Das Skript prüft die fixierte Toolchain und den Quellstand und erzeugt `artifacts/schulpilot-android.apk`, `artifacts/schulpilot-play.aab` und den zugehörigen Release-Nachweis. `scripts/android_manifest.py` berechnet das öffentliche Manifest aus der tatsächlichen Direct-APK. Für jedes neue Update den Versionscode erhöhen. Private Signierschlüssel unverändert außerhalb des Repositorys halten.

## Tatsächliche Prüfung

Der native Prüftreiber `qa/android_update.py` verwendet ausschließlich den eigenen Emulator und zwei tatsächlich signierte Versionen. Er prüft neue Startabrufe und den echten Installationsdialog samt Versionswechsel. `--check-starts` prüft auf der installierten aktuellen Version Kaltstart, Hintergrundrückkehr und einen weiteren Launcher-Aufruf. Ergebnis und verbleibende Grenzen in [STATUS.md](STATUS.md).

Für die lokale Negativprüfung installiert `qa/android_update_validation.py` ausschließlich eine gesonderte Debug-App mit der Kennung `de.dorfspy.schulpilot.updateprobe` und ihre Instrumentierung auf einem ausdrücklich angegebenen Emulator. Sie erstellt künstliche APKs und prüft die native Direct-Validierung für passende Dateien und Abweichungen bei Größe, Hash, Paket, Signatur, Version und Mindest-Android. Die Übergabe an den Installer wird in einer Test-Activity abgefangen; hierdurch wird keine Installation ausgelöst. Beide Testpakete werden anschließend entfernt. Die Prüfung benötigt die bereits lokal vorbereitete, fixierte Flutter-/Android-Toolchain:

```bash
cd app
flutter pub get --offline --enforce-lockfile
cd android
./gradlew --offline assembleDirectDebug assembleDirectDebugAndroidTest -PsyntheticUpdateProbe
cd ../..
python3 qa/android_update_validation.py --serial emulator-5580 \
  --app app/build/app/outputs/apk/direct/debug/app-direct-debug.apk \
  --test app/build/app/outputs/apk/androidTest/direct/debug/app-direct-debug-androidTest.apk
```

Der separate Lesetest `qa/android_play_update_evidence.py --release-root <Release-Checkout>` verifiziert den signierten Release-Nachweis, das Play-Bundle, sein Manifest und Anhaltspunkte für den Play-Updatepfad im zugehörigen R8-Mapping und DEX. Das Mapping ist nicht selbst Teil des signierten Nachweises. Die Prüfung ersetzt weder einen Play-Upload noch einen tatsächlichen über Google Play ausgelieferten Updatevorgang.
