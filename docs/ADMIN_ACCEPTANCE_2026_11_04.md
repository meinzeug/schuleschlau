# Betriebsadministration: technische Prüfung vom 4. November 2026

## Umfang

Geprüft wurden Benutzer- und Familienverwaltung, Kinderkostensteuerung,
Providerkonfiguration, Kostenbelege und der KI-Notfallstopp anhand
ausschließlich künstlicher Konten und Daten. Die Tests führen keine echten
Anbieter- oder Modellaufrufe aus und verändern keine produktiven Konten,
Budgets, Providerbindungen oder Freigaben. Grundlage ist Commit
`1559d967db35d71f57972df9de469dd2f982c1c0`; späterer Code benötigt einen
eigenen Nachweis. Dieser Bericht ersetzt weder eine unabhängige Sicherheits-
noch eine physische Androidprüfung.

## Aktueller Testbefund

Sieben Backendmodule bestanden auf SQLite mit **122 Fällen**; sechs Fälle
wurden dort übersprungen und auf PostgreSQL ausgeführt. Auf einem isolierten
PostgreSQL-16-Cluster bestanden **127 Fälle**, ein ausschließlich für SQLite
vorgesehener Fall wurde dort übersprungen. Sechs Flutter-Testdateien bestanden
mit **102 Fällen**. Drei davon bestanden auch im Chrome-Webrunner mit
**65 Fällen**; das Framework musste den eigenen Testbrowser beim Schließen
nach erfolglosem SIGTERM mit SIGKILL beenden. Die UI-Prüfungen verwenden
kontrollierte API-Antworten, darunter einen künstlichen Providerfehler; aus
einem Mock wird keine Aussage über die Verfügbarkeit eines realen Anbieters
oder über echte Preise abgeleitet.

Die zusätzliche Prüfung, dass ein Betriebsadmin kein privates Originalbild
einer Heftseite abrufen kann, bestand jeweils einmal auf SQLite und auf dem
isolierten PostgreSQL-Cluster. Zwei weitere Fälle auf jeder Datenbank prüfen,
dass Betriebsadmins keine privaten Noten und Schulbuddy-Kontexte lesen oder
für diese Fragen stellen können.

| Kriterium | Nachweis durch künstliche Fälle |
| --- | --- |
| Familien, Konten, private Inhalte | Filter, Seiten, Revisionen und Löschvorschau; Eltern-/Kinder-/Adminrechte, beispielhafte Sperren für private Originalbilder, Noten und Tutor-Kontexte sowie nachträglicher Sitzungsentzug. |
| Tages-, Monats- und Systemgrenzen | Null, endliche und bewusst unbegrenzte Kindergrenzen; Reservierung, atomare konkurrierende Aufrufe, unveränderte Systemgrenze und erneute Grenzprüfung. |
| Kostenbelege | Bekannte, unbekannte und später korrigierte Kosten; Reservierungen und Gebührenbelege werden nachvollziehbar und idempotent getrennt behandelt. Die Kostenantworten sind simuliert. |
| Notfallstopp | Ein Provider-503 lässt Navigation und expliziten Stopp erreichbar; nur die bewusste Aktion sendet den Stopp. Eine alte Konfigurationsrevision kann ihn nicht wieder aufheben. |
| Entwürfe und Änderungen | Abschnittswechsel, Neuabfrage und Tarifdialog erhalten unabhängige Providerentwürfe. Aktualisierungen verwenden Revisionen, erfolgreiche Änderungen werden auditiert, widerrufene Sitzungen abgewiesen. |
| Lesen und Anzeige | Kontrollierte Lesewege reservieren keine KI-Arbeit und ändern keine Budgets. UI-Fälle decken kleine und breite Ansichten einschließlich großer Schrift ab. |

`unbegrenzt` bezeichnet nur ausdrücklich konfigurierte Kindergrenzen und die
dadurch nach den bestehenden Regeln ersetzten älteren Familien-/Kindergrenzen;
die globale Systemgrenze bleibt eigenständig wirksam. Unbekannte tatsächliche
Gebühren werden nicht als null oder als kostenlos ausgegeben.

## Reproduzierbarkeit

Aus dem Repositorywurzelverzeichnis mit eingerichteter lokaler Testumgebung:

```sh
TMPDIR=/dev/shm PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_admin_users.py backend/tests/test_admin_user_races.py backend/tests/test_admin_ux_controls.py backend/tests/test_child_cost_controls.py backend/tests/test_child_cost_freshness.py backend/tests/test_provider_cost_preflight.py backend/tests/test_parent_audit_ux90.py
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_admin_users.py backend/tests/test_admin_user_races.py backend/tests/test_admin_ux_controls.py backend/tests/test_child_cost_controls.py backend/tests/test_child_cost_freshness.py backend/tests/test_provider_cost_preflight.py backend/tests/test_parent_audit_ux90.py
TMPDIR=/dev/shm PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_source_reading.py::test_operating_admin_cannot_read_a_private_source_figure
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_source_reading.py::test_operating_admin_cannot_read_a_private_source_figure
TMPDIR=/dev/shm PYTHONPATH=backend .venv/bin/pytest -q backend/tests/test_grades.py::test_foreign_family_grade_and_admin_have_no_private_access backend/tests/test_schulbuddy.py::test_admin_and_other_parent_cannot_read_or_submit_private_context
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_grades.py::test_foreign_family_grade_and_admin_have_no_private_access backend/tests/test_schulbuddy.py::test_admin_and_other_parent_cannot_read_or_submit_private_context
cd app
flutter test test/admin_workspace_test.dart test/admin_batch1_ux_test.dart test/admin_child_costs_107_test.dart test/admin_users_screen_test.dart test/admin_round2_provider_test.dart test/installation_provider_draft_test.dart
flutter test --platform chrome test/admin_workspace_test.dart test/admin_child_costs_107_test.dart test/admin_users_screen_test.dart
```

Das temporäre Dateisystem `/dev/shm` ist optional. Die SQLite-Datenbank wird
durch die vorhandenen Testfixtures eigens angelegt und nicht mit dem
Produktivbestand verbunden. Der PostgreSQL-Runner legt seinen eigenen
kurzlebigen Cluster mit privatem Unix-Socket an und entfernt ihn danach.
