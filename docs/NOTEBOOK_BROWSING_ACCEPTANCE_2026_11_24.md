# Hefte: funktionale Abnahme mit künstlichen Daten, 24.11.2026

Der Hefte-Hauptpunkt ist für seine dokumentierten Funktions- und
Berechtigungsfälle abgeschlossen. Die Prüfung betrifft den Quellstand
`7ebf4948f9270a0af1b8b82f016c5a4d4328f7e5` mit den zugehörigen
Teständerungen dieses Commits. Die öffentliche Installation wurde dafür
weder geändert noch als neuer Stand geprüft. Die lokale Webprüfung verwendet
einen Debug-Build, keine Release-APK und keinen laufenden Produktionsserver.

## Browser und gespeicherte Daten

Der versionierte lokale Prüflauf verwendet eine neu angelegte SQLite-Datenbank,
ein temporäres Uploadverzeichnis, ausschließlich künstliche Familien und
Kinder sowie Chrome mit abgeschirmten Netzwerkzielen. Fünf künstliche,
unterschiedlich gestaltete JPEG-Seiten je Kind werden über die Upload-API
angelegt; die künstlichen Transkripte werden für diesen Test lokal vorbereitet
und über die API bestätigt. Ein Worker und externe Anbieter laufen nicht.

Der Browser bedient den Elternzugang bei 390 Pixeln und Kinderzugänge bei
390 und 1280 Pixeln. Er prüft Blättern durch die tatsächlichen Bilder,
Geschwisterschutz, die elterliche Löschvorschau mit verknüpfter Runde und
Antwort, den Schutz bestätigter Kinderseiten und die ausdrückliche Löschung
einer unbestätigten Seite. Ein bewusst abgebrochenes Neueinlesen startet
keinen Auftrag. Einzel- und Mehrseitenstart erzeugen zwei wartende Aufträge;
die isolierte Datenbank bestätigt für jeden Auftrag die ausgewählten eigenen
Quellen und ihre Revisionen. Die Aufträge werden nicht als erzeugte
KI-Lernrunden ausgegeben.

Ein weiteres künstliches Kind besitzt fünf Fotoseiten und 42 synthetische
Textseiten. Im 390-Pixel-Browser wird ein Material-GET gezielt abgebrochen,
der Fehler angezeigt und über „Erneut laden“ wiederhergestellt. Anschließend
wird über die 20-Seiten-Grenze hinaus geblättert und eine Seite gesucht. Die
Testdatenbank und das Browserprotokoll belegen für dieses Kind keine neue
Lernaktivität, keinen zusätzlichen Auftrag und keine zusätzlichen Kosten durch
Blättern, Wiederholen des Leseabrufs oder Suche. Der Zugriff auf ein fremdes
Foto wird abgewiesen. Die Unterbrechung ist ein gezielt abgefangener einzelner
GET, keine allgemeine Offline- oder Dauerstörungsprüfung.

Der Testtreiber bedient die aktuellen mobilen Seitenaktionen als Menüeinträge.
Der Fehlerhaken der Browser-Netzwerksperre kann ausschließlich nach Prüfung
des Loopback-Ursprungs einen Abruf abbrechen; fremde Ziele und Redirects
bleiben gesperrt. Ungültige Hakenantworten und Fehler bei der Bereinigung
lassen den Test fehlschlagen. Synthetische Screenshots und Daten liegen nur
im temporären Testverzeichnis und sind keine Produktionsdaten.

## Ergebnisse

- Der zusammenhängende lokale Browser-Runner bestand mit sechs Fällen ohne
  Skip; er enthält neben dem Hefter auch den bestehenden Lern- und
  Elternkonfliktweg. Die Netzsperre bestand sieben isolierte Vertragsfälle
  und ihre separate Echt-Chrome-Prüfung.
- 102 Flutter-Widgetfälle bestanden für Hefte, Dialoge und Ansichten. Dazu
  gehören 320/390/1280 Pixel, große Schrift, Suche, Filter, Zoom,
  Kontowechsel, Seitensprung und die aktuellen Seitenaktionen.
- Die gezielten Backendprüfungen bestanden auf isoliertem PostgreSQL 16 mit
  111 und weiteren vier Fällen, einschließlich unzugeordneter Seiten,
  Quellenrevisionen, Geschwisterschutz und Sperren. Auf SQLite bestanden
  94 Fälle; 17 PostgreSQL-spezifische Sperrfälle wurden dort ausdrücklich
  übersprungen und durch den PostgreSQL-Lauf abgedeckt.
- Im lokalen Testlauf erschien eine bekannte Deprecation-Warnung des
  FastAPI-Testclients. Ein späterer Release und ein unabhängiger Sicherheits-
  oder Bedienungstest sind damit nicht freigegeben.

## Grenzen und Wiederholung

Die Fotos sind künstliche Layoutseiten, keine repräsentativen Handyfotos.
Der Test führt weder OCR noch eine tatsächliche KI-Generierung oder fachliche
Prüfung aus; diese bleiben in den entsprechenden OCR-, Lernpaket- und
Fachabnahme-Hauptpunkten offen. Auch eine fortgesetzte Nutzung ohne Netzwerk
nach App-Neustart, ein physischer Gerätetest und eine unabhängige Prüfung mit
Kindern werden hier nicht behauptet. Frühere Berichte behalten ihren
historischen Stand; diese Abnahme ergänzt ihre damals noch fehlenden
funktionalen Mehrseiten-, Rechte- und Browsernachweise.

Reproduzierbarer Lauf nach einem passenden lokalen Webbuild und mit den
festgelegten Testabhängigkeiten:

```sh
node --test qa/test_browser_network_guard_unit.mjs
node qa/test_browser_network_guard.mjs
python qa/run_notebook_local_browser.py --web-dir app/build/web --scratch-root /dev/shm
```

Der Runner entfernt ererbte Provider-, Datenbank- und Zugangseinstellungen,
verlangt die getrennte SQLite-Datenbank und überprüft die vollständigen
JUnit-Ergebnisse einschließlich der Schutztests gegen fremde Datenbanken.
