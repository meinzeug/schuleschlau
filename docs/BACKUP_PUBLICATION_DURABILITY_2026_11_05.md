# Veröffentlichungsreihenfolge für Sicherungsarchive

Der bisherige Backup-Writer schloss das verschlüsselte Archiv vor dem Rename,
aber er synchronisierte weder dessen Inhalt noch die Verzeichniseinträge der
Status- und Archivdatei ausdrücklich. Ein erfolgreicher Prozess belegte daher
allein keine beständige Veröffentlichung bei einem plötzlichen Stromverlust.

Unter der vorhandenen exklusiven Backup-Veröffentlichungssperre wird nun das
vollständig verschlüsselte temporäre Archiv einschließlich Authentisierungstag
synchronisiert. Sein Deskriptor bleibt bis nach dem Rename geöffnet; die
Dateiidentität wird geprüft. Der temporäre Name darf kein symbolischer oder
mehrfach verlinkter Dateieintrag sein und muss im Zielverzeichnis liegen. Der
Writer synchronisiert anschließend die Statusdatei, benennt sie um und
synchronisiert das Verzeichnis, bevor er das Archiv umbenennt. Nach dem
Archiv-Rename synchronisiert er das Verzeichnis erneut. Ein vorhandenes
Archiv einschließlich eines defekten symbolischen Links wird nicht ersetzt.

Jeder Sync- oder Identitätsfehler beendet den Auftrag mit Fehler. Wenn der
Status schon sichtbar ist, das Archiv aber noch nicht umbenannt wurde, kann ein
verwaister Status zurückbleiben. Scheitert der letzte Verzeichnis-Sync, ist das
Archiv bereits sichtbar, sein Dauerhaftigkeitszustand aber ungewiss: Es wird
nicht gelöscht oder als erfolgreicher Auftrag ausgegeben. Frühere Sicherungen
bleiben unangetastet. Eine Wiederaufnahme erfolgt ausschließlich über den
normalen Backupbetrieb; der Writer startet keine neuen Aufträge automatisch.

Offline-Tests prüfen die genaue Reihenfolge sowie künstliche Fehler an jedem
Sync, symbolische Links und alte Dateien; die bestehenden Journal-, Retention-,
Offsite- und Mountprüfungen laufen unverändert mit. Diese Prüfungen simulieren
keinen realen Stromausfall, keine defekte Hardware und keinen Restore. Die
Aussage hängt davon ab, dass Dateisystem, Blockgerät und Infrastruktur die
`fsync`-Zusagen tatsächlich einhalten. Ein erfolgreicher Backupservice beweist
weiterhin nicht, dass ein Löschjournal vorliegt oder dass ein Restore gelingt.

Bei einem Rückwechsel auf einen älteren Backup-Writer gilt diese
Sync-Reihenfolge für danach neu erstellte Sicherungen nicht automatisch. Das
bisherige Archiv-, Status- und Verschlüsselungsformat ändert sich nicht; nach
einem Rückwechsel müssen Sicherung und Wiederherstellung mit dem tatsächlich
aktiven Writer erneut geprüft werden.
