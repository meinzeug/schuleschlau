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
| `families.py:delete_child` | Kandidat: Journal → sortierte Units → volle Child-Sperre → Session und erneute Familien-/Passwortprüfung; Outbox-Commit unter Journal, Flush danach. Abweichende Unit-Menge nach Child führt zu 409. Unabhängige PostgreSQL-Tests reproduzierten zuvor zwei Deadlockrennen; die Gegenläufe prüfen den 409-Abbruch und eine blockierte FK-Einfügung. Falsches Passwort wird vor Journal abgewiesen und nach dem Sessioncheck nochmals geprüft. Weitere gleichzeitige Familien-/Lernaktionen bleiben vor Integration zu prüfen. |
| `families.py:delete_account`; Helfer `remove_child`, `remove_family` | Kandidat: Journal vor revisions- und sitzungsgeprüfter Kontolöschung, Commit darunter, Flush danach. Geteilte Familien bleiben wie beim Admin erhalten; letzte gemeinsame Inhaber erhalten 409. Entfernung einer erhaltenen Mitgliedschaft erhält einen Löschbeleg. Familienanruf-/Session-/Usage-Races und Berechtigungen wurden isoliert auf SQLite und PostgreSQL geprüft. Helfer werden auch vom Worker und Admin verwendet; keine verschachtelte Journalsperre. Weitere Cascade-/Retentionpfade bleiben zu prüfen. |
| `school_day.py:remove_page`, `material_actions.py:bulk_delete`, `materials.py:delete_material` | Neu: Journal vor Unit → Child → Session, Outbox-Commit darunter und Flush nach Freigabe. Kinder-Tagesseiten delegieren vor der Sperre, damit sie nicht verschachtelt erworben wird. Konkurrierende Snapshot-/Sitzungstests auf SQLite und PostgreSQL; Rechteverlust kann datensparsam als 401 oder 404 abgewiesen werden. |
| `source_cleanup.py:main --apply-digest` | Neu: expliziter Operator-Apply erwirbt das Journal vor der DB-Transaktion und Unit → Child; Flush nach Sperrfreigabe. Ein konkurrierender Test und bestehende Bereinigungs-/Restoretests bestanden jeweils auf SQLite und PostgreSQL. Das wiederverwendbare `apply` setzt voraus, dass jeder schreibende Aufrufer die äußere Sperre bereits hält. |
| `unit_actions.py:confirm` | Neu: Journal vor Unit → Child → Session; Outbox-Commit unter der Sperre, Flush danach. Tests prüfen sowohl die blockierte Snapshot-Konkurrenz als auch den Sitzungswiderruf während des Wartens; bestehende Unit-/Sessiontests auf SQLite und PostgreSQL erneut ausgeführt. |
| `admin_users.py:confirm_delete` | Kandidat: Journal vor der bestehenden revisions- und sitzungsgebundenen Admin-/Unit-/Child-Prüfung, Outbox-Commit darunter, Flush/Dateibereinigung danach. Unit-, Child-, User- und Session-Konflikte führen nach Rollback zu 409, bevor eine unter Family oder Child gehaltene Sperre einen Deadlock verursacht. Unabhängige synthetische PostgreSQL-Gegenläufe decken Usage-FK, tatsächliche Familienanrufe und späte Session-Inserts ab; weitere indirekte Cascades bleiben vor Integration zu prüfen. |
| `worker.py:maintenance` | Kandidat: Journal vor großer DB-Transaktion, Flush danach. Für abgelaufene Familien Token, Family, Units, Child, Users und Sessions in stabiler Reihenfolge mit NOWAIT sperren und Familien-, Unit- und Tokenstand nachprüfen; zusätzlich begrenzt PostgreSQL jeden einzelnen Lockwarteversuch auf 500 ms. Bei Konflikt wird diese DB-Transaktion vollständig verworfen und ein späterer regulärer Lauf übernimmt; vorher separat committe Grade-Outbox wird trotzdem geflusht. Alte Exportdateien werden erst nach erfolgreichem Commit und Flush entfernt. Echte synthetische PostgreSQL-Gegenläufe prüften Family-Call, eine abgelaufene Note, Outbox, Export und konfliktfreien Folgelauf. Der Timeout begrenzt weder die Gesamtlaufzeit noch jeden indirekten Cascadepfad; die lange globale Journalsperre und vollständige Aufteilung in Batches bleiben offen. |
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
