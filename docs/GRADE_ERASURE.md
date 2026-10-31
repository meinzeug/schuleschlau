# Notenlöschung und Wiederherstellung

Stand: 31.10.2026. Die Implementierung ist lokal getestet; das ist noch kein
Nachweis für eine erfolgte Produktionsumstellung oder eine lückenlose frühere
Löschhistorie.

## Löschung

Eltern löschen eine Note nach erneuter Rechteprüfung unter Kind- und
Notensperre. Die Transaktion entfernt die Note, ersetzt exakt zugeordnete
Importpositionen durch inhaltsfreie Platzhalter, leert zugehörige Slotwerte
und legt einen versionierten Löschauftrag in der Outbox ab. Für manuelle
Anfrageschlüssel schützt ein kindgebundener HMAC vor einer Wiederholung. Das
Journal enthält ausschließlich opake Kennungen und Positionen, keine Noten,
Fächer oder Freitexte. Änderungen am Installationsschlüssel benötigen einen
gesonderten Migrationsvertrag; alte HMACs werden nicht automatisch übertragen.

Seit Migration 0043 halten bestätigte Importe die genaue Beziehung zwischen
Note und Importposition fest. Für ältere Daten ist ein gleicher Rasterplatz
oder Wert kein hinreichender Beweis. In diesem Fall fragt die Elternansicht
für jede mehrdeutige Position ausdrücklich nach; ohne vollständige Auswahl
bleibt die Löschung gesperrt. Die Bestätigung ist revisionsgebunden. Laufende
PDF-Auswertungen werden verworfen, wenn sich der Notenkontext zwischenzeitlich
geändert hat. Elternziele und andere Noten bleiben erhalten.

Der Aufbewahrungslauf verwendet denselben Löschweg. Solange alte Quellen nicht
eindeutig zugeordnet sind, bleiben betroffene Noten vorübergehend erhalten;
der Worker protokolliert eine inhaltsfreie Anzahl betroffener Kinderkonten.
Ein noch mit einer vorhandenen Note verknüpfter Quellslot bleibt zur sicheren
späteren Zuordnung erhalten. Das kann die übliche 365-Tage-Frist überschreiten
und muss betrieblich verfolgt werden; eine ungeklärte Zuordnung ist kein
Nachweis fristgerechter Löschung.

## Restore und Betrieb

Ein authentifizierter Notenbeleg verweist auch auf Importpositionen, deren
Verknüpfung erst nach einem Backup bestätigt wurde. Ein neuer Restore-Leser
redigiert diese Positionen und entfernt die Note; ältere Leser lehnen die
neuen Ressourcentypen ab. Import- und Slotablauf erhalten eigene Belege.
Migration 0044 ergänzt die versionierten Outbox-Details; eine Rückstufung mit
vorhandenen Details wird verweigert. Nach einer Schemaänderung sind ein
kompatibler Code-Rückweg und ein getesteter neuer Restore-Leser erforderlich.
Ein alter Worker darf neue Noten-Outboxeinträge nicht verarbeiten.

Die Restoreprobe liest unter der Journalsperre zusätzlich die aktuelle
Produktions-Outbox und verweigert den Abschluss bei unveröffentlichten
Löschaufträgen. Eine bei Ausfall des Produktivsystems verlorene Outbox lässt
sich dadurch nicht rekonstruieren. Auch ein vorhandenes signiertes Journal
belegt nicht, dass historische Einträge vollständig sind. Ohne belegbare
Journal- und Outboxhistorie darf keine Löschkonformität behauptet oder ein
Stand ungeprüft produktiv freigegeben werden. Vor einer tatsächlichen
Wiederherstellung sind die Schreibdienste kontrolliert anzuhalten, der
aktuelle externe Journalstand und seine Herkunft abzugleichen und die
Wiederherstellung zunächst in einer separaten Datenbank zu prüfen.

Historische Einzellöschungen ohne Notenjournal sind nicht rückwirkend durch
den neuen Code belegt. Die vorhandenen Sicherungszeiträume, Auditbelege und
etwaige Kopien müssen vor produktiver Freigabe gesondert geprüft werden;
Beziehungen dürfen nicht aus gleichem Wert erraten werden. Für einen Rollout
sind Schema, API, Worker und Restorewerkzeuge abgestimmt auszuliefern und
anschließend ein echter isolierter Restore mit aktuellem Journal zu prüfen.
