# Isolierte Regressionen zu fünf offenen Roadmap-Punkten

Stand: 02.11.2026. Ausgeführt durch Codex auf dem lokalen Arbeitsstand
`297d244`; es wurden ausschließlich künstliche Inhalte und separate
Testdatenbanken verwendet. Die Testsuite simuliert die jeweils verwendeten
Modelltransporte. Es fand bei diesen Läufen kein echter KI-Aufruf, keine
Bedienung durch ein Kind und keine fachkundige Abnahme statt. Die produktive
Datenbank und die beiden bereits vorhandenen lokalen Versionsänderungen wurden
nicht verwendet.

Die folgenden Ergebnisse sind Teilnachweise. Sie erfüllen nicht die gesamten
Abnahmekriterien der jeweiligen Roadmap-Punkte.

## Abruf und Lernplanung

```sh
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_recall_planning_journey.py \
  backend/tests/test_learning_controller.py --tb=short
```

**SQLite: 13 bestanden.** Der kombinierte Mehrtagesfall nutzt eine Testuhr,
synthetische Antworten und erzeugt die Wiederholungsrunden als Testdatensätze.
Er belegt keine durchgehende tatsächliche Planauswahl oder mobile Bedienung
über mehrere Tage. Der kombinierte Fall bestand zusätzlich auf PostgreSQL,
siehe unten.

## Ausgabelängen, Schemafehler und Providerstörungen

```sh
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_package_transport_retry.py \
  backend/tests/test_package_output_budget.py \
  backend/tests/test_package_prefix_publication.py --tb=short
```

**SQLite: 49 bestanden, ein PostgreSQL-Sperrentest übersprungen.** Die Fälle
decken unter anderem begrenzte Ausgaben, erhaltene Teilergebnisse, bewusste
Wiederholung und doppelte Anforderungen ab. Der übersprungene Parallelitätsfall
bestand separat auf PostgreSQL. Es handelt sich nicht um eine vollständige
Matrix aller Anbieterfehler oder um einen echten Anbieteraufruf.

## Referenzdatenbank und Medienauswahl

```sh
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_catalog_ai.py \
  backend/tests/test_package_part_reference_binding.py \
  backend/tests/test_visual_references.py --tb=short
```

**SQLite: 109 bestanden.** Geprüft werden unter anderem erlaubte Kandidaten,
Referenz- und Quellenbindung, Versionen, ungültige oder geänderte Quellen und
der simulierte Transport. Sichtbare Browserausgaben für mehrere Fächer,
fachliche Abnahme und Vollständigkeit des tatsächlichen Medienkatalogs sind
dadurch nicht belegt.

## Erklärgrafiken und Animationen

```sh
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_learning_scenes.py \
  backend/tests/test_visual_positions.py --tb=short
```

**SQLite: 50 bestanden.** Die Tests prüfen unter anderem Szenenstruktur,
Quellenbelege, Offenlegungsstufen, Manipulationen und simulierte
Modelltransporte. Sie prüfen weder jede angebotene Erklärung noch fachliche
Richtigkeit oder tatsächliche Bedienbarkeit aller Animationen im Browser.

## Schulbuddy

```sh
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_tutor.py \
  backend/tests/test_schulbuddy_learning_assets.py --tb=short
```

**SQLite: 44 bestanden, zwei PostgreSQL-Sperrentests übersprungen.** Die
synthetischen Tests prüfen Quellenzitate, Familienrechte, Quellen- und
Sitzungsänderungen sowie die Zuordnung von Hilfe. Die beiden übersprungenen
Rennen bestanden separat auf PostgreSQL. Eine echte Bewertung der
Antwortqualität und die vollständige Browserbedienung sind nicht enthalten.

## PostgreSQL-Nachprüfung

Ein eigener kurzlebiger PostgreSQL-Cluster und eine separate Testdatenbank:

```sh
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py \
  backend/tests/test_recall_planning_journey.py \
  backend/tests/test_package_prefix_publication.py::test_two_parallel_requests_publish_exactly_once_under_real_child_row_lock \
  backend/tests/test_tutor.py::test_simultaneous_last_answer_finishes_before_tutor_without_retrospective_help \
  backend/tests/test_tutor.py::test_legacy_delete_racing_tutor_waits_then_requires_counted_cascade \
  --tb=short
```

**PostgreSQL: vier bestanden, keiner übersprungen.** Dieser Lauf ergänzt die
gezielten Sperren und den Mehrtagesfall; er ist keine vollständige
PostgreSQL-Wiederholung aller oben genannten Tests.
