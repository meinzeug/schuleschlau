# Datenlebenszyklus: nachprüfbare Teilabnahme

Stand 04.11.2026. Alle genannten Läufe verwenden künstliche Konten und Inhalte
in lokalen Testdatenbanken. Es wurden keine produktiven Daten kopiert oder
verändert. Ein Test belegt den genannten Ausschnitt, nicht die vollständige
Produktionsfreigabe des gesamten Datenlebenszyklus.

| Datenart | Ausgeführter Beleg | Aussage und Grenzen |
| --- | --- | --- |
| Familien, Quellen und Fotos | `test_operations.py::test_authenticated_erasure_journal_reconciles_a_separate_snapshot`; `test_private_images.py` | Künstliche Familienlöschung, signiertes Journal und Replay in separater SQLite-Kopie; Fotoausgabe/Export gegen Pfadflucht und Symlinks. Kein Nachweis eines vollständigen Produktions-Restore. |
| Tutor-Zitate | `test_tutor.py::test_deleting_a_source_purges_quotes_in_day_and_unit_scopes` | Quellenlöschung entfernt getestete Zitate für Tages- und Einheitenkontext. Keine allgemeine Aussage zu externen Providerkopien. |
| Antworten und Lernrunden | `test_operations.py::test_expired_learning_unit_is_journaled_and_not_resurrected_by_restore` | Alte künstliche Runde verschwindet beim Ablauf und im älteren Restore; aktuelle Kontrollrunde bleibt. |
| Wortschatz, Vorschläge, Sammlung | `test_vocabulary_erasure_restore.py`; `test_language_jobs.py::test_source_deletion_purges_import_items_and_projects` | Ausdrückliche Löschung und 365-Tage-Ablauf erhalten signierte Belege; Replay entfernt Wiederholungen/Zuordnungen, erhält getrennte Kinder, Quellen und Antworten. Details und zwingende Restore-Kompatibilität: [Vokabel-Löschjournal](VOCABULARY_ERASURE_2026_11_04.md). |
| Noten und lokale PDF-Vorschau | `test_grades.py::test_export_and_account_erasure_include_grades`; `test_grade_pdf_imports.py::test_import_preview_confirmation_repeat_export_delete_and_no_ai` | Noten im berechtigten Export und Löschung des Testkontos; künstlicher PDF-Import und Vorschau ohne KI. Historische Quellen- und Wiederherstellungsgrenzen siehe [Notenlöschung](GRADE_ERASURE.md). |
| Klassenarbeitsnacharbeit | `test_exam_lifecycle.py::test_actual_source_delete_and_restore_replay_remove_private_review_derived_rows` | Testquelle und abgeleiteter Bericht werden entfernt; fremde Quelle und Kostenbeleg bleiben. |
| Zahlungsbelege | `test_payment_documents.py::test_family_owner_export_keeps_receipt_but_viewer_has_no_financial_declaration` | Nur berechtigter Familieninhaber erhält die getesteten Belege im Export. Dies ist keine steuerliche Prüfung der gesetzlichen Aufbewahrungsfrist. |
| Profilfotos | `test_profile_images.py::test_exports_include_only_authorized_profile_photos_and_without_photo_option`; `test_unavailable_avatar_is_visible_in_export_and_fifo_does_not_block` | Getrennter Eltern-/Kinderexport, Fotooption und Anzeige nicht lesbarer Profilbilder. Kein Anspruch, dass eine beschädigte Datenbank die Dateieigentümerschaft beweist. |
| Löschjournal bei Dateifehler | `test_deletion_journal_safety.py`; `test_admin_users.py::test_delete_cleanup_error_replay_does_not_claim_files_removed` | Bei manipuliertem Uploadverzeichnis wird der Datenbankbeleg zunächst signiert; Dateifehler melden keinen bestätigten Löschabschluss. |
| Ablauf von Tutor-, Schulbuddy- und Elternrückblicken | `test_restore_conversation_retention.py` | Am 05.11. jeweils neun künstliche Fälle auf SQLite und isoliertem PostgreSQL: bestehender strikter Cutoff im Wartungslauf, beide Restore-Ausführungspfade und signierte Journale, Zurückweisung manipulierter Journale, Schemalücke und dokumentierte Kaskaden. Die beiden Restore-Zieldatenbanken der Tests sind separate SQLite-Dateien; die automatische Probe wird mit gestubbter Migration ausgeführt. Kein Produktions-Restore und kein Beleg für die Vollständigkeit des Löschjournals. |

Ein zusammengefasster SQLite-Lauf vom 04.11. umfasste vier Vokabel- und neun
weitere ausdrücklich gewählte Fälle (13 bestanden). Ein isolierter
PostgreSQL-Lauf umfasste vier Vokabel- und zwei quellgebundene Sprachfälle
(sechs bestanden); seine Restore-Zieldatenbank in den Vokabeltests war separat
und verwendete SQLite. Für die zuvor durchgeführten Bild-/Journalprüfungen
standen zusätzlich gezielte SQLite- und PostgreSQL-Fälle zur Verfügung.

Offen bleiben insbesondere eine vollständige aktuelle Export-/Löschmatrix für
jede Datenart und jeden Endpunkt, die Wiederherstellung weiterer direkt
abgelaufener oder gelöschter Datenarten wie Nachrichten und sonstiger privater
Metadaten sowie die tatsächlichen Aufbewahrungs-, Lösch- und Logfristen bei
Hosting, KI-Anbietern, Support und Proxys. Aus dem lokalen Test ergibt sich
keine unabhängige Datenschutz- oder Rechtsabnahme. Der übergeordnete
Roadmap-Punkt bleibt offen.
