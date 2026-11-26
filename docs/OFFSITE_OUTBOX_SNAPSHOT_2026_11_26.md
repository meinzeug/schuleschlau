# Offsite-Journal: ausstehende Löschbelege vor Export erkennen

Der bisherige Export verschlüsselte das lesbare Journal unter der gemeinsamen
Journalsperre, prüfte aber die Datenbank-Outbox nicht. Ein zuvor committeter,
noch nicht ins Journal veröffentlichter Löschbeleg konnte daher beim Export
fehlen. Der bestätigende ACK prüfte ebenfalls nicht auf solche wartenden Belege.
Eine Lesesperre allein beweist auch keine vollständige historische Löschkette.

Der neue Stand fragt unmittelbar nach Erwerb der Journalsperre den regulären
Outboxstatus ab. Eine nicht veröffentlichte Zeile, eine unbekannte Antwort
oder ein Abfragefehler verhindert den Export vor Ausgabe des Ciphertext-Headers.
Beim ACK wird die Prüfung nach dem bereits vorhandenen Backup-Identitätscheck
und vor einem Erfolgsmarker wiederholt. Die PostgreSQL-Abfrage ist lesend,
transaktionsweit schreibgeschützt und mit Statement- und Sperrtimeout begrenzt;
fehlende oder ungültige Ergebnisse gelten nicht als sauber. Bereits gesicherte
Archive und frühere Offsite-Kopien werden dadurch nicht überschrieben.

Künstliche Dateitests prüfen die gehaltene Journalsperre, ausstehende und
unbekannte Ergebnisse, erhaltene alte ACK-Marker und neutrale Fehler. Auf einem
kurzlebigen isolierten PostgreSQL-Cluster wurden eine leere, eine ausstehende
und eine veröffentlichte Outbox sowie ein echter blockierender Tabellenlock
geprüft; die Abfrage scheiterte begrenzt und funktionierte nach Freigabe wieder.
100 künstliche Sicherungs-/Restore-/Offsitefälle und 34 Unterfälle bestanden.

Dies ist **keine Freigabe einer Wiederherstellung** und kein Nachweis für eine
vollständige Löschhistorie. Der noch vorhandene ACK-Vertrag bindet die
Bestätigung nicht an die Bytes des konkret zuvor exportierten Journals: Ein
nach dem Export neu veröffentlichter Löschbeleg kann vor dem ACK liegen.
Roh-SQL/alte Prozesse ohne Journalsperre, zwei Hosts, unterbrochene Pulls und
ältere Versionen bleiben gesondert zu behandeln. Die Änderung ist lokal
geprüft und noch nicht produktiv ausgerollt.
