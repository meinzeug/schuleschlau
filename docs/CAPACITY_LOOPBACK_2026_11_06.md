# Isoliertes Loopback-Lastprofil und Verbindungs-Pool vom 6. November 2026

Geprüfter Ausgangsstand `c2aa4f9a` mit den Änderungen dieses Berichts.

Bei der gleichzeitigen Reservierung künstlicher KI-Aufträge zeigte sich ein
zeitweise reproduzierbarer Verbindungsengpass. Der erste Request hielt bereits
eine Datenbankverbindung und eine Kindersperre, während die Freigabeprüfung
für die Betriebseinstellungen eine zweite Verbindung aus demselben Pool
anforderte. Wenn gleichzeitig genügend Requests ihre erste Verbindung hielten,
warteten sie auf weitere Verbindungen; Kind-Sperren verlängerten die Blockade.
Ein Thread-Dump der isolierten Testumgebung zeigte diesen tatsächlichen
Produktcodepfad. Der Test belegte keine aktiven künstlich gehaltenen
Transaktionen außerhalb der Anfragen.

Der Fix übergibt vorhandene Datenbanksitzungen an die Freigabeprüfung und liest
die gespeicherten Betriebseinstellungen innerhalb dieser Sitzung frisch per
Skalarabfrage, ohne die ORM-Identity-Map zu vertrauen oder ungespeicherte
Änderungen zu flushen beziehungsweise zu überschreiben. Die vorhandenen
Prüfungen von Datenschutzfreigaben, Anbieter, Fähigkeiten, Revisionsstand und
Notfallstopp bleiben erhalten. Dieselbe Änderung wird in den vorhandenen
Vorher-/Nachher-Prüfstellen genutzt; der externe Provideraufruf selbst erhält
keine offene DB-Sitzung. Bestehende Kontingente und Poolgrößen wurden nicht
angehoben. Unter PostgreSQLs normalem `READ COMMITTED` wurde im Test eine
zwischenzeitliche Freigabe- beziehungsweise Nachweisrücknahme aus einer zweiten
Sitzung auch bei einem absichtlich veralteten ORM-Objekt erkannt; ein anderes,
ungespeichertes Kindfeld blieb dabei unverändert und ungeschrieben.

## Reproduzierbarer Sättigungstest

```sh
TMPDIR=/dev/shm nice -n 10 taskset -c 0 \
  /home/dennis/schulpilot/.venv/bin/python scripts/test_postgres.py \
  backend/tests/capacity_pool_regression.py \
  backend/tests/test_provider_session_reuse.py -s --tb=short
```

Der Runner erstellt einen kurzlebigen PostgreSQL-16-Cluster mit privatem
Unix-Socket und künstlichen Familien/Fotos. Ein nur an `127.0.0.1` gebundener
Uvicorn-Prozesspfad bedient echte lokale TCP-HTTP-Anfragen; API, künstlicher
Provider und Testtreiber laufen in Threads desselben Pythonprozesses. Eine
Testbarriere hält **15 getrennte reguläre Reservierungsrequests** unmittelbar
vor der Freigabeprüfung an, nachdem jeder seine normale Transaktion geöffnet
hat. Das entspricht der Standard-Poolobergrenze von fünf plus zehn
Overflow-Verbindungen. Der Pool-Timeout wird ausschließlich im Test auf zwei
Sekunden gesetzt, damit die vor dem Fix reproduzierbare Störung begrenzt
bleibt; weder Anwendungs-Poolgröße noch Produktions-Timeout werden geändert.

Vor dem Fix: 3 × HTTP 202 und 12 × HTTP 500 bei 15 Anfragen. Nach dem Fix:
15 × HTTP 202, p95 523,43 ms und Gesamtdauer 0,723 s. Danach lieferten 30
idempotente Wiederholungen HTTP 202; 15 Jobs mit 15 Reservierungen wurden von
zwei künstlichen Worker-Threads einmalig abgeschlossen. Zwei weitere Tests
prüften den dokumentierten Widerruf und unveränderte ungespeicherte Daten.
**Drei Tests bestanden** auf isoliertem PostgreSQL. Die Barriere ist ein
gezieltes Fehlerreproduktionsmittel und kein realistisches Lastmodell.

## Wiederholtes Lastprofil ohne Barriere

```sh
TMPDIR=/dev/shm nice -n 10 taskset -c 0 \
  /home/dennis/schulpilot/.venv/bin/python scripts/test_postgres.py \
  backend/tests/capacity_network_profile.py -s --tb=short
```

