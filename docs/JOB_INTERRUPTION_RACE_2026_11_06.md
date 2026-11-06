# Abbruch und verspätete KI-Antwort

Stand: 6. November 2026. Ein künstlicher Paketauftrag lief im regulären
Worker auf isoliertem PostgreSQL. Der Worker las nach der Modellantwort den
Status `running`; unmittelbar danach markierte die Wartung den seit über
240 Sekunden laufenden Auftrag als unterbrochen und behielt dessen unbekannte
Kosten reserviert. Vor der Korrektur veröffentlichte der Worker anschließend
trotzdem das Ergebnis und überschieb `failed` mit `completed`. Die gespeicherte
Abrechnung blieb dabei `failed_unknown`. Dies wurde ohne Netzaufruf,
Produktionsdaten oder tatsächliche Kinderantworten reproduziert.

Alle gewöhnlichen ORM-Änderungen am `Job` verwenden nun den zuvor gelesenen
Status als optimistischen Vergleichswert. Wird ein Auftrag inzwischen beendet,
abgebrochen oder gelöscht, schlägt der veraltete Schreibversuch fehl und seine
gesamte Datenbanktransaktion wird zurückgerollt. Massenupdates müssen weiterhin
ihre eigenen Statusbedingungen enthalten; der Schutz beweist nicht, dass ein
künftiger unbedingter SQL-Massenupdate sicher wäre. Es sind keine neue Spalte
und keine Migration nötig. Bestehende Einheiten, Antworten und Kostenbelege
werden nicht nachträglich umgeschrieben. Dies setzt voraus, dass ein beendeter
Job nicht erneut auf `running` gesetzt wird.

Der allgemeine Reaper liest höchstens 100 Kandidaten und überprüft Status,
Beginn und Typ beim Schreibzugriff erneut atomar. Jeder Abbruch und seine
Kostenbuchung laufen in einer kurzen gemeinsamen Transaktion. Der spezielle
Asset-Reaper behält seine eigene `Child → Build → Job`-Reihenfolge. Erfolgreiche
Worker markieren den Job vor der Buchung im selben Datenbank-Commit; damit
sperren sie Job und Usage in der gleichen Reihenfolge wie der allgemeine
Reaper. Die fachliche `LearningUnit → Child`-Sperrreihenfolge bleibt bestehen.
Fehlerhandler dürfen einen bereits abgeschlossenen oder unterbrochenen Auftrag
nicht mit einem verspäteten Fehler überschreiben. Kein automatischer erneuter
Anbieteraufruf und kein neuer Anbieterwechsel wurden ergänzt.

Zwei mit Threads synchronisierte PostgreSQL-Fälle prüften beide Reihenfolgen:
Ein unterbrochener Auftrag veröffentlicht keine verspätete Paketantwort;
ein bereits abgeschlossenes Paket und seine einmalige bekannte Kostenbuchung
überstehen den zuvor ausgewählten Reaper-Kandidaten. Zusätzlich wurden der
späte Fehler, der transaktionale Rücklauf mit erhaltenem künstlichem
Antwortbeleg und bestehende Workerpfade geprüft. Im breiten Lauf bestanden
273 SQLite-Fälle (fünf umgebungsspezifisch übersprungen) und 103 Fälle auf
einem kurzlebigen isolierten PostgreSQL. Der künstliche Anbieter war simuliert.
Die Tests umfassen nicht alle möglichen Worker- oder Datenbankrennabläufe.

Ist der Reaper schneller als die tatsächliche Modellantwort, bleibt die volle
Reservierung als unbekannt erhalten. Das Paket wird nicht übernommen. Ein
verspätetes Providerergebnis wird im allgemeinen Paketpfad nicht als
Kostenbeleg nachgetragen; ein vorhandener Generierungsbeleg kann über den
bestehenden Abgleich verarbeitet werden. Diese Einschränkung gilt weiter.

## Ergänzende Prüfung auf Status-Neuladen und Prüfungsabbruch

Eine unabhängige Gegenprüfung fand ein zweites konkretes Rennen: Vier Worker
leeren nach ihrer ersten Statusprüfung den ORM-Cache. Vor der Ergänzung konnte
ein dazwischen abgebrochener Job deshalb mit dem neu geladenen `failed` als
Vergleichswert wieder abgeschlossen werden. Auch dieses Verhalten wurde mit
einem tatsächlichen Grafikworker und künstlicher Ausgabe auf getrenntem
PostgreSQL reproduziert. Alle vier Stellen prüfen nach dem Leeren des Caches
erneut auf `running`; danach bleibt der Vergleichswert bis zur Änderung
bestehen. Eine spätere Statusänderung löst wie oben den Transaktionsrücklauf
aus. Die besonderen Asset- und Materialprüfungen prüfen den aktualisierten
Jobstatus bereits. Das betrifft keine Aussage über unbedingte SQL-Updates.

Alle acht vorhandenen `update(Job)`-Aufrufstellen begrenzen ihre Übergänge durch
Statusprädikate. Die normale Wiederholung eines unterbrochenen Paketjobs legt
einen Auftrag mit neuer ID an; der alte `failed`-Status und dessen unbekannter
Verbrauch bleiben bestehen. Ein neuer unbedingter SQL-Übergang oder eine
manuelle Reaktivierung von `failed` zu `running` würde diesen Schutz aushebeln;
die Untersuchung ist kein Datenbank-Constraint gegen solche Änderungen.

Bei der Löschung einer Klassenarbeitsquelle werden laufende Analyse- und
Nacharbeitsjobs nun atomar als `failed_unknown` abgerechnet, ohne die
Reservierung freizugeben oder eine kostenlose Ausführung zu behaupten.
Wiederholte Löschung bucht nicht erneut. Ein angehaltener künstlicher
Anbieteraufruf kann danach keinen Bericht übernehmen. Für noch nicht gestartete
Aufträge bleibt der bestehende Nullkostenweg erhalten. Der No-op-Paketpfad
setzt den Jobstatus vor der Kostenbuchung und verwendet damit ausdrücklich die
gleiche Job→Usage-Reihenfolge wie der Reaper.

Nach diesen Ergänzungen bestanden 14 gezielte Tests auf isoliertem PostgreSQL
und 11 auf SQLite (dort zwei PostgreSQL-Rennen übersprungen). Die breiteren
Läufe von zuvor wurden nicht als vollständig neu ausgeführt ausgewiesen; ein
historischer Test zur Prüfungsbuchung wurde auf den verbesserten Zustand
`failed_unknown` bei unveränderter Reservierung aktualisiert und ist in beiden
gezielten Läufen enthalten.
