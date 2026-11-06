# Löschjournal: Inventar der Snapshot-Sperren

Stand: isolierte Entwicklung, **nicht produktiv ausgerollt**. Ein Journalexport
prüft die Outbox unter einer gemeinsamen Lesesperre. Ein Lösch-Commit, der diese
Sperre nicht ebenfalls exklusiv nimmt, kann nach der Prüfung erfolgen. Das
Beispiel `test_unguarded_outbox_commit_after_probe_is_a_documented_snapshot_gap`
zeigt diese Grenze bewusst; es ist kein Erfolgstest für vollständige Abdeckung.

## Nachvollzogene Pfade

| Pfad | Gegenwärtiger Stand |
| --- | --- |
| `grades.py`: Notenänderung/Löschung; `grade_erasure.py`: ablaufende Noten und Importbelege | Bestehende `journal_write_lock` vor der jeweiligen schreibenden Transaktion; vorhandene Pfade/Tests bei Integration erneut prüfen. |
| `vocabulary.py:delete_item`, `discard_import`, `erase_collection` | Neu: Journalsperre vor Kind, anschließend Sitzungs- und Familienrechte erneut prüfen, Outbox-Commit unter der Sperre, Journalflush erst nach ihrer Freigabe. Konkurrente API-Tests und vorhandene Wortschatz-Restoretests laufen auf isoliertem SQLite und PostgreSQL. Die Worker-Aufbewahrung ist ein separater, weiterhin offener Pfad. |
| `families.py:revoke_member` | Neu: Journalsperre vor Family und Child, anschließend Sitzung und Eigentümerschaft neu prüfen; Outbox-Commit unter der Sperre, Flush danach. Konkurrierende API-Tests; bestehende PostgreSQL-Tests zu gleichzeitigem Sitzungswiderruf und Seitenlöschung erneut ausgeführt. |
| `families.py:delete_child` | Kandidat: Journal → alle Units → Child → Session und erneute Familien-/Passwortprüfung; Outbox-Commit unter Journal, Flush danach. Snapshot- und Widerrufsrennen auf SQLite und PostgreSQL geprüft. Weitere gleichzeitige Familien-/Lernaktionen sowie unabhängiger Review bleiben vor Integration erforderlich. |
| `families.py:delete_account`; Helfer `remove_child`, `remove_family` | Noch offen: Familien- und Kontolöschung committen ohne durchgehende Journalsperre. Helfer werden auch vom Worker und Admin verwendet; sie selbst dürfen nicht blind eine zweite nicht-reentrante Sperre nehmen. |
| `school_day.py:remove_page`, `material_actions.py:bulk_delete`, `materials.py:delete_material` | Neu: Journal vor Unit → Child → Session, Outbox-Commit darunter und Flush nach Freigabe. Kinder-Tagesseiten delegieren vor der Sperre, damit sie nicht verschachtelt erworben wird. Konkurrierende Snapshot-/Sitzungstests auf SQLite und PostgreSQL; Rechteverlust kann datensparsam als 401 oder 404 abgewiesen werden. |
| `source_cleanup.py:main --apply-digest` | Neu: expliziter Operator-Apply erwirbt das Journal vor der DB-Transaktion und Unit → Child; Flush nach Sperrfreigabe. Ein konkurrierender Test und bestehende Bereinigungs-/Restoretests bestanden jeweils auf SQLite und PostgreSQL. Das wiederverwendbare `apply` setzt voraus, dass jeder schreibende Aufrufer die äußere Sperre bereits hält. |
| `unit_actions.py:confirm` | Neu: Journal vor Unit → Child → Session; Outbox-Commit unter der Sperre, Flush danach. Tests prüfen sowohl die blockierte Snapshot-Konkurrenz als auch den Sitzungswiderruf während des Wartens; bestehende Unit-/Sessiontests auf SQLite und PostgreSQL erneut ausgeführt. |
| `admin_users.py:confirm_delete` | Noch offen: nach revisionsgebundener Prüfung können Familien-/Kinder-/Mitgliedschafts- und Nutzerereignisse entstehen; Sperre vor die gesamte schreibende Transaktion legen, Audit/Idempotenz und Cleanup erhalten. |
| `worker.py:maintenance` | Noch offen: große Transaktion für abgelaufene Familien, Seiten, Units und Wortschatz erzeugt verschiedene Outbox-Einträge. Bevor diese unter die Sperre fällt, Laufzeit, verschachtelte grade-/Workerpfade und Sperrreihenfolge untersuchen; gegebenenfalls in kurze explizite Transaktionen zerlegen. |
| `erasure.py:flush_journal` | Nimmt bereits Journal vor DB; eine nachträgliche Sperre ausschließlich bei `Session.commit()` kann umgekehrt DB vor Journal nehmen und Deadlocks verursachen. |
| `erasure.py:reconcile` | Bewusst separater Restore-Testbestand; keine produktiven API-Sperren daraus ableiten. |

Diese Tabelle ist eine Code-Inventur, kein Beweis, dass alle indirekten Aufrufer
bereits gefunden sind. Insbesondere vor jeder Änderung sämtliche Aufrufe von
`request`, `remove`, `remove_child`, `remove_family` und
`erase_assignments` sowie implizite Commits und Hintergrundroutinen prüfen.

## Nächste Schritte

1. Für jeden schreibenden Einstieg `journal_write_lock` **vor** der ersten
   DB-Schreib-/Zeilensperre erwerben; sie bis zum Commit der Löschungen und
   Outbox halten. Bestehende Reihenfolge Unit → Child → weitere Zeilen bleibt
   innerhalb der äußeren Journalsperre bestehen. `flush_journal()` erst nach
   Freigabe aufrufen, da die Betriebssperre nicht reentrant ist.
2. Für jeden Einstieg einen echten konkurrierenden Test mit gehaltener
   Snapshot-Lesesperre durchführen: keine Löschung und kein Outbox-Commit vor
   Freigabe; danach dauerhafter korrekter Löschbeleg. Auf SQLite und einem
   isolierten PostgreSQL-Cluster testen. Session-/Familienrechte, abgebrochene
   Transaktionen, parallele Antwort-/Elternaktionen und Idempotenz mitprüfen.
3. Für die Worker-Aufbewahrung die lange Sammeltransaktion gesondert umbauen
   oder begründet belegen, dass kein anderer Pfad eine DB-Sperre hält, während
   er auf das Journal wartet. Parallelität mit laufendem Export und Cleanup
   unter begrenzten Testtimeouts prüfen.
4. Export und ACK nur mit erfolgreicher Outboxprüfung erlauben; DB-Ausfall und
   unbekannte Antwort bleiben Fehler. Nach vollständiger Pfadabdeckung den
   Gegenbeispieltest durch einen realen End-to-End-Racetest ersetzen. Status,
   Clock-Synchronisation, fehlende Journalgenerationen und Outbox nach Abstürzen
   bleiben weiterhin gesondert zu prüfen.
