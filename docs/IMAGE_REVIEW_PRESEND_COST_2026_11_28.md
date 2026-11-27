# Kostenbehandlung bei lokaler Bildprüfung

Der Auftrag zur unabhängigen KI-Prüfung reserviert sein Budget, bevor der
Worker das öffentliche Katalogbild für den Versand vorbereitet. Diese lokale
Vorbereitung dekodiert das Bild und erzeugt ein JPEG. Bisher konnte ein Fehler
dabei als Auftrag mit unbekannten Kosten enden, obwohl noch kein Anbieteraufruf
stattgefunden hatte. Auch als Fehler behandelte Pillow-Größenwarnungen wurden
nicht immer als ungültiges Bild eingeordnet.

Ungültige, übergroße oder lokal nicht konvertierbare Bilder führen nun vor dem
Netzwerkversand zu einem kontrollierten Fehlerbeleg mit null Kosten und
`cost_source=cancelled`. Die reservierte Summe wird in den vorhandenen
Buchungswegen genau einmal freigegeben; das Bild erhält keinen Prüfstatus
„bestanden“. Nur nachweislich lokale Fehler vor `client.stream` erhalten
diesen Beleg. Bei Transportfehlern und unklaren oder unvollständigen
Providerantworten bleiben die bestehenden konservativen Regeln für unbekannte
oder tatsächlich gemeldete Kosten erhalten.

Künstliche Tests prüfen fehlerhafte Bilddaten, hochgestufte Bildwarnungen,
Pillow-Größenfehler sowie leere und übergroße lokal erzeugte JPEGs. Der
Workerfall kontrolliert ausdrücklich, dass kein Transport aufgerufen wird,
der Auftrag fehlschlägt und nur seine eigene Reservierung genau einmal aus den
Kostenständen entfernt wird. Dies ist kein echter Anbieteraufruf und keine
fachliche Freigabe der Bildprüfung.

Die angrenzenden Bildprüf-, Bildauftrags- und Kostenfälle bestanden auf SQLite
mit 48 bestandenen und fünf übersprungenen sowie auf isoliertem PostgreSQL mit
51 bestandenen und zwei übersprungenen Fällen. Die fünf gezielten neuen
Fehlerfälle bestanden zusätzlich auf beiden Datenbanken. Die übersprungenen
Fälle umfassen optionale Umgebungs- beziehungsweise Livepfade; daraus folgt
kein Live-Anbieternachweis.

## Bilderzeugung: ungültige lokale Parameter

Die Bilderzeugung setzt den konservativen Versandmarker ebenfalls vor dem
Aufruf ihres Transportadapters. Der Adapter prüft Zugangsdaten, Modellroute und
öffentlichen Prompt lokal, bevor er `client.stream` erreicht. Wenn diese
Parameter ungültig waren, blieb zuvor die Reservierung als unbekannter Aufwand
stehen. Diese zwei expliziten Prüfstellen liefern nun einen Nullkostenbeleg für
einen nicht gesendeten Auftrag; die Anwendung rechnet ihn über den bestehenden
idempotenten Pfad ab. Wurde der Transport dagegen aufgerufen und schlägt fehl,
bleiben Kosten und Reservierung unbekannt. Tests verwenden künstliche Aufträge,
prüfen die eigenen Kosten-Buckets und zählen die Transportversuche. Sie zeigen
keine tatsächliche Anbieterantwort.

Nach der Ergänzung für die Bilderzeugung bestand die gemeinsame Suite aus
Bildvertrag, Bilderzeugung, Bildprüfung und Kostenkontrollen mit 68 Fällen auf
SQLite (fünf übersprungen) und 71 Fällen auf isoliertem PostgreSQL (zwei
übersprungen). Die künstlichen Fälle ersetzen keinen echten Anbieterbeleg.
