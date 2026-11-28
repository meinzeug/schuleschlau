# Löschjournal: nachstellbare Grenzen des Vollständigkeitsnachweises

Stand: synthetische lokale Gegenversuche; keine Produktionsdaten, kein
Serverzugriff und keine Freigabe einer Wiederherstellung.

`scripts/tests/test_audit_erasure_journal.py` vergleicht eine künstliche,
signierte Journaldatei mit einer getrennten SQLite-Outbox. Fehlt ein dort
vorhandener Löschbeleg nur im Journal, meldet das Audit eine fehlende
Journalzeile; fehlt ein signierter Journalbeleg nur in der Outbox, meldet es
einen fehlenden Outboxbeleg. Fehlt derselbe Beleg dagegen in **beiden**
Beständen, sehen die übrigen, gültigen Einträge bei diesem Vergleich
vollständig aus. Trotzdem bleiben `historical_completeness_verified`,
`writer_fence_verified` und `restore_activation_authorized` auf `false`.

Für diesen Doppelverlust spielt der Test die authentifizierten vorhandenen
Belege in eine weitere, ausschließlich künstliche In-Memory-Datenbank ein.
Darin bleibt eine zuvor gelöschte synthetische Familie aus dem alten
Datenstand erhalten. Der im Test bekannte, signierte fehlende Beleg entfernt
sie hingegen beim erneuten Abgleich. Das zeigt die Ursache der Gefahr; es
rekonstruiert weder eine reale Löschung noch einen unbekannten Beleg. Der Test
weist keine vollständige Abdeckung sämtlicher Datenarten oder anderer
Wiederherstellungswege nach.

Ein separater Monitortest versieht einen technisch gültigen künstlichen
Prüfbericht mit erfundenen Behauptungen über Vollständigkeit, Writer-Fence,
Offsite-ACK und Aktivierung. Der Monitor muss trotzdem
`restore_journal_completeness_unverified` ausgeben. Ein tatsächlich
überprüfter ACK bindet den Export an einen Stand zum Prüfzeitpunkt; er beweist
keine frühere lückenlose Historie oder einen dauerhaften Schreibstopp.

Für einen echten Freigabeweg fehlen weiterhin ein unabhängig belegter
vollständiger Ausgangspunkt, Abdeckung aller Lösch- und Retentionwriter,
eine verlässlich extern verankerte fortlaufende Bindung von Datenbank und
Journal, ein koordinierter Fence beider Hosts und die gesonderte Prüfung der
älteren weiterhin gültigen Sicherungen. Einzelne gültige Signaturen, ein
leerer Outboxstatus und eine geglückte isolierte Wiederherstellung ersetzen
diese Nachweise nicht. Ein möglicher künftiger Anker kann nur für den nach
seiner nachgewiesenen Einführung abgedeckten Zeitraum sprechen; er kann eine
unbekannte historische Löschung nicht rückwirkend beweisen.
