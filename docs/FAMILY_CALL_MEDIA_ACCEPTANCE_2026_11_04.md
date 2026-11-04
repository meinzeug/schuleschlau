# Familienanrufe und externe Lerntipps: Abnahme vom 4. November 2026

## Umfang und Nachweisgrenzen

Diese Prüfung betrifft die in der bestehenden Anwendung optionalen
Familienanrufe und die in der App verlinkten Sofatutor-Lerntipps. Sie ersetzt
keine eigenständige Prüfung auf einem physischen Telefon. Neue Tests nutzen
ausschließlich künstliche Konten und Inhalte; sie rufen keinen KI-Anbieter auf.
Mock-Medien und simulierte Netzwerkantworten belegen keine echte Übertragung.
Nach [RELEASE_SCOPE.md](RELEASE_SCOPE.md) sind Familienanrufe nicht automatisch
Bestandteil einer gewählten Startstufe; eine Aufnahme in einen bestimmten
Freigabeumfang bleibt eine separate Betreiberentscheidung.

Der aktuelle Teststand ist Commit `1559d967db35d71f57972df9de469dd2f982c1c0`.
Seit der dokumentierten Echtprüfung vom 22. Oktober blieb das
Server-Anrufmodul unverändert; die Flutter-Oberfläche und die Lerntipps wurden
dagegen nachträglich überarbeitet. Der historische Medienbeleg und die neuen
automatisierten Prüfungen sind deshalb getrennt zu lesen.

## Aktuelle automatisierte Prüfung

Fünf Backend-Testmodule für Anrufrechte, Migration, Lerntipps und den
versionierten Katalog bestanden mit **69 Fällen auf SQLite**. Vier Fälle,
darunter PostgreSQL-Sperrrennen und PostgreSQL-Migrationen, wurden in diesem
Lauf übersprungen. Auf dem isolierten PostgreSQL-16-Cluster bestanden dieselben
Module mit **73 Fällen ohne Auslassung**. Acht Flutter-Testdateien bestanden
mit **83 Fällen**; vier davon bestanden zusätzlich mit **35 Fällen im
Chrome-Webrunner**. Nach dessen Erfolg musste das Framework den eigenen
Testbrowser beim Schließen nach erfolglosem SIGTERM mit SIGKILL beenden.

Die reproduzierbaren Aufrufe aus dem Repositorywurzelverzeichnis sind:

```sh
TMPDIR=/dev/shm PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_family_calls.py backend/tests/test_family_call_migration.py backend/tests/test_learning_tips.py backend/tests/test_catalog_ai.py backend/tests/test_catalog_migration.py
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_family_calls.py backend/tests/test_family_call_migration.py backend/tests/test_learning_tips.py backend/tests/test_catalog_ai.py backend/tests/test_catalog_migration.py
cd app
flutter test test/family_call_navigation_test.dart test/family_call_test.dart test/family_call_continuity_ux88_test.dart test/family_call_dock_test.dart test/family_call_media_test.dart test/family_call_native_test.dart test/learning_tips_test.dart test/learning_tips_return_test.dart
flutter test --platform chrome test/family_call_navigation_test.dart test/family_call_continuity_ux88_test.dart test/learning_tips_return_test.dart test/learning_tips_test.dart
```

Die lokale virtuelle Umgebung und Flutter 3.47.7 müssen jeweils vorhanden sein;
`/dev/shm` ist ein optionales temporäres Dateisystem und keine Produktivdatenbank.

Die Backendfälle prüfen unter anderem eigene und fremde Familien, Admins,
geräte-/sitzungsgebundene Annahme, ausdrücklichen Widerruf, konkurrierende
Annahmen, Abschalten, begrenzte Signalisierung sowie Katalogherkunft,
Zugriffsgrenzen und idempotentes Linköffnen. Die Flutterfälle prüfen getrennte
Start-, Annahme- und Bildschirmfreigaben, abgelehnte Berechtigungen,
Netzausfälle, Kontowechsel, die Fortführung von Aufgabe und Entwurf und die
Rückkehr aus Lerntipps bei 320 Pixeln und großer Schrift. Ein Medienaufruf
erzeugt allein weder einen Versuch noch einen Kompetenz- oder Zeitnachweis.

Die Katalogimporte und der Flutter-Launcher erlauben nur die festen
HTTPS-Sofatutor-Hosts; die App hängt keine private Aufgabe oder Familienkennung
an die Katalogadresse. Am 4. November lieferte die produktive Startseite bei
einem lesenden HTTPS-Aufruf `Referrer-Policy: no-referrer`. Der fixierte
Weblauncher verwendet zusätzlich `noopener,noreferrer`. Das ist ein Header-
und Codebeleg, kein erneuter beobachteter Aufruf einer externen Zielseite.

## Frühere echte Medien- und Browserprüfung

Die separat dokumentierte [Abnahme vom 21.–22. Oktober](FAMILY_CALL_EVALUATION_2026_10_21.md)
verwendete künstliche Konten, einen ausdrücklich erzwungenen TURN-Relay und
einen Android-36-Emulator. Sie beobachtete Kamera, Bildschirm, Audio und
geregeltes Gesprächsende; die heutigen Tests beweisen keine neue physische
Geräteübertragung. Der lokale historische Beleg
`artifacts/family-call83/live-parent-result.json` meldet synthetische Daten,
Relay, empfangene Kamera-/Bildschirm- und Audioframes sowie Erfolg; der
historische Bereinigungsbeleg meldet Kontolöschung und widerrufene Sitzung.
Diese nicht zum Repository gehörenden Artefakte wurden nur auf die genannten
Metadaten geprüft und nicht neu erzeugt.

Der in [CATALOG_INTEGRATION.md](CATALOG_INTEGRATION.md) dokumentierte frühere
öffentliche Browsertest auf `f04539fd5d959b7a5b082dacb1573a8d907b5379`
öffnete einen gespeicherten Kataloglink ohne Referrer; sein lokaler Ergebnisbeleg
meldet Erfolg und null erfundene Attempts. Er belegt das damalige Release,
nicht eine heutige Videowiedergabe oder einen heutigen Login bei Sofatutor.
