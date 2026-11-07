# Fehlgeschlagene Aktivierung: keine automatische Rückkehr

Der Fehlerpfad von `deploy/activate.py` bittet systemd nach einem begonnenen
Writer-Stopp oder einem möglichen Start neuer Writer, API und Worker
anzuhalten. Ein fehlgeschlagener Stopp wird gemeldet; ein erfolgreiches
`systemctl stop` belegt für sich weder den Drain aller Prozesse noch das Ende
aller Datenbanksitzungen. Die Unitdateien und der `current`-Verweis werden im
Fehlerpfad nicht zurückgesetzt. Insbesondere darf ein fehlgeschlagener Stopp
nicht dazu führen, dass laufender Code unter einem anderen Releasepfad weiter
arbeitet. Alte Dienste oder ein vorheriger Fotodienst werden nicht automatisch
neu gestartet. Nach einem Migrationsversuch bedeutet auch eine gleiche
Schema-Revision nicht, dass keine Daten geändert wurden.

Caddy-Hauptdatei und Fragment werden unabhängig voneinander bestmöglich
zurückgeschrieben. Scheitert ein Schritt, wird der andere trotzdem versucht
und der ursprüngliche Aktivierungsfehler weitergegeben. Ein fehlgeschlagener
Reload-Rückgabecode wird gemeldet. Ein Caddy-Reload wird
nur nach erfolgreicher Rückschreibung beider Dateien angefordert; ein
fehlgeschlagener Reload muss getrennt untersucht werden. Vor einem begonnenen
Writer-Stopp berührt der Fehlerpfad weder API-/Worker- noch Fotozustand. Dieses
Vorgehen erhält nach Fehlern bewusst weniger Verfügbarkeit als ein
automatischer Neustart. Vor einer expliziten Wiederaufnahme müssen Betreiber
Releaseverweis, tatsächlich geladene Units, alle Prozessgruppen, laufende
Datenbanksitzungen, Schema, Daten, Decoder sowie Timer und Backupzustand
prüfen. Timer werden durch den Fehlerpfad nicht auf den vorherigen Zustand
zurückgesetzt; bereits gestartete Timer können weiterlaufen.

## Erstinstallation

Fehlt `current`, wird sie nur nach separater Prüfung als leer behandelt:
keine der bekannten Units darf vorhanden, aktiv oder in einem Job sein;
`/var/lib/schulpilot` muss das beim regulären Bootstrap angelegte leere
`uploads`-Verzeichnis und sonst keine Inhalte enthalten; die lokale
`schulpilot`-Datenbank muss über eine explizite Unix-Socket-Verbindung leer
sein und darf keine weiteren Client-Sitzungen oder vorbereiteten Transaktionen
haben. Die root-kontrollierte Environment-Datei muss exakt die zuvor geprüfte
Bootstrap-Datenbank und das geprüfte Datenverzeichnis benennen; PG-, Python-
und Loader-Umleitungen werden abgewiesen. Ihre unveränderten Bytes und Werte
werden unmittelbar vor der Migration erneut geprüft und genau diese Werte für
den Migrationsprozess verwendet. Der Systemaufruf erbt keine libpq-Umgebung. Fehlende oder mehrdeutige
Zustände führen zum Abbruch vor Konfigurationsänderung und Migration. Ein
beschädigter, nicht lesbarer oder nicht-symlinkartiger Current-Verweis ist kein
Beleg für eine neue Installation. Ein durch den regulären Bootstrap neu
angelegtes leeres Konto/Datenverzeichnis/Datenbank bleibt initialisierbar.

Die Tests prüfen den echten Fehlerhandler mit synthetischen Dateien und
systemctl-Stellvertretern, inklusive fehlgeschlagenem Stopp, unabhängig
fehlgeschlagenen Caddy-Wiederherstellungen und unverändertem Releaseverweis.
Zudem prüfen Tests den Erstinstallationsvertrag sowie einen künstlichen
leeren und danach gefüllten PostgreSQL-Cluster mit echter lesender
systemd-Abfrage. Eine abschließende vollständige Installation auf einem neuen
Produktivhost ist damit nicht belegt.

Diese Änderung ist kein dauerhafter Startzaun. Ein SIGKILL oder Stromverlust
führt nicht durch den Fehlerhandler; systemd-Timer, direkte Programme, andere
Hosts, Altprozesse und zukünftige Verbindungen sind dadurch nicht vollständig
ausgeschlossen. Die Erstinstallationsprüfung ist eine Momentaufnahme und
keine Sperre gegen privilegierte gleichzeitige Änderungen. Kein Teil dieses
Fixes autorisiert für sich einen produktiven Cutover.
