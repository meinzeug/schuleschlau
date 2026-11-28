# Nicht-endliche Versuchsdaten: geprüfter Teil und offene Lücken

Ältere `Attempt.created`-Werte können auf PostgreSQL NaN oder ±Infinity
enthalten. SQLite speichert ±Infinity, wandelt aber NaN zu SQL-NULL um; die
bestehende NOT-NULL-Sperre verhindert dort das Einfügen von NaN. Die Originale
werden bei dieser Behandlung weder überschrieben noch gelöscht.

Das Übungs-Ledger zählt Aufgaben mit mindestens einem nicht-endlichen Datum als
unklar; es behauptet weder selbstständigen Erfolg noch eine ermittelte letzte
Aktivitätszeit. Andere Aufgaben bleiben gezählt. Unbekannt datierte Aufgaben
werden bei datumsgefilterten Auswertungen nicht einem Zeitraum zugeordnet.
Mit künstlichen Daten blieben eine getrennte Runde und eine kompakte Heute-Seite
im getesteten Fall verfügbar. Dies ist kein Beweis für alle Heute-Konstellationen.

Die Korrektur ist ausdrücklich **nicht vollständig**: Rundendetail und ältere,
ungkürzte Übersicht können nicht-endliche Zeitstempel weiter in JSON ausgeben
und mit HTTP 500 scheitern. Der Start kann trotz anschließendem
Serialisierungsfehler bereits gespeichert sein. Eine bloße Sperre in der
allgemeinen Rundendatenfunktion würde auch alle Einträge der älteren Übersicht
blockieren. Eine Ersatzvorschau ohne `questions` wurde verworfen, weil ältere
Clients eine Aufgabenliste erwarten könnten und eine leere Ersatzliste falsche
Tatsachen vorgäbe. Beide Probleme sind als strikte XFAIL-Regressionen in
`test_nonfinite_attempt_time.py` reproduziert; sie sind nicht gelöst.

Auch Coaching-Beobachtungen, quellengebundene Lernziel- und
Kompetenzberechnungen sowie deren Abruf- und Tagesplanung müssen nicht-endliche
Zeiten für jede Aufgabe und fachübergreifende Exposition noch konservativ
berücksichtigen. Insbesondere darf ein zeitlich nicht einordenbarer Versuch
nicht als eigenständiger Erfolg oder neuer Prüftag gelten. Eine weitere strikte
XFAIL-Regression zeigt die bestehende Coaching-Fehlklassifikation. Pauschale
Ausnahmen im gemeinsamen Coaching wurden nicht eingebaut, weil sie die
Heute-Seite wegen einer einzelnen Altaufgabe blockieren könnten.

Endliche, aber außerhalb der vom Datumsdienst unterstützten Kalendergrenzen
liegende Zeiten sowie Zeitangaben anderer Tabellen sind hier nicht abgedeckt.
Dies ist kein Freigabenachweis für die unbehobenen Funktionen.
