# Einstellungen: veraltete ORM-Daten nach Zeilensperre

Ein Schreibaufruf für Betriebseinstellungen sperrt zunächst den gemeinsamen
Installationsdatensatz. War derselbe Datensatz bereits in seiner SQLAlchemy-
Session geladen und wurde zwischenzeitlich durch eine andere Session geändert,
lieferte `db.get` dennoch das alte ORM-Objekt. Eine danach gespeicherte
Teiländerung konnte unbeteiligte ältere Einstellungen übernehmen; in der
künstlichen Gegenprobe wurde dadurch ein abgeschlossener Widerruf wieder auf
Freigabe gesetzt. Umgekehrt konnte eine spätere Freigabe verlorengehen.

Nach der Sperre wird der Datensatz nun explizit aus der Datenbank aufgefrischt,
bevor die Teiländerung eingemischt wird. Dies ändert weder die vorgesehenen
Rollen- und Rechteprüfungen noch bestehende Kontingente oder Einwilligungen.

## Nachweise und Umfang

Die künstlichen Tests laden den Datensatz vorab und bestätigen einen
zwischenzeitlichen Widerruf beziehungsweise eine Freigabe in separater Session.
Beide Richtungen werden auf SQLite und PostgreSQL geprüft. Zusätzliche
PostgreSQL-Fälle verwenden die echten HTTP-Routen und zwei verschränkte
Requests. Eine künstliche Request-Dependency hält gezielt das zuvor geladene
Objekt in der jeweiligen Session; die Tests belegen die Lücke für eine solche
Einbettung, nicht, dass die derzeitige Middleware im regulären Betrieb die
Referenz tatsächlich hält. Vor der Korrektur schlugen beide HTTP-Gegenfälle
fehl; danach bleiben aktueller Freigabewert und eine gegebenenfalls vorhandene
Tutor-Freigabegeneration erhalten. Die vier Fälle sind für die PostgreSQL-CI
verbindlich. Es wurden weder Kinderdaten noch Provideranfragen verwendet.

Dies ist kein Ersatz für einen revisionsgebundenen Abgleich veralteter
Adminformulare, einen Restore-Schutz für Freigaben oder die Prüfung von
Alteinträgen. Die neue Tutor-Generationsbindung ist nicht Teil dieses Fixes.
