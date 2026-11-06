# Isoliertes Zwei-Worker-Profil vom 6. November 2026

**Ergebnis:** Zwei konkurrierende Worker-Threads verarbeiteten acht getrennte
künstliche Aufträge genau einmal. Die Warteschlange war anschließend leer.
Dies ist ein begrenzter Funktionstest mit Messwerten, keine Aussage zur
Produktionskapazität, zu echten Anbieterzeiten oder zu einer Zahl betreubarer
Familien. Auch die bestehenden Alarmgrenzen sind dadurch nicht kalibriert.

## Ziel und vorher festgelegtes Profil

Auf Basis von `45b66d20` einschließlich der für diesen Bericht ergänzten
Teständerung: acht künstliche Familien, je ein JPEG mit 1.938.882 Byte,
pro Familie zwei gleichzeitige Uploads mit demselben Idempotenzschlüsseln und
zwei gleichzeitige Reservierungen desselben Auftrags. Zwei konkurrierende
Worker-Threads rufen den tatsächlichen PostgreSQL-Claim und den Workerpfad auf;
die fest eingebaute künstliche Providerantwort wartet zwei Sekunden. Während
die Worker laufen, greifen acht Clients gleichzeitig mit insgesamt 24
Übersichts-, Listen-, Upload- und Wiederholungsanfragen zu. Der Test verlangt
zwei tatsächlich gleichzeitig im künstlichen Provider aktive Worker, korrekte
HTTP-Status, genau eine gespeicherte Seite und Reservierung pro
Idempotenzschlüssel, eindeutige Claims, genau acht beendete Aufträge und je
einen Versuch. Er darf keinen externen Anbieter ansprechen.

## Isolation und Reproduktion

```sh
TMPDIR=/dev/shm nice -n 10 taskset -c 0 \
  /home/dennis/schulpilot/.venv/bin/python scripts/test_postgres.py \
  backend/tests/capacity_worker_profile.py \
  backend/tests/capacity_delayed_worker_profile.py \
  backend/tests/test_operations.py \
  -k 'bounded_multi_family_worker_profile or bounded_delayed_multi_family_worker_profile or queue_age or successful_queue_snapshot or operational_metrics_are_private' \
  -s --tb=short
```

Der Runner erstellt eine temporäre PostgreSQL-16-Datenbank und private
Unix-Sockets in einem neuen temporären Verzeichnis, öffnet keinen TCP-Port und
räumt den Cluster nach dem Lauf auf. Die Lastprofile überprüfen das Ziel vor
dem zerstörenden Test-Fixture: Der Datenbankname, die lokale Socketstruktur,
der Eigentümer und die Verzeichnisrechte müssen zum privaten Test-Runner
passen. Direkte Aufrufe ohne Datenbankziel und mit einem TCP-Ziel wurden bei
der Sammlung abgewiesen. Alle Fotos, Familien und Anfragen sind künstlich.
Die Anwendung wird per FastAPI-TestClient in demselben Prozess aufgerufen;
Netzwerk, TLS, Proxy und echte Geräte werden nicht gemessen.

Der Test lief am 06.11.2026 gegen 05:13 Uhr Berliner Zeit auf Python 3.12.3 und
PostgreSQL 16.15. PostgreSQL und temporäre Testdaten lagen auf `tmpfs` unter
`/dev/shm`, weil zeitgleich der reguläre Offsite-Lauf das Dateisystem belastete.
Der Test erbte `taskset -c 0` und eine reduzierte Prozesspriorität. Der Rechner
war nicht exklusiv reserviert; ein RAM-Dateisystem, lokale Arbeit und andere
Hardware sind ausdrücklich keine Abbildung des Produktivservers. Der separate
Ein-Worker-Vergleich verwendete dieselbe Umgebung und den simulierten
100-ms-Anbieter. Keine Modellqualität und keine externe Dienstlatenz wurden
überprüft.

## Beobachtungen

| Messung | Ein Worker / 0,1 s | Zwei Worker / 2 s |
| --- | ---: | ---: |
| Familien und Aufträge | 8 | 8 |
| Simulierte gleichzeitige Provideraufrufe, beobachtet | 1 | 2 |
| Übersicht 24 GET, parallel 1, p95 | 51,59 ms | 46,57 ms |
| Übersicht 24 GET, parallel 4, p95 | 327,41 ms | 399,31 ms |
| Übersicht 24 GET, parallel 8, p95 | 622,09 ms | 648,99 ms |
| 16 Upload-Wiederholungen, parallel 8, p95 | 789,79 ms | 730,54 ms |
| 16 Reservierungswiederholungen, parallel 8, p95 | 396,11 ms | 327,63 ms |
| 24 gemischte API-Aufrufe während Worker, p95 | 720,35 ms | 847,38 ms |
| Dauer Claim und Worker | 6,506 s | 9,753 s |
| Warteschlange zu Beginn / am Ende | 8 / 0 | 8 / 0 |
| Höchstes abgetastetes Alter eines wartenden Jobs | 6 s | 8 s |
| Höchste abgetastete Anzahl wartend / laufend | 4 / 4 | 6 / 2 |
| Einmalig verarbeitete Jobs | 8 | 8 |
| Gesamtdauer des Messabschnitts | 24,240 s | 28,459 s |
| Python-CPU-Zeit im Messabschnitt | 19,665 s | 21,356 s |
| Höchste abgetastete RSS-Summe Python plus PostgreSQL | 745.700 KiB | 902.924 KiB |

Die p95-Werte sind bei 16 bis 24 Einzelanfragen der nächsthöhere beobachtete
Rang und keine stabile Perzentilschätzung. Das Warteschlangenalter wurde nur
während des Workerabschnitts alle 0,5 Sekunden abgetastet, die beiden
Datenbankabfragen für wartend und laufend sind keine gemeinsame Momentaufnahme.
Beim Ein-Worker-Vergleich wurden vier Aufträge vorab zum Claim-Test als laufend
markiert; das ist keine Angabe von vier gleichzeitig rechnenden Workern.
Die RSS-Summe zählt gemeinsam genutzte PostgreSQL-Speicherseiten mehrfach und
enthält den Testtreiber; der zweite Test lief im selben pytest-Prozess wie der
erste. Auch temporäre `tmpfs`-Dateien benötigen Speicher, den diese RSS-Summe
nicht erfasst. Acht simulierte und null externe Provideraufrufe wurden gezählt.

Beide Profile sowie vier Operations-Tests bestanden auf PostgreSQL: **6 Tests,
7 abgewählt**. Die vier Operations-Tests bestanden zusätzlich auf isoliertem
SQLite. Sie prüfen das aggregierte Alter bei leeren und gefüllten
Warteschlangen, fehlenden und zukünftigen Zeitstempeln und den Schutz des
privaten Betriebsendpunkts. `oldest_queued_seconds` und
`oldest_running_seconds` liefern nur Zeitspannen, keine Inhaltsdaten; `null`
bedeutet keinen vorhandenen Zeitstempel. Die bisherigen Schwellen bleiben
unverändert.

Die Abnahme des großen Roadmap-Punkts bleibt offen: Es fehlen ein vereinbartes
reales Nutzungsprofil, längere Laststufen, getrennte produktionsähnliche
Prozesse mit echter Speichergrenze, Netzwerk und kontrolliert gemessenen
Anbieterzeiten, die Bewertung der Alarmzustellung sowie daraus abgeleitete
verantwortete Betriebsgrenzen.
