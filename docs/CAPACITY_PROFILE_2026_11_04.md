# Isoliertes Kapazitätsprofil vom 4. November 2026

Dieses Profil misst eine eng begrenzte künstliche Last, keine Produktionskapazität und keine Nutzerzahl. Es verwendet den Code auf Basis `f63b054` sowie das in dieser Änderung ergänzte Testprofil. Es wurden keine produktiven Konten, Daten, Serverzeiten oder Anbieter verwendet.

## Reproduktion und Schutz

```sh
python scripts/test_postgres.py backend/tests/capacity_profile.py -s
```

Voraussetzung sind die installierten Backend-Testabhängigkeiten und lokale PostgreSQL-16-Binärdateien. Der Test verwendet den vorhandenen Fixture-Schutz: eine temporäre Datenbank und ein temporäres Datenverzeichnis; zusätzlich wird PostgreSQL ausdrücklich verlangt. Der Runner startet einen kurzlebigen PostgreSQL-16-Cluster mit privatem Unix-Socket und fährt ihn anschließend herunter. Die Testanwendung verwendet nur künstliche Konten und Pixel. Der Worker wird nicht gestartet und ein Provideraufruf ist im Test zusätzlich abgefangen. Die Warteschlange wird nur lokal angelegt. Die Python-Testausgabe enthält ausschließlich aggregierte Messwerte, keine Zugangsdaten oder Inhalte.

Gemessen wird in einem lokalen Prozess über den FastAPI-TestClient und den ASGI-Pfad, **ohne** echten Netzwerk-, TLS-, Proxy-, Geräte-, Worker- oder Anbieterverkehr. Für jeden Request wird ein neuer TestClient verwendet. Die gemessene Requestdauer umfasst den API-Aufruf; die Gesamtzeit des Abschnitts umfasst zusätzlich die Erstellung der Clients. Der Test ist absichtlich nicht Teil der regulären automatischen Testsammlung, sondern muss wie oben ausdrücklich gestartet werden.

## Ablauf und Ergebnis

Am 04.11.2026 gegen 06:40 UTC: Python 3.12.3, PostgreSQL 16.15, 11 für den Prozess sichtbare CPUs. Eine künstliche Familie beziehungsweise ein Kind, dieselbe angemeldete Sitzung und ein künstliches JPEG mit 1200 × 900 Pixeln und 17.729 Bytes. Der Host war keine reservierte Lasttestmaschine; zeitgleiche Arbeit kann die Werte beeinflusst haben. Keine Laufzeitgrenzen oder Produktionsalarme wurden aus diesen Daten festgelegt.

| Aktion | Gleichzeitige Requests | Anzahl | Gesamtdauer | p95 der Requestdauer | Ergebnis |
| --- | ---: | ---: | ---: | ---: | --- |
| Übersicht lesen | 1 | 3 | 0,633 s | 129,73 ms | 3 × HTTP 200 |
| Übersicht lesen | 4 | 12 | 1,996 s | 252,07 ms | 12 × HTTP 200 |
| Übersicht lesen | 8 | 24 | 4,608 s | 569,60 ms | 24 × HTTP 200 |
| Dasselbe Foto mit demselben Schlüssel hochladen | 4 | 4 | 0,701 s | 184,47 ms | 4 × HTTP 201, eine gespeicherte Seite |
| Denselben Erkennungsauftrag reservieren | 4 | 4 | 0,668 s | 161,76 ms | 4 × HTTP 202, ein Auftrag und eine Reservierung |

Die p95-Werte sind bei den kleinen Stichproben als nächsthöherer beobachteter Rang berechnet und statistisch nur eingeschränkt aussagefähig. Am Ende lag genau ein Auftrag in der lokalen Warteschlange; kein Auftrag wurde abgearbeitet. Der Testprozess verbrauchte für die Messabschnitte 8,205 CPU-Sekunden; sein höchster beobachteter RSS betrug 273.920 KiB und umfasst auch Test- und Anwendungsinitialisierung, aber nicht den separaten PostgreSQL-Prozess. Der Profiltest bestand; eine bestehende Starlette-Depräkationswarnung wurde ausgegeben.

## Zweiter Lauf mit getrennten Familien

Ebenfalls am 04.11.2026 wurden drei reguläre künstliche Familien mit getrennten
Anmeldungen gleichzeitig über denselben lokalen ASGI-Testpfad geprüft. Jede
fragte ihre Übersicht ab, lud ein künstlich erzeugtes 1800 × 1200-Pixel-JPEG
mit 1.937.944 Bytes hoch und reservierte anschließend einen Erkennungsauftrag.
Alle drei Vorgänge bestanden; es entstanden drei getrennte lokale
Warteschlangenaufträge und Reservierungen. Kein Worker oder Anbieter wurde
gestartet. Die Gesamtdauer betrug 0,945 s; die p95-Werte für Übersicht, Upload
und Reservierung waren bei nur drei Stichproben 393,42 ms, 219,34 ms und
96,37 ms. Der Pythonprozess verbrauchte 1,005 CPU-Sekunden; sein bis dahin
erreichter maximaler RSS betrug 280.868 KiB, ohne den PostgreSQL-Prozess.
Das künstliche Rauschbild prüft Dateigröße und Bildverarbeitung, nicht die
Erkennbarkeit einer echten Heftseite. Bei drei Beobachtungen ist p95 der
höchste beobachtete Wert und kein belastbarer Grenzwert.

## Noch erforderliche Kapazitätsabnahme

Das Profil prüft neben drei künstlichen Familien keine größeren Familienzahlen, unabhängige Geräte, verschiedene reale Fotoinhalte, Last über längere Zeit, Worker-Durchsatz, Warteschlangenalter, externe Latenz, Netzwerk- oder Ressourcenauslastung des produktionsähnlichen Gesamtsystems. Ein Parallelitätsgrad von acht Requests bedeutet keine acht gleichzeitig lernenden Familien. Für belastbare Betriebsgrenzen müssen vorab ein reales Einsatzprofil, Fehler-/Latenz- und Warteschlangenziele sowie geeignete Alarmwerte festgelegt werden. Anschließend sind Laststufen, Sperren und Idempotenz unter konkurrierenden Sitzungen auf einer ausreichend vergleichbaren, isolierten Umgebung zu messen. Der Roadmap-Hauptpunkt bleibt bis dahin offen.