Am 06.11.2026 ab etwa 05:41 Uhr Berliner Zeit, Python 3.12.3,
PostgreSQL 16.15, ein CPU-Kern, `tmpfs`; der Host war nicht exklusiv und ein
Offsite-Prozess lief parallel. Sechzehn Familien verwenden je ein künstliches
JPEG mit 1.938.882 Byte. Dieselben Uploads und Aufträge werden je zweimal mit
identischen Schlüsseln und bis zu 16 parallelen HTTP-Anfragen gestartet. Zwei
Worker bearbeiten Jobs über den echten Claim-/Verarbeitungspfad; der
synthetische Anbieter wartet jeweils zwei Sekunden und sendet keine Netzwerk-
oder KI-Anfragen. Daneben erfolgen Übersichts- und Listenabrufe sowie weitere
Uploads. Familienregistrierung geschieht vor der Messung über TestClient.

Drei aufeinanderfolgende Läufe vor dem Fix scheiterten bei der Reservierung:
32, 16 beziehungsweise 16 von 32 Requests liefen jeweils in einen 30-s-
Lesetimeout. Ein früherer unveränderter Vergleichslauf war zufällig bestanden;
die Störung trat also nicht in jedem Lauf auf.

Nach dem Fix bestanden drei erneute Läufe. Jeweils 32/32 Foto- und
32/32 Reservierungswiederholungen waren erfolgreich und ergaben genau 16
verschiedene Quellseiten, 16 Aufträge, 16 Reservierungen und 16 einmalige
Abschlüsse. Die Warteschlange sank von 16 auf null; zwei Provider-Threads waren
nachweislich gleichzeitig aktiv. Beispiele der drei p95-Werte:

| Vorgang | Parallelität | p95 Lauf 1 / 2 / 3 |
| --- | ---: | --- |
| Übersicht, je 48 GET | 1 | 56,01 / 49,66 / 51,64 ms |
| Übersicht, je 48 GET | 4 | 193,09 / 211,79 / 446,65 ms |
| Übersicht, je 48 GET | 8 | 532,71 / 480,75 / 584,58 ms |
| Übersicht, je 48 GET | 16 | 1.144,08 / 1.193,71 / 1.192,60 ms |
| Uploadwiederholung, je 32 POST | 16 | 1.664,84 / 1.445,16 / 1.427,64 ms |
| Reservierungswiederholung, je 32 POST | 16 | 2.383,42 / 612,78 / 545,39 ms |
| Gemischte API-Anfragen mit Worker, je 48 | 16 | 1.297,53 / 1.302,19 / 1.277,21 ms |

Die Workerabschnitte dauerten 17,922 / 18,009 / 18,087 s; das höchste
abgetastete Alter wartender Jobs betrug 16 / 16 / 15 s. Die höchste gemessene
RSS-Summe aus Test-/API-Prozess und PostgreSQL-Prozessen lag bei 1.121.632 /
1.120.480 / 1.099.272 KiB. Die RSS-Summe zählt gemeinsam genutzte Seiten
mehrfach und enthält den Lastgenerator; `tmpfs`-Dateien sind darin nicht
vollständig erfasst. Der nächsthöhere beobachtete p95-Rang bei nur 32–48
Messungen ist keine belastbare Langzeitprognose.

Eine breitere isolierte SQLite-Regression über Provider, Kostenprüfung,
Schulalltag, Materialprüfung, Tutor, Wortschatz, Klassenarbeiten, Lernweg und
Grafik-Jobs ergab 483 bestandene und sechs übersprungene Tests. Dazu gehören
auch künstliche Änderungen und Widerrufe während der Verarbeitung.
Ein weiterer isolierter PostgreSQL-Lauf mit dem gesättigten HTTP-Pool und
gezielten API-/Workerprüfungen für Sitzungs-, Quellen- und Provideränderungen
ergab 32 bestandene Tests; der Sättigungsfall lieferte erneut 15 × HTTP 202.

**Grenzen:** Keine TLS-/Reverse-Proxy- oder echten Mobilgerätelatenzen,
getrennten API-/Worker-Prozesse mit produktiven systemd-Speicherlimits,
Netzwerkausfälle, Dauerlast oder echte Anbieterzeiten wurden geprüft. Die
Messwerte sind keine Nutzerzahl oder Freigabe für wachsenden Betrieb; auch
Alarmzustellung und Schwellenwerte sind noch nicht kalibriert. Der große
Kapazitäts-Roadmap-Punkt bleibt offen.
