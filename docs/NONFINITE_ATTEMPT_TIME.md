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

Ein bloßes Ersetzen des ungültigen Werts durch `null` löst den Altclientkonflikt
nicht: Eine bereits veröffentlichte Elternansicht (beispielsweise Stand
`833f910`) bezeichnet `outcome=correct` und `assisted=false` unmittelbar als
„selbstständig“, auch bei `evaluation.independence_uncertain=true`. Die neue
Elternansicht berücksichtigt diesen Marker und ein ausdrücklich unbekanntes
Datum; nachgewiesene Unterstützung bleibt sichtbar. Bereits installierte alte
Clients erhalten diese Änderung jedoch erst durch ein Update. Ein Umsetzen
gespeicherter `outcome`- oder `assisted`-Werte wäre eine falsche Darstellung
der Originaldaten und ist keine sichere Kompatibilitätslösung.

Ein möglicher nächster Schritt ist ein ausdrücklich versionierter
Capability-Vertrag: Nur nachgewiesen kompatible Clients erhalten einen
unbekannten Zeitwert und erklären dessen Bedeutung; ältere Clients erhalten
für die betroffene Runde einen verständlichen Update-/Prüfhinweis. Für die
ungekürzte Übersicht muss zusätzlich ein mit alten Clients nachweislich
kompatibler Umgang mit einem einzelnen nicht darstellbaren Eintrag gefunden
werden. Solange dies nicht belegt ist, bleiben beide XFAILs offen. Eine
Capability selbst darf weder Rechte noch Datenfreigaben ersetzen.

Coaching-Beobachtungen behandeln betroffene Aufgaben als unklar, vergeben keine
datierten Prüferfolge daraus und berücksichtigen bei identischen Fragen deren
unklare frühere Exposition. Im kombinierten synthetischen Test blieben die
kompakte Heute-Seite und eine getrennte Fachrunde auf SQLite und PostgreSQL
verfügbar. Pauschale Ausnahmen im gemeinsamen Coaching wurden nicht eingebaut.
Quellengebundene Lernziel- und Kompetenzberechnungen und deren Abruf- und
Tagesplanung müssen nicht-endliche Zeiten und fachübergreifende Exposition noch
gesondert konservativ berücksichtigen; die Coaching-Prüfung belegt sie nicht.

Endliche, aber außerhalb der vom Datumsdienst unterstützten Kalendergrenzen
liegende Zeiten sowie Zeitangaben anderer Tabellen sind hier nicht abgedeckt.
Dies ist kein Freigabenachweis für die unbehobenen Funktionen.
