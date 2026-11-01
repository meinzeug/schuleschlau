# Notenlöschung und Wiederherstellung

Stand: 01.11.2026. Die Implementierung ist mit Release `1.38.57+212`,
Quellcommit `669ae59`, aktiv; Schema `0044` und eine authentifizierte
isolierte Restoreprobe mit aktuellem Journal wurden auf dem Zielserver
geprüft. Das belegt keine lückenlose frühere Löschhistorie.

Der produktive Worker wurde mit einer ausdrücklich synthetischen, gesperrten
Testfamilie und einer 366 Tage alten Note geprüft. Er redigierte zwei mögliche
Importkopien, behielt eine jüngere Vergleichsnote und veröffentlichte den
authentifizierten Löschbeleg. Die Testfamilie wurde anschließend über den
journalisierten Familienlöschweg entfernt. SQLite und isoliertes PostgreSQL
prüfen zusätzlich das Abgleichen eines vor der Löschung erstellten Snapshots.

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

Der Aufbewahrungslauf verwendet denselben Löschweg. Bei Ablauf einer Note
entfernt er auch alle nicht anderweitig belegten Importpositionen am passenden
historischen Tabellenplatz. Diese vorsorgliche Redigierung behauptet keine
gesicherte Herkunft und kann auch eine noch junge Importvorschau betreffen;
andere Noten und ausdrücklich mit anderen Noten verknüpfte Positionen bleiben
erhalten. Die Positionen werden im signierten Löschjournal aufgeführt, damit
auch ein älterer Snapshot die möglichen Kopien nicht wiederherstellt. Bei
manueller Löschung gilt weiterhin die ausdrückliche Elternprüfung.

Beschädigte oder widersprüchliche Quellstrukturen können weiterhin nicht
automatisch sicher verarbeitet werden; der Worker protokolliert eine
inhaltsfreie Anzahl betroffener Kinderkonten. Die Elternansicht kennzeichnet
Noten nach Ablauf der Frist und bietet die Prüfung und Entfernung an.
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
