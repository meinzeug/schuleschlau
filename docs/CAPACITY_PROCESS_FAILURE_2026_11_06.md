# Getrennte Prozessprüfung: Fotoimport unter Speicherdruck

**Status: offen, nicht produktionsreif abgenommen.** Auf Commit `060f5e0`
wurde mit ausschließlich künstlichen Bildern und Familien ein reproduzierbarer
Abbruch des API-Prozesses bei parallelen Fotoimporten beobachtet. Die API im
Test war wie der tatsächliche Dienst auf 350 MiB beschränkt; der Worker hatte
300 MiB. Es wurde keine Produktivlast erzeugt und keine Produktionsdatei oder
Konfiguration verändert. Es gibt damit keine Aussage über eine Anzahl
unterstützbarer Familien oder die Häufigkeit des Fehlers im echten Betrieb.

## Aufbau und Reproduktion

```sh
TMPDIR=/dev/shm nice -n 10 taskset -c 0 \
  /home/dennis/schulpilot/.venv/bin/python scripts/test_postgres.py \
  backend/tests/capacity_process_profile.py -s --tb=short
```

Der Test ist ausdrücklich kein regulärer CI-Test. Er benötigt Linux mit einer
nutzbaren `systemd --user`-Instanz und PostgreSQL 16. Er erstellt einen
privaten temporären PostgreSQL-Cluster und eine private Socketverbindung;
vor irgendeinem Inhaltstest verlangen Runner und Hilfsprozesse explizit die
isolierte Test-Datenbank und das Test-Environment. API und Worker werden in
getrennten kurzlebigen Benutzer-scopes mit der jeweiligen Speichergrenze und
`TasksMax=64` gestartet. Die CPU-Affinität beschränkt alle Prozesse auf einen
Kern; die Hostmaschine war nicht exklusiv reserviert. SQL-Datenbank und
Testdateien lagen hier im RAM-Dateisystem, das deshalb auch Speicherplatz
benötigt und nicht den Produktivdatenträger nachbildet. Der API-Port lauscht
nur auf `127.0.0.1`; die Hilfsprozesse verweigern Verbindungen zu anderen
Internetadressen. Der Worker verwendet ausschließlich eine fest eingebaute
künstliche Antwort nach zwei Sekunden, keine echten Anbieter oder Kindertexte.

Acht künstliche Familien senden je zwei idempotente Uploadanfragen, höchstens
acht gleichzeitig, für ein synthetisches JPEG mit 1.938.882 Byte. Während
Import und Wiederholungen liest ein anderer Client fortlaufend Übersichten.
Vor dem Import lieferten je 32 GET-Anfragen bei Parallelität 1, 4 und 8 jeweils
HTTP 200; gemessene p95: 49,43 / 196,33 / 422,13 ms. Während der Uploadphase
brach der API-Prozess durch `SIGKILL` ab, und Clients meldeten eine abgebrochene
HTTP-Verbindung. Der Wert `memory.peak` der API-cgroup betrug 367.001.600 Byte;
`memory.events` meldete `oom 1` und `oom_kill 1`. Dadurch erreichte der Test
den Workerabschnitt nicht. Eine spätere Wiederholung mit expliziter
`memory.max`-Prüfung meldete erneut `oom 1`, `oom_kill 1` und denselben
Grenzwert; die Übersichtsp95 waren 50,71 / 195,38 / 541,48 ms. Ein direkter
Aufruf des Hilfsprozesses ohne Testdatenbank sowie mit einem SQLite-Ziel wurde
jeweils vor dem Start abgewiesen. Kleine Stichprobe und RAM-Dateisystem schließen
Schlüsse über reale Lastgrenzen ausdrücklich aus.

Ein zusätzlicher mit `CAPACITY_LARGE=1` wählbarer Fall verwendet ein künstliches
3990×3990-JPEG (15.920.100 Pixel, 8.136.284 Byte), vier Familien und acht
Uploadversuche. Ein experimenteller Zwischenstand, der nur die Normalisierung
serialisierte und Vollbildkopien verringerte, stieß auch bei diesem Fall mit
parallel laufenden Übersichtslesern an das cgroup-Limit. Eine zusätzliche
Begrenzung vor dem Multipart-Einlesen bestand zwar einen Durchlauf ohne
Leseverkehr, erreichte aber bereits 363.618.304 Byte; mit laufenden Lesern
scheiterte sie erneut. Diese Zwischenstände wurden **nicht übernommen**.
Sie beweisen deshalb weder eine Behebung noch einen sicheren Durchsatz.

Bei der geprüft installierten Pillow-Version liefert
`draft('RGB', (3200, 3200))` für das 3990×3990-JPEG weiterhin 3990×3990 Pixel.
Eine stärkere JPEG-Dekodierung auf die nächste Stufe ergäbe 1995×1995 und
würde die bisherige maximale Darstellung von 3200 Pixeln unterschreiten. Eine
solche Qualitätsänderung oder eine Absenkung erlaubter Bildgrößen wurde nicht
vorgenommen. PNG, EXIF-Rotation und Bildbombenprüfung wurden durch diese
Untersuchung nicht geändert oder neu abgenommen.

