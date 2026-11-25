# Reproduzierbare 30-Schultage-Regression

Der neue Lauf verwendet ausschließlich eine automatisch isolierte Testfamilie,
lokal erzeugte künstliche Fotos und fest programmierte Providerantworten. Er
setzt weder die Systemzeit noch Produktionsdaten. Die beiden Testquellen sind
die vorhandenen künstlichen Szenen zu Geographie und Geschichte; sie sind
keine Abdeckung eines vollständigen Lehrplans.

Für 30 getrennte Wochentage wird je ein eigenes Foto über die API hochgeladen,
die zweistufige Erkennung und eine ausdrücklich gestartete Paketvorbereitung
werden über den regulären Worker verarbeitet und eine gespeicherte Runde wird
beantwortet. Jede zweite Runde nutzt einen Hinweis; jede fünfte enthält eine
bewusst unbekannte Antwort, die unklar bleiben muss. Ein doppelter Upload wird
mit demselben Schlüssel wiederholt. Zwei getrennt angemeldete Gerätesitzungen
lesen den gespeicherten Stand. Der separate Rückblickauftrag wird regulär
abgeschlossen. Für einen Rückblick sind die simulierten Kosten unbekannt;
alle anderen Testpreise sind künstlich gemeldete Werte, keine Echtgeldbeträge.

Der Test stellt die Tages-, Sitzungs-, Auftrags- und gespeicherten
Antwortzeitpunkte sowie die Ratenfenster innerhalb des Testprozesses um; zwei
Anmeldungen werden an jedem Testtag erneuert. Ein Lernpausentag und ein
ausgelassener Tag erzeugen bei der lesenden Abfrage keinen neuen Auftrag. Die
globale Provider-Monatszuordnung verwendet noch die Systemuhr des Testhosts;
der Lauf belegt daher keinen vollständigen Monatswechsel aller Kostenbudgets.
Auch tatsächliche Lernzeit, langfristige Lernwirkung und echte OCR werden
nicht simuliert oder als bestanden ausgegeben.

Zusätzlich laufen bestehende künstliche Fälle für Fehler und bewusste
Wiederholung, eine geänderte Quelle, Unterbrechung, Mitternacht, Nachholen,
freiwilliges Lernen an einem freien Tag und Entwürfe auf zwei Geräten. Diese
Fälle sind separate Regressionen; sie wurden nicht als 30-mal tatsächlich
erlebte Netzwerk- oder Gerätetests ausgegeben.

Der Runner startet nur die explizit genannten Tests mit bereinigter Umgebung,
isolierter Datenbank und ohne übernommene Anbieterzugänge. Der Monatsfall
sperrt Python-Netzwerkverbindungen zusätzlich während des künstlichen Laufs.
Ein JUnit-Abgleich lehnt ausgelassene, doppelte oder fehlgeschlagene Fälle ab.
Der Tagesbericht enthält nur künstliche Kennungen, Quellenrevisionen,
Planumfang, Auftragsstatus und Kostenarten sowie Ergebnis-/Hilfestatus. Seine
30 Tage, 120 unterschiedlichen Aufträge, beide Fächer, ein unbekannter Betrag
und der Fingerabdruck der Testdatei werden geprüft. Das Prüftor kann so
wiederholt werden:

```sh
python qa/run_month_regression.py --database postgresql
python qa/run_month_regression.py --database sqlite
python -m pytest -q qa/test_run_month_regression.py
```

Die Runner geben den Pfad zum erzeugten synthetischen JSON-Bericht und zum
JUnit-Ergebnis in einem neuen temporären Verzeichnis aus. PostgreSQL benötigt
lokale PostgreSQL-Werkzeuge; eine separate Testinstanz wird gestartet und
wieder entfernt. Es gibt keine Provideraufrufe oder echten Kinderkonten.

**Ausführung am 25.11.2026:** Das PostgreSQL- und das SQLite-Prüftor bestanden
jeweils alle elf ausgeführten Fälle. Der [synthetische Tagesbericht](evidence/month-regression-2026-11-25-postgresql.json)
enthält 30 Tage, 30 Quellen und Runden, 60 gespeicherte Antworten und 120
Aufträge. Die beiden Fächer sind je 15-mal vertreten; ein Auftrag behält
unbekannte Kosten. Der Bericht nennt den SHA-256-Fingerabdruck der
Testdatei. Neun separate Prüfungen des Auswertungswerkzeugs bestanden; sie
prüfen unter anderem, dass keine der beiden Mitternachtsvarianten fehlt.
Ein lokaler JavaScript-Webbuild für die anschließende Browserprüfung war
erfolgreich. Der gesonderte Wasm-Trockenlauf meldete Inkompatibilitäten in
`flutter_tts`; er gilt nicht als bestandener Wasm-Build.

Die Anwendung für den Test stammt vom Ausgangsstand `bd24e9a`, ohne Änderungen
an Anwendungscode oder Laufzeitkonfiguration. Der Webbuild verwendete Flutter
3.47.7/Dart 3.13.5; die lokale Browserautomatisierung verwendete Chrome
156.0.8078.47, Node 22.23.1 und Python 3.12.3. Das Prüfszenario und seine
Konfiguration liegen versioniert im Repository; der Tagesbericht enthält
zusätzlich den Fingerabdruck der ausführenden Backend-Testdatei.

## Noch nicht abgenommen

Der API-Lauf bedient die regulären HTTP-Schnittstellen über `TestClient`. Ein
zusätzlicher mobiler Browserlauf mit künstlichen Providerantworten wurde auf
Nutzerwunsch nach 28 abgeschlossenen Tagen angehalten; er ist keine vollständige
30-Tage-Abnahme. Vorherige Versuche scheiterten an instabilen Fokus- und
Tabwechseln im Testtreiber. Der Nutzer verlangt stattdessen einen erneuten
Alltagstest mit echten, regulär reservierten KI-Aufrufen im Browser und dem
Konto von Juna Fee. Unterschiedliche reale Schulthemen, echte Anbieterergebnisse,
Elternnoten und eine vollständige Lernstandswirkung sind durch den hier
dokumentierten API-Lauf nicht belegt. Deshalb bleibt der Hauptpunkt offen.
