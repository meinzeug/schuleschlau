# Paketfehler und Wiederaufnahme: Abnahme vom 24.11.2026

Diese Abnahme betrifft die Begrenzung und Behandlung der ausdrücklich
aufgeführten Ausgabefehler und Providerstörungen. Sie bescheinigt keine
fehlerfreie KI, keine vollständige Abdeckung aller denkbaren Fehler und keine
pädagogische oder fotografische Qualitätsabnahme.

## Mehrteilige Pakete und Fehlermatrix

Der reguläre Paketworker verarbeitet sieben künstliche bestätigte Quellen in
drei getrennt reservierten Teilen. Die isolierte Matrix nutzt den echten
OpenRouter-Adapter mit lokalem künstlichem HTTP-Transport. Sie umfasst unter
anderem HTTP 400 einschließlich Schemakonflikt, 408, 429, 500, 503 und 504,
Netz- und Lesetimeout, eingebettete Fehler, fehlende Auswahl, nichttextuellen
Inhalt, ungültige Hüllen und Schemata sowie `finish_reason=length`.

Der erste validierte Teil und ein künstlicher früherer Antwortbeleg bleiben
bei einem Fehler des zweiten Teils erhalten. Fehler mit gemeldeten Kosten
werden einmal gebucht; bei unbekannten Kosten bleibt die konservative
Reservierung bestehen. Weder wiederholtes Lesen noch Workerläufe starten den
fehlgeschlagenen Teil automatisch erneut. Nach einem ausdrücklichen neuen
Start wird der fehlende Teil verarbeitet und das Paket anschließend mit den
ursprünglichen Quellenrevisionen veröffentlicht. Die Tests prüfen zugleich,
dass künstliche Anbieterfehlertexte nicht in Fehlerstatus oder Telemetrie
übernommen werden. Weitere unbekannte Transportformen und irreführende
formatgültige Anbieterkennungen sind damit nicht ausgeschlossen.

Separat prüfen 108 künstliche Transport-, Partitionierungs- und Ausgabe-
Schemafälle unter anderem mehrere Fachgruppen und Quellen mit insgesamt
11.641 Zeichen. Die jeweilige festgelegte Route, Token- und
Reservierungsgrenze bleibt bestehen; ein Fehler löst keinen automatischen
Providerwechsel aus.

## Tatsächlicher Prozessabbruch

`backend/tests/test_package_worker_process_restart.py` verwendet einen
kurzlebigen isolierten PostgreSQL-16-Cluster und ausschließlich künstliche
Daten. Ein echter separater Workerprozess beansprucht den zweiten Paketanteil
und erreicht einen simulierten, lokal blockierten Anbietertransport. Der Test
beendet diesen Prozess mit `SIGKILL`; es wird keine Netzverbindung zu einem
Anbieter aufgebaut. Für die danach ausgeführte normale Wartung wird nur der
Startzeitpunkt des künstlichen Auftrags so gesetzt, dass die reguläre
Zeitüberschreitung bereits eingetreten ist. Die Systemuhr bleibt unverändert.

Der Reaper markiert den Auftrag als unterbrochen. Sein unbekannter Verbrauch
bleibt einmalig reserviert, der erste Teil und eine frühere Antwort bleiben
unverändert. Mehrfache Statusabfragen und Wartung erzeugen keinen neuen
Auftrag. Erst eine ausdrückliche Wiederaufnahme startet den fehlenden Teil;
zwei neue separate Workerprozesse verarbeiten die Teile zwei und drei mit
künstlichen Providerantworten. Die drei gespeicherten Einheiten und alle sieben
Quellenrevisionen werden abschließend geprüft. Der abgebrochene Auftrag und
seine unbekannte Abrechnung bleiben erhalten. Dies simuliert einen
Prozessabsturz, keinen Hostausfall und keine tatsächliche Anbieterrechnung.

Der Neustarttest ist im PostgreSQL-CI-Gate und dessen JUnit-Prüfvertrag
verankert: ein fehlender, doppelter, fehlgeschlagener oder übersprungener Fall
kann den Gate-Nachweis nicht erfüllen.

## Echte künstliche Anbieterläufe

Die [dokumentierten OpenRouter-Läufe vom 23.11.2026](PACKAGE_FRACTION_MIXED_2026_11_23.md)
verwendeten getrennte künstliche Testkonten. In einem frischen Ablauf wurden
zwei künstliche Mathematikfotos regulär hochgeladen, erkannt und gegengeprüft;
das Paket entstand beim ersten Versuch. Drei Runden mit insgesamt sechs
künstlichen Antworten und ausdrücklich angeforderten Anschlussübungen wurden
bedient. Ein zwischenzeitlicher Freigabeentzug ließ eine Anschlussübung
scheitern; erst nach Wiederfreigabe wurde sie ausdrücklich erneut angefordert.
Elf Aufrufe kosteten einschließlich des Fehlers laut verfügbaren Belegen
insgesamt 0,242509 USD; unbekannte Kosten waren keine vorhanden. Das künstliche
Konto wurde gelöscht. Ein weiterer dokumentierter Lauf erreichte bei elf
Aufrufen einschließlich früherer Fehlversuche bis zum angegebenen Zeitpunkt
0,192590 USD. Diese Beträge sind Gesamtkosten der jeweiligen Prüfverläufe,
keine Preise einzelner Pakete.

Der damals verwendete Paketcode wurde auf dem aktuellen Entwicklungsstand
beibehalten; die aktuelle Änderung an der Reservierung betrifft nur den
separaten Schulbuddy-Konfliktfall. Die tatsächlichen Aufrufe liegen zeitlich
in der Vergangenheit und belegen weder eine heutige Anbieterverfügbarkeit
noch eine Fehlerquote. Es wurde in dieser Arbeitseinheit kein neuer
Providerauftrag ausgelöst und kein Release durchgeführt.

## Prüfumfang

Auf SQLite bestanden 110 Fälle der Fehler-, Budget-, Wiederaufnahme- und
Interruptionstests; drei PostgreSQL-spezifische Fälle waren dort übersprungen.
Die gleiche Matrix bestand mit 113 Fällen auf isoliertem PostgreSQL vor der
anschließenden Korrektur der Schulbuddy-Sperre; der endgültig erweiterte reale
Prozessneustart und die betroffenen Reservierungsfälle wurden danach separat
auf PostgreSQL geprüft. Weitere 108 Transport- und Schemafälle bestanden auf
SQLite. Nach Behebung der beiden im ersten Gate-Lauf aufgedeckten Probleme
bestanden das vollständige PostgreSQL-Gate mit 81 Fällen ohne Skip und eine
ergänzende Auswahl aus Schulbuddy-, Paket- und Reservierungstests mit 24
Fällen. Die gezielte SQLite-Auswahl bestand mit 45 Fällen; sechs nur auf
PostgreSQL aussagekräftige Fälle waren dort übersprungen. Die erschienene
FastAPI-Testclient-Deprecation-Warnung ist kein fehlgeschlagener Test und
bleibt eine gesonderte Abhängigkeitspflege.
