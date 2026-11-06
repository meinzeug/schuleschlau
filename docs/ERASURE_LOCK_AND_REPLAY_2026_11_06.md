# Löschbelege und isolierter Replay: begrenzte Absicherung

Der normale SQLAlchemy-Weg auf dem Anwendungspool verweigert neue
`ErasureRequest`-Einträge und deren Commit ohne dieselbe während der gesamten
Transaktion gehaltene Journal-Schreibsperre. Das umfasst `request`, ORM-Flush,
SQLAlchemy-Insert auf der Session oder Connection, Legacy-Bulk-Inserts und
OptionEngines desselben Pools. Eine explizite AUTOCOMMIT-Option wird für diese
Inserts abgelehnt. Kopierte Ausführungskontexte und andere Threads können eine
nach Sperrende beziehungsweise auf einem anderen Thread verwendete Sperre
nicht wiederverwenden. Nach fehlgeschlagenem Commit bleibt die Verbindung bis
zum Pool-Reset geschützt; dort wird vor Freigabe ein physischer Rollback
ausgeführt. Die Listener werden beim Import der Anwendungsdatenbank
registriert; eine separat erzeugte Restore-Engine bleibt für den Import alter
Daten nutzbar.

Replays von Familien-, Kinder- und Material-Löschbelegen führen die
Datenbankänderungen aus, legen aber keine neuen Löschbelege an und löschen
keine Dateien im Diagnoseverzeichnis des laufenden Betriebs. Vorhandene
Diagnosebezüge in der wiederhergestellten Datenbank werden weiterhin bereinigt.

Die synthetischen Tests prüfen abgelehnte Schreib- und Commitpfade,
Sperrwechsel, Pool-Wiederverwendung, getrennte Restore-Engine und erhaltene
Diagnosedateien für alle drei Replayarten. Ein zurückgerollter Savepoint kann
den äußeren Commit konservativ weiterhin sperren; derzeit ist kein
Löschbelegpfad in den vorhandenen Savepoints bekannt. Rohes SQL, direkte
DBAPI-Zugriffe, zweiphasige Transaktionen, Prozesse älterer Releases und andere Engines sind keine durch
diese Hooks geschützten Wege. Der Export muss außerdem unveröffentlichte
Outboxeinträge prüfen und eine Offsite-Bestätigung an genau den exportierten
Journalstand binden. Diese Änderung ist **kein** Beleg eines vollständigen
Offsite-Restores oder eines sicheren Versionswechsels.
