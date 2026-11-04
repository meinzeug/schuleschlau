# Externe Web-Skripte: Teilprüfung vom 04.11.2026

Die Prüfung betrifft nur den im Repository festgelegten Firebase-Web-Bootstrap.
Er lädt die beiden öffentlichen ES-Module erst nach dem Geräte-Opt-in. Am
04.11.2026 stimmte die SHA-256 von `/push_bootstrap.js` auf der öffentlichen
Installation mit der Datei in Release `69eda38` überein:
`37914c639141e1fd3e6f182bfae6b0f44f5b448c601cc3e4b930ec4bc8db5a47`.
Dieser Vergleich beweist nicht, dass das Opt-in oder die Push-Zustellung auf
einem konkreten Gerät funktioniert.

| Ressource auf `www.gstatic.com/firebasejs/12.19.0/` | Bytes | SHA-256 am Prüftag |
| --- | ---: | --- |
| `firebase-app.js` | 106558 | `39a50952b5def557337b2290069c7d7371f3515ad46c44a43b9c520f734d8d14` |
| `firebase-messaging.js` | 37630 | `7572acc95d2f0182ef70bb16b2920b022340bde54cea5962704c745488e98b23` |

Das versionierte npm-Paket `firebase@12.19.0` nennt `@firebase/app@0.16.2`
und `@firebase/messaging@0.13.3` als direkte Abhängigkeiten und gibt für das
Paket Apache-2.0 an. Die paginierte OSV-Abfrage meldete für diese drei
konkreten Paketversionen am Prüftag keine Einträge. Das ist keine Aussage über
alle transitiven Abhängigkeiten, unbekannte Sicherheitslücken oder die
Übereinstimmung der CDN-Bundles mit den npm-Paketen. Die
[Firebase-Lizenzdatei](https://github.com/firebase/firebase-js-sdk/blob/master/LICENSE)
nennt zusätzliche Lizenzbestandteile; eine vollständige Lizenzprüfung der
Bundles wurde nicht durchgeführt. Laut offiziellen
[Veröffentlichungsnotizen](https://firebase.google.com/support/release-notes/js)
ist 12.19.0 ein konkretes Release; eine Migration auf eine aktuellere Version
wurde weder geprüft noch vorgenommen.

Der wiederholbare, lesende Teil wird aus dem Repository mit
`python3 scripts/audit_firebase_web.py` ausgeführt. Er prüft den festen
Bootstrapumfang, lädt die öffentlichen Module und npm-Metadaten und fragt OSV
für die genannten drei Pakete mit Pagination ab. Bei anderen Bootstrap-URLs,
Netzfehlern, ungültigen Daten, wiederholten OSV-Seitentokens oder Treffern muss
der Betrieb den Grund prüfen; leere oder abgebrochene Abfragen sind kein
Sicherheitsnachweis. Die Hashes sind Bestandswerte und werden nicht im Browser
als Integritätsschutz erzwungen. Die Abfrage enthält keine Kontodaten oder
Lerninhalte. Zuständig für die Wiederholung bei SDK-Updates und mindestens im
Rahmen der regelmäßigen Lieferkettenprüfung ist der Betreiber.

Nicht abgedeckt: die tatsächlich bei autorisiertem Checkout dynamisch
bezogenen und vom jeweiligen Zahlungsanbieter veränderbaren PayPal-/Google-Pay-
Skripte, deren Abhängigkeiten und Lizenzen, weitere Laufzeit-Skripte und
Serviceworker, die nativen Gradle-Transitive, Container und Hostpakete. Diese
müssen gesondert erfasst und bewertet werden. Die Roadmap-Gesamtprüfung der
Lieferkette bleibt daher offen.
