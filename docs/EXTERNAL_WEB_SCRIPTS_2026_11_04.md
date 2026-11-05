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

Die [OSV-Abfrage](https://google.github.io/osv.dev/post-v1-query/) darf bei
null Treffern ein leeres Objekt und bei einer zeitlich begrenzten Seite nur
einen Fortsetzungstoken liefern. Der Prüfer akzeptiert diese Fälle, verwirft
aber fehlerhafte Ergebnisobjekte, IDs und Seitentokens und begrenzt die
Paginierung auf 500 Seiten. Ein Fehlerobjekt mit HTTP 200 wird damit nicht als
trefferfreie Abfrage ausgegeben. Eine leere, formal gültige Antwort allein
beweist weiterhin weder die Verfügbarkeit aller Datenquellen noch eine
vollständige Sicherheitsprüfung.

Nicht abgedeckt: die tatsächlich bei autorisiertem Checkout dynamisch
bezogenen und vom jeweiligen Zahlungsanbieter veränderbaren PayPal-/Google-Pay-
Skripte, deren Abhängigkeiten und Lizenzen, weitere Laufzeit-Skripte und
Serviceworker, die nativen Gradle-Transitive, Container und Hostpakete. Diese
müssen gesondert erfasst und bewertet werden. Die Roadmap-Gesamtprüfung der
Lieferkette bleibt daher offen.

## Ergänzung: npm-Auflösung von App und Messaging

Die neun in einem gesonderten npm-Lock aufgelösten direkten und transitiven
Pakete von `@firebase/app@0.16.2` und `@firebase/messaging@0.13.3` sind unter
[`dependency-inventory/firebase-npm-20261104`](dependency-inventory/firebase-npm-20261104/)
mit Lock, Paketwurzeln und [Abfrageergebnis](dependency-inventory/firebase-npm-20261104/audit.json)
erfasst. Der Lock wurde mit npm 10.9.8 ohne Installationsskripte aufgelöst;
die festgeschriebene Auflösung wird anschließend von `npm ls` offline geprüft.
Bei der Abfrage am 04.11.2026 meldete OSV keine Treffer für die neun
konkreten Versionen; die Registermetadaten nennen für sieben Pakete Apache-2.0,
für `idb` ISC und für `tslib` 0BSD. Dies sind Lizenzkennungen aus Metadaten,
keine rechtliche Bewertung oder vollständige Prüfung von Lizenztexten und
Weitergabepflichten. `firebase@12.19.0` selbst wird zusätzlich geprüft.

Wiederholung: `python3 scripts/audit_firebase_npm_tree.py`. Das Skript prüft
den im Bootstrap gewählten Umfang, den Lock, npm-Auflösung, Versions-,
Lizenz- und Integritätsangaben der Registry und OSV mit Pagination. Es
installiert keine Pakete und führt keine Paketinstallationsskripte aus. Die
Lizenz- und Integritätsangaben werden miteinander verglichen. Am 04.11. wurden
Paketarchive noch nicht heruntergeladen oder gehasht; siehe die Ergänzung vom
05.11. unten. Änderungen am SDK erfordern
einen neu geprüften Lock. Das npm-Ergebnis kann sich durch neue Meldungen
ändern und ist kein Nachweis für noch unbekannte Schwachstellen.

Entscheidend: Der npm-Lock beschreibt eine Auflösung am Prüftag und belegt
nicht, welche Versionen in den tatsächlich von Google ausgelieferten
CDN-Dateien gebündelt sind. Insbesondere ein mittels Versionsbereich
aufgelöstes Paket wie `tslib` kann im CDN von diesem Lock abweichen. Die
gesonderte Bestandserfassung der CDN-Dateien und die ungeprüfte
Bundlezuordnung bleiben bestehen.

## Ergänzung 05.11.: Archivprüfung der aufgelösten npm-Pakete

Die neun im vorhandenen Lock aufgelösten Paketarchive wurden direkt von den
festgelegten Registry-URLs geladen und ihre tatsächlichen Bytes mit dem jeweils
gesperrten SHA-512-Wert verglichen. Alle neun stimmten überein; die erneute
OSV-Abfrage meldete am Prüfzeitpunkt keine Kennungen für die konkreten neun
Versionen und die drei zuvor gesondert erfassten Wurzelpakete. Der datierte
[Prüfbeleg](dependency-inventory/firebase-npm-20261104/archive-audit-20261105.json)
enthält Größen, Integritätswerte und die zeitgebundenen Abfrageergebnisse.

Das Prüfwerkzeug lädt für jedes Paket nur die exakt im Lock und in der
Registry-Metadatei übereinstimmende HTTPS-URL auf `registry.npmjs.org`, folgt
bei den Archiven keinen Weiterleitungen und begrenzt die Antwortgröße auf vier
Megabyte. Fehlende, veränderte, übergroße oder falsch kodierte Archive führen
zum Fehler. Archive werden weder entpackt noch installiert oder ausgeführt;
auch npm-Installationsskripte werden nicht gestartet. Der lokale Offline-Test
prüft Integritätsfehler und unerwartete URLs. Eine erneute Kontrolle verwendet
`python3 scripts/audit_firebase_npm_tree.py`.

Der überprüfte Lock ist weiterhin lediglich eine bestimmte npm-Auflösung. Die
Verwendung dieser Paketarchive in Googles CDN-Dateien, die Vollständigkeit der
Lizenzpflichten und unbekannte Sicherheitslücken sind dadurch nicht belegt.
Das Ergebnis ist keine Signaturprüfung einer unabhängigen Vertrauensstelle;
der Lock und seine Herkunft müssen selbst geprüft und geschützt werden.

## Ergänzung 05.11.: Hintergrund-Serviceworker und Compat-Pakete

Die bisherige Untersuchung erfasste die beiden vom Webbootstrap importierten
Module, **nicht aber** die beiden Compat-Skripte, die der Hintergrund-Push-
Serviceworker aus `backend/schulpilot/notifications.py` über `importScripts`
lädt. Der öffentliche Endpunkt `/push/firebase-messaging-sw.js` lieferte bei
einer lesenden Prüfung am 05.11.2026 tatsächlich die beiden nachfolgenden
Imports aus `www.gstatic.com/firebasejs/12.19.0/`; die Konfiguration wurde dabei
nicht ausgegeben. Die vier CDN-Dateien lieferten bei der Abfrage:

| Datei | Bytes | SHA-256 |
| --- | ---: | --- |
| `firebase-app.js` | 106558 | `39a50952b5def557337b2290069c7d7371f3515ad46c44a43b9c520f734d8d14` |
| `firebase-messaging.js` | 37630 | `7572acc95d2f0182ef70bb16b2920b022340bde54cea5962704c745488e98b23` |
| `firebase-app-compat.js` | 32037 | `11354507ecdd4a0f56f989800ccc8925baf120864d0b8fdd9c372e4c7ec059a6` |
| `firebase-messaging-compat.js` | 49432 | `0bc50d63f0642d99c974ff0e02c3f5fff88e6665edca545c61c77d18cb62c427` |

Der ergänzte Prüfer erfasst die fest vorgegebenen Modul- und Workerimporte;
bei abweichender Anzahl oder Zieladresse bricht er vor der Netzwerkabfrage ab.
Die Auflösung der vier npm-Wurzeln `@firebase/app@0.16.2`,
`@firebase/messaging@0.13.3`, `@firebase/app-compat@0.5.18` und
`@firebase/messaging-compat@0.2.30` ist in einem
[separaten Lock](dependency-inventory/firebase-npm-compat-20261105/package-lock.json)
festgehalten; der historische Lock bleibt unverändert. Mit npm 10.9.8 wurde
der Lock ohne Installationsskripte erstellt und offline geprüft. Alle elf
aufgelösten Paketarchive wurden gegen die SHA-512-Werte des Locks geprüft;
die paginierte OSV-Abfrage meldete zum Prüfzeitpunkt 05.11.2026,
11:27:51 UTC, für diese elf Versionen und das separate `firebase@12.19.0`
keine Kennungen. Der [Prüfbeleg](dependency-inventory/firebase-npm-compat-20261105/audit.json)
enthält die Einzelwerte und ist mit `python3 scripts/audit_firebase_npm_tree.py`
erneut erstellbar. Er enthält weder Konten noch Lerninhalte.

Die Importscopeprüfung liest statische Quelltexte; sie ist keine vollständige
JavaScript-Ausführungs- oder Transitivitätsanalyse. Die CDN-Hashes sind
Bestandswerte und werden zur Laufzeit nicht als Integritätsprüfung erzwungen.
Die Paketauflösung belegt nicht die Identität mit Googles CDN-Bundles; auch
Signaturen, unbekannte Lücken, die vollständigen Lizenzpflichten, weitere
Webskripte und die übrige Lieferkette bleiben offen. Der lesende Endpunktcheck
belegt keine Push-Zustellung.
