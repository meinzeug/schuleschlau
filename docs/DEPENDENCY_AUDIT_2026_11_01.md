# Abhängigkeitsprüfung · 01.11.2026

Dieser Bericht beschreibt den technisch geprüften Stand und keine allgemeine
Sicherheits- oder Lizenzfreigabe. Produktion und Entwicklung können bis zum
nächsten tatsächlich aktivierten Release unterschiedliche Versionen verwenden.

## Sicherheitsabfrage

Die festgeschriebenen Versionen wurden am 01.11.2026 mit der
[OSV-Batch-API](https://google.github.io/osv.dev/post-v1-querybatch/)
gegen bekannte Meldungen geprüft. Abgefragt wurden 40 Python-Pakete aus dem
Backend-Lock und 122 gehostete Pub-Pakete; außerdem die Versionen des
Entwicklungs- und Codex-Worker-Locks, das QA-npm-Lock sowie das explizit
geladene Firebase-JS-Paket. Die zweite Abfrage enthält Überschneidungen mit der
ersten. Antwortanzahl und Pagination wurden kontrolliert. Gradle-Transitive,
Container-Basisimages, Systempakete und die tatsächliche CDN-Auslieferung sind
darin **nicht** vollständig enthalten; OSV meldet zudem nur dort erfasste Fälle.

Vier Python-Versionen des vorherigen Releases hatten OSV-Treffer:

| Paket | Alt → Kandidat | Beispiel für einen Treffer / Anlass |
| --- | --- | --- |
| certifi | 2026.7.22 → 2026.10.23 | [GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2): betroffene Zertifikatsstellen im Bundle |
| Pillow | 12.3.0 → 13.0.0 | [GHSA-22hg-r758-rrw9](https://github.com/advisories/GHSA-22hg-r758-rrw9): mögliche Endlosschleife bei bestimmten Bilddateien; weitere Einträge vorhanden |
| pyasn1 | 0.6.4 → 0.6.5 | [GHSA-2qm8-x737-gmw5](https://github.com/advisories/GHSA-2qm8-x737-gmw5): übermäßige Rechenzeit bei bestimmten ASN.1-Daten |
| pypdf | 6.21.1 → 6.21.4 | [GHSA-42gh-23hr-vphw](https://github.com/advisories/GHSA-42gh-23hr-vphw): hoher Zeitbedarf bei bestimmten PDF-Daten; weitere Einträge vorhanden |

Für die Kandidaten und die übrigen abgefragten Versionen ergab die erneute
OSV-Abfrage keinen Treffer. Daraus folgt weder die tatsächliche Ausnutzbarkeit
jeder alten Meldung in SchuleSchlau noch die Freiheit von unbekannten Fehlern.
Der PDF-Import bleibt lokal, dateigrößen- und laufzeitbegrenzt. Die Anwendung
verwendet weiterhin ihre existierenden Upload-, Rechte- und Anbietergrenzen.
`certifi` ist auch im Codex-Worker-Lock aktualisiert; ein bereits gebautes
Worker-Containerimage ändert sich dadurch nicht von selbst.

Die Kandidaten wurden in einer getrennten Python-3.12-Umgebung aus dem
aktualisierten Entwicklungs-Lock installiert; `pip check` meldete keine
Konflikte. Mit künstlichen Daten bestanden 230 SQLite-Fälle (fünf nur für
PostgreSQL übersprungen) und dieselben 235 Fälle auf isoliertem PostgreSQL 16.
Sie umfassen unter anderem Fuxnoten-PDFs, Foto-/Profilbildimport, Heftseiten,
Klassenarbeitsfotos und Google-Anmeldung. Weitere 98 Codex-Adapter- und
Workerfälle bestanden; eine getrennte Installation des Worker-Locks war
ebenfalls konfliktfrei. TLS-GETs an Google und OpenRouter gelangen mit dem
neuen Zertifikatsspeicher. Die Prüfungen verwenden keine echten Kinderbilder
und belegen weder eine erfolgreiche echte KI-Anfrage noch einen Gerätetest.

**Auslieferung:** Release `1.38.58+213` aus Commit `40649e8` ist aktiv.
Die vier Versionen wurden in der produktiven Backend-Umgebung nachgeschlagen;
der gesondert neu gebaute Codex-Container enthält ebenfalls certifi
2026.10.23. Sein Buildfingerprint und die Lockdatei stimmen mit dem aktiven
Release überein. Die vollständige [CI für den Releasecommit](https://github.com/meinzeug/schulpilot/actions/runs/41292493190)
bestand. Zusätzlich bestanden jeweils 157 künstliche Fälle zu Kostengrenzen,
Erklärung und Grafiktransport auf SQLite und isoliertem PostgreSQL; die später
ergänzte engere Kostengrenze bestand mit je zwölf Fällen auf beiden Datenbanken.
Web, signierte APK und Play-Bundle wurden quellgebunden gebaut. Die tatsächlich
heruntergeladene APK stimmt in Version, Größe und Hash mit dem öffentlichen
Manifest überein. Es wurde kein physischer Androidtest durchgeführt.

## Bekannte Toolchainhinweise

- Der reguläre JavaScript-Webbuild gelingt. Die automatische Wasm-Trockenprobe
  meldet JS-Interop-Casts in `flutter_tts` 4.2.5. Das ist kein getesteter
  Wasm-Build. Flutter beschreibt die [Wasm-Trockenprüfung und Migration](https://docs.flutter.dev/platform-integration/web/wasm).
  Vor einem Wasm-Angebot Plugin-Kompatibilität und Sprachfunktionen praktisch
  prüfen; bis dahin bleibt JavaScript der freigegebene Webpfad.
- AGP 9.1 und Flutter 3.47 verwenden derzeit den dokumentierten Übergangsweg
  mit `android.builtInKotlin=false`. Laut [Flutter-Migrationsanleitung](https://docs.flutter.dev/release/breaking-changes/migrate-to-built-in-kotlin)
  muss nach Migration aller beteiligten Plugins auf eingebautes Kotlin
  umgestellt werden. Der Android-Releasebuild meldete den bisherigen
  Kotlin-Gradle-Plugin-Weg für `firebase_core`, `flutter_tts` und
  `flutter_webrtc`. Kein ungeprüfter Plugin- oder Gradle-Wechsel in diesem
  Update; vor Entfernung des Übergangswegs getrennt bauen und testen.
- Starlette meldet für Tests mit `httpx` eine Deprecation; laut
  [TestClient-Dokumentation](https://www.starlette.io/testclient/) ist
  `httpx2` der vorgesehene Ersatz. Die Warnung betrifft den Testclient und ist
  kein Beleg für einen Fehler produktiver HTTP-Aufrufe. Ersatz getrennt mit
  den Testfixtures und Sperr-/Parallelitätsfällen prüfen.

Paketmetadaten von PyPI nennen für die vier Kandidaten MPL-2.0 (certifi),
MIT-CMU (Pillow), BSD-2-Clause (pyasn1) und BSD-3-Clause (pypdf). Dies ist
eine Metadatenaufnahme, keine unabhängige Lizenzprüfung der gesamten Lieferkette.
Nächste Sichtung der genannten Warnungen und Sicherheitsstände spätestens am
01.12.2026 oder früher bei einem Toolchain-/Sicherheitsupdate; sie wird nicht
automatisch ausgeführt.
