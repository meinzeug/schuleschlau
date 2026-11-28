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
Auch die aktuelle Wörterrunde und die Ergebniskarten mussten den Marker und
ausdrücklich unbekannte Zeiten berücksichtigen. Eine gespeicherte Hilfe bleibt
dabei als Hilfe sichtbar; bekannte Wiederholungen gelten nicht als
selbstständiger Erstversuch. Das ist mit künstlichen Widgetfällen geprüft.

Ein möglicher nächster Schritt ist ein ausdrücklich versionierter
Capability-Vertrag: Nur nachgewiesen kompatible Clients erhalten einen
unbekannten Zeitwert und erklären dessen Bedeutung; ältere Clients erhalten
für die betroffene Runde einen verständlichen Update-/Prüfhinweis. Für die
ungekürzte Übersicht muss zusätzlich ein mit alten Clients nachweislich
kompatibler Umgang mit einem einzelnen nicht darstellbaren Eintrag gefunden
werden. Solange dies nicht belegt ist, bleiben beide XFAILs offen. Eine
Capability selbst darf weder Rechte noch Datenfreigaben ersetzen.
Die globale Capability darf erst gesetzt werden, wenn sämtliche Wege, die
`unit_data` ausliefern (auch Start, Antwort, Lerncontroller, Heft-/Schultag und
Grafikposition), sowie alle quellen- und kompetenzgebundenen Projektionen mit
dem neuen Vertrag getestet sind. Ein isolierter Test von zwei GET-Endpunkten
belegt diese Voraussetzungen nicht.

### Tatsächlicher Altclient und weiterer Controller-Befund

Der historische Flutter-Stand `833f910` (App-Version `1.22.0+90`) wurde
separat ausgecheckt und mit dem künstlichen Widgetfall
`qa/nonfinite_legacy/client_833f910_test.dart` sowohl nativ als auch im echten
Chrome-Webrunner ausgeführt. Die Antwort wurde tatsächlich als JSON kodiert:
`created: null`, unverändertes `outcome: correct`, unverändertes
`assisted: false` und `independence_uncertain: true`. Der ursprüngliche Client
dekodiert sie ohne Absturz, zeigt aber tatsächlich „selbstständig“. Sein
Capability-Header enthält keine neue Zeitstempel-Capability. Ein erfolgreicher
Transport beweist hier also keine fachlich korrekte Darstellung.
Im selben historischen Widgettest zeigen Kinder- und Elternansicht eine
künstliche HTTP-409-Antwort mit verständlichem Text und einem erneuten Versuch
an. Das belegt den Dialog für **direkte Rundendetails** dieses konkreten
Clients; es ist kein implementierter Serververtrag und kein Nachweis für die
alte unkompakte Übersicht oder weitere installierte APK-Versionen.

Der Test ist ein **Fehlernachweis**, keine Sollvorgabe. Reproduktion: Einen
temporären Git-Worktree auf `833f910` anlegen, die genannte Datei in dessen
`app/test/` kopieren, dort die bereits vorhandenen Abhängigkeiten offline
auflösen und den Widgettest nativ sowie mit `flutter test -d chrome` ausführen.
Es werden ausschließlich künstliche Daten und `example.invalid` verwendet.
Der Teststand deckt genau diese historische App-Version ab, nicht sämtliche
installierten APKs. Im selben Stand setzt die Rundendetailansicht
`questions` als Liste voraus; eine Ersatzvorschau mit fehlendem oder erfundenem
leeren Inhalt ist daher kein nachgewiesener kompatibler Vertrag.

Zusätzlich wurde der reguläre `/learning-session`-Endpunkt mit künstlicher
Quelle und einem nicht-endlichen Antwortzeitpunkt geprüft. Zuvor zählte er die
Antwort als unabhängigen Erstversuch; der begrenzte Controller-Fix behandelt
diesen einzelnen Beleg nicht mehr als unabhängig und lässt seine gespeicherte
Antwort und Bewertung unverändert. Dies löst die zwei oben beschriebenen
Rundendetail- und Legacy-Übersichtsfehler nicht und erlaubt noch keine globale
Capability-Ankündigung.

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