## Lokal getesteter Lösungsstand

Ein isolierter Fotodecoder läuft als eigener lokaler Dienst in einer separaten
256-MiB-cgroup. API und Dienst überprüfen ihre Unix-Socket-Gegenstellen;
der Dienst erhält keine Provider- oder Datenbankkonfiguration. Fotoanfragen werden
vor dem Einlesen begrenzt, bei Überlast oder Dienstausfall mit 503 abgewiesen
und können ausdrücklich wiederholt werden. Nach dem Dekodieren werden
Sitzung, Familienberechtigung und Importfreigabe erneut geprüft. Das betrifft
Heft- und Klassenarbeitsfotos; andere Bildpfade wie Profilbilder und
Quellausschnitte sind nicht umfasst. Bildqualität, 16-MP-Grenze und erlaubte
Formate bleiben erhalten.

Ein lokaler PostgreSQL-Mischlastlauf mit vier künstlichen Familien, acht
15.920.100-Pixel-JPEG-Uploads, parallel lesenden Clients und einem einzelnen
CPU-Kern bestand. Fünf explizite Wiederholungen nach Überlast waren nötig;
acht Uploadantworten waren 201, die API-cgroup erreichte 226.934.784 von
367.001.600 Byte und die Fotodienst-cgroup 224.149.504 von 268.435.456 Byte;
kein OOM wurde gemeldet. Dies beschreibt genau diesen Lauf, keinen garantierten
Durchsatz oder allgemeine Überlastfestigkeit. Die lokale Socket- und
Systemd-User-Probe verwendete ausschließlich künstliche Daten. Eine separate
Systemd-Testunit zeigte beim Wechsel zwischen künstlichen Releases einen
korrekten Decoderwechsel und dass ein laufender Decoder beim Dienstneustart
beendet wurde; das ist keine Prüfung der Produktionsunit oder von activate.py.

Auf Basis `ee36ab8` bestand derselbe große JPEG-Mischlastfall erneut: vier
explizite Wiederholungen, acht erfolgreiche Uploads, API-Spitze 242.622.464
Byte und Fotodienst-Spitze 227.205.120 Byte, ohne OOM. Eine kurzlebige echte
System-Systemd-Testunit mit künstlicher DynamicUser-Identität und denselben
wesentlichen Sandboxdirektiven zeigte die erwarteten effektiven Werte. Ein
zugehöriger Negativtest verwehrte IPv4 und verbarg die geprüften D-Bus-,
Resolver-, PostgreSQL-, Provider- und privaten Datenpfade. Socketrechte,
berechtigte und falsche Peer-UID wurden ebenfalls geprüft. Sie verwendete
System-Python und eine künstliche Gruppe, nicht die produktiven Dienstkonten.

Ein weiterer Lauf mit einem stark komprimierbaren künstlichen RGBA-PNG derselben
Pixelzahl bestand mit vier expliziten Überlast-Wiederholungen; API-Spitze
140.439.552 Byte, Fotodienst-Spitze 174.780.416 Byte, kein OOM. Das ist kein
Nachweis für alle Bildinhalte oder weitere Lastkombinationen.

Authentifizierte Nutzer können den einzelnen Uploadslot wiederholt mit langsam
übertragenen Anfragen bis zur absoluten 60-Sekunden-Frist belegen; dies ist
eine bekannte Fairnessgrenze. Die zusätzlichen Mount- und Netznamespace-
Negativproben decken ausgewählte lokale Brokerpfade ab, keine vollständige
Prüfung gegen jede mögliche Kompromittierung. Ein produktiver Wechsel setzt
den unabhängigen Review, eine reale Testaktivierung mit Rückweg, gesicherte
Datensicherung und Prüfungen auf dem Zielsystem voraus. Insbesondere dürfen
Rollback und Pruning nicht mit alten Werkzeugen erfolgen, die den neuen Dienst
nicht kennen.

## Ergänzung: Stillstand beim Hochladen

Der lokale Stand begrenzt die Wartezeit auf das nächste Datenpaket zusätzlich
auf 15 Sekunden. Kommen Daten weiter an, beginnt die Inaktivitätsfrist erneut;
die absolute 60-Sekunden-Frist und die bisherigen Größen- und Bildgrenzen
bleiben bestehen. Die Tests prüfen fortlaufende Daten, Stillstand, die weiterhin
wirksame Gesamtfrist, die Freigabe des belegten Slots und einen tatsächlichen
langsamen lokalen HTTP-Socket. Ein bewusst tröpfelnder Transfer kann bis zur
Gesamtfrist weiter einen Slot belegen. Netzwerkqualität und produktive
Kapazität sind damit nicht umfassend abgenommen.

## Noch erforderlich

Die produktiven Dienstdefinitionen und die vollständige Aktivierungs- und
Rückrollkette müssen auf dem Zielsystem nachgewiesen werden. Die Mischlasten
und weitere parallele API-Wege müssen mit längerer Laufdauer und unter den
tatsächlichen Prozessgrenzen geprüft werden. Der große Roadmap-Punkt für
Kapazität bleibt offen.
