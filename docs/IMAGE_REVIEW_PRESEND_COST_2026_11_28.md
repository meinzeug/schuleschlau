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
