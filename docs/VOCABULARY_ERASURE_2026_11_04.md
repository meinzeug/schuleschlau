# Wortschatz: Löschungen und Wiederherstellung

Stand 04.11.2026, lokale Umsetzung; kein Deployment und kein Zugriff auf echte
Kinderinhalte. Ein Wort, ein verworfener Vorschlag oder eine Sammlung konnte
bislang nach Wiederherstellung einer älteren Sicherung erneut erscheinen: Die
API entfernte die Zeile, erzeugte aber keinen Beleg im Löschjournal.

Die drei ausdrücklichen Löschaktionen erzeugen nun zusammen mit dem Entfernen
der Zeile einen Outboxbeleg. Auch die Löschung nach 365 Tagen erzeugt pro
betroffener Zeile genau einen Beleg. Das bestehende signierte Format verwendet
`scope=unit` mit `resource_kind=vocab_item`, `vocab_import` oder `vocab_set`;
der Beleg enthält zufällige IDs und Zeitpunkt, keine Wörter oder Inhalte. Der
Rückspielweg erkennt den Typ, löscht die konkrete Zeile und wendet die
Datenbankkaskaden an. Doppelte und anders sortierte Belege sind idempotent.
Wortlöschung entfernt Wiederholungszustand und Sammlungszuordnung; gespeicherte
Antworten und andere Wörter bleiben erhalten. Sammlungslöschung entfernt nur die
Sammlung und ihre Zuordnungen. Eine ausdrücklich gelöschte Sammlung mit
deterministischer ID kann während der Journalaufbewahrung nicht durch erneutes
Senden ihres alten Anlage-Schlüssels neu angelegt werden; eine neue Aktion
verwendet einen neuen Schlüssel.

**Kompatibilität vor einem späteren Release:** Ältere Restoreprogramme kennen
die neuen `resource_kind`-Werte nicht und müssen ab dem ersten neuen Beleg als
unvereinbar gelten. Zuerst Restore- und Prüfwerkzeuge auf den neuen Stand
bringen, inklusive der auf dem Sicherungsserver verwendeten Anwendung, und
isoliert anhand eines Journals mit den drei neuen Typen prüfen. Anschließend
Backups/Offsite-Abgleich und Wiederherstellung getrennt prüfen und erst danach
Code aktivieren, der die neuen Typen schreibt. Eine Rückkehr zu alten
Restorewerkzeugen ist unzulässig, solange neue Belege oder davon betroffene
Sicherungen vorliegen. Der Offsite-Client überträgt das verschlüsselte Journal;
eine erfolgreiche Übertragung belegt weder dessen Interpretation noch eine
Wiederherstellung. Keine Änderungen an produktiven Diensten erfolgten.

Die konkrete Reihenfolge für eine separat gepinnte Restore-Runtime, ihren
synthetischen Vorabtest und den Rückweg steht in
[RESTORE_RUNTIME_UPGRADE_2026_11_04.md](RESTORE_RUNTIME_UPGRADE_2026_11_04.md).

Das Journal wird nach 35 Tagen bereinigt; zulässige Sicherungen sind höchstens
14 Tage alt. Die künstlichen Tests prüfen einen 15 Tage alten Beleg, einen
abgelaufenen 36 Tage alten Beleg und wiederholtes Rückspielen in eine getrennte
Datenbank. Das ersetzt keinen Nachweis über eine tatsächlich vollständige
historische Journalfolge oder die Einhaltung externer Aufbewahrungsfristen.
Bereits vor der Umstellung ohne Beleg gelöschte Daten lassen sich nicht
nachträglich anhand dieser Änderung identifizieren. Andere direkt gelöschte
Datenarten und ihre Wiederherstellung bleiben gesondert zu prüfen.
