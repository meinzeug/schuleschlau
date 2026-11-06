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

## Noch erforderlich

Eine Lösung muss bereits das Einlesen paralleler Multipart-Anfragen und die
Dekodierung begrenzen, ohne die bisherigen erlaubten Formate, die 16-MP-Grenze,
EXIF-Ausrichtung, Qualität und idempotente Wiederholungen unbemerkt zu ändern.
Ein gesondert begrenzter Decoderprozess kann untersucht werden; ein API-Abbruch
muss auch beim Überschreiten seines Speichers vermieden und der Ablehnungsweg
für die App verständlich und wiederholbar sein. Nach dem Fix müssen die oben
aufgeführten Mischlasten und große Fotos mehrfach unter den tatsächlichen
Prozessgrenzen bestehen. Auch weitere parallele API-Wege und eine längere
Lastdauer bleiben dann gesondert zu prüfen. Der große Roadmap-Punkt für
Kapazität bleibt offen.
