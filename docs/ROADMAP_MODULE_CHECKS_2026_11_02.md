# Modulprüfungen für fünf offene Roadmap-Punkte

Ausgeführt am 02.11.2026 durch Codex auf Code-Commit `fffca4a` mit künstlichen
Konten und Inhalten in separaten lokalen Testdatenbanken. Modelltransporte in
diesen Fällen sind simuliert. Dies sind Teilprüfungen, keine vollständigen
Abnahmen im Browser, auf Android oder durch Fachpersonen.

## Hefte und digitaler Ranzen

`TMPDIR=/dev/shm .venv/bin/python -m pytest -q backend/tests/test_notebooks.py backend/tests/test_notebook_actions.py --tb=short`

SQLite: **34 bestanden, drei übersprungen**. Die Fälle prüfen Fachfilter und
begrenzte Listen, fremde Kinderkonten, Löschvorschau und Quelländerungen,
erneutes Einlesen sowie den erhaltenen Aufgabenstand. Die drei ausgelassenen
Sperrentests bestanden separat auf PostgreSQL. Fotoanzeige, große Listen und
Bedienung bei Netzverlust sind hierdurch nicht im Browser nachgewiesen.

## Klassenarbeiten und Nacharbeit

`TMPDIR=/dev/shm .venv/bin/python -m pytest -q backend/tests/test_exam_integration.py backend/tests/test_exam_review_transport.py --tb=short`

SQLite: **45 bestanden**. Geprüft werden unter anderem Quellbindung,
Nacharbeits- und Exportgrenzen, begrenzte Transporte und künstliche Fotos.
Fachliche Qualität tatsächlicher KI-Ausgaben und vollständige mobile
Bedienung bleiben offen.

## Elternübersicht, Noten und Planung

`TMPDIR=/dev/shm .venv/bin/python -m pytest -q backend/tests/test_parent_grade_filters_ux88.py backend/tests/test_grade_pdf_imports.py --tb=short`

SQLite: **45 bestanden**. Die Tests prüfen unter anderem datensparsame Filter,
den lokalen PDF-Import und seine Vorschau. Sie ersetzen keinen Vergleich aller
Anzeigen mit gespeicherten Fakten für mehrere Kinder im Browser.

## Administration

`TMPDIR=/dev/shm .venv/bin/python -m pytest -q backend/tests/test_admin_users.py backend/tests/test_admin_ux_controls.py --tb=short`

SQLite: **47 bestanden**. Abgedeckt sind ausgewählte Rollen-, Kontoverwaltungs-,
Filter- und Revisionsfälle. Sie zeigen keine vollständige Bedienung sämtlicher
Administrations- und Providerzustände auf verschiedenen Ansichten.

## Datenlebenszyklus und Löschung

`TMPDIR=/dev/shm .venv/bin/python -m pytest -q backend/tests/test_preparation_retention.py backend/tests/test_grade_erasure_restore_regression.py --tb=short`

SQLite: **21 bestanden**. Die künstlichen Fälle betreffen unter anderem
Auftragsaufbewahrung und die Wiederherstellung gelöschter Noten. Eine
vollständige Export-/Löschmatrix sowie externe Log- und Aufbewahrungsfristen
sind dadurch nicht belegt.

## PostgreSQL-Sperren

```sh
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py \
  backend/tests/test_notebook_actions.py::test_parallel_reprocess_requests_create_one_source_and_reservation \
  backend/tests/test_notebook_actions.py::test_bulk_keeps_unit_before_child_lock_order_with_concurrent_answer \
  backend/tests/test_notebook_actions.py::test_bulk_rechecks_session_revocation_after_waiting_for_child_lock \
  backend/tests/test_admin_user_races.py --tb=short
```

**Zehn bestanden**, einschließlich der drei in SQLite übersprungenen
Heftfälle. Der kurzlebige PostgreSQL-Cluster nutzte eine eigene Testdatenbank;
dies ist keine vollständige PostgreSQL-Wiederholung aller obigen Fälle.
