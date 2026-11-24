# Schulbuddy: automatisierter Browserablauf

Der am 24.11.2026 ergänzte Test verbindet die Flutter-Weboberfläche bei
390 × 844 Pixeln mit einem lokalen FastAPI-Server und einer automatisch
isolierten SQLite-Datenbank. Ein künstliches Kind öffnet eine bestätigte
künstliche Heftseite, startet Schulbuddy und sendet eine Frage. Der reguläre
Auftragspfad reserviert und verarbeitet genau einen Auftrag; lediglich der
Providertransport liefert eine feste künstliche Antwort. Im Browser erscheinen
Antwort und Quellenzitat. Nach erneutem Öffnen sind beide noch vorhanden,
ohne dass ein weiterer Auftrag gesendet wird. Ein fremdes Familienkonto darf
die gespeicherte Antwort nicht lesen. In der Datenbank entstehen weder
Aufgabenversuche noch Kompetenznachweise.

Der Worker wird ausschließlich im lokalen Testprozess über eine an Loopback
gebundene, mit Zufallstoken geschützte Testroute gestartet. Die Route wird beim
Beenden entfernt und ist kein Bestandteil der Anwendung. Der Browser sperrt
fremde Netzwerkziele; die Startumgebung enthält weder Anbieterschlüssel noch
externe Datenbankeinstellungen. Das Test-Opt-in verwirft eine angegebene
`TEST_DATABASE_URL` vor dem Laden der Anwendung. Ohne Opt-in wird der
Browserfall vor Aufbau der Providerfixture übersprungen.

Die Fälle sind Bestandteil von `qa/run_notebook_local_browser.py`; sein
JUnit-Vertrag lehnt fehlende, doppelte, fehlgeschlagene und übersprungene
Pflichtfälle ab. Für einen isolierten lokalen Lauf zuerst den Flutter-Webbuild
erstellen und anschließend `python qa/run_notebook_local_browser.py --web-dir
app/build/web` im Repository ausführen.

Der Test belegt keine echte KI-Ausgabe, keine fachliche Vollständigkeit über
alle Themen und keine Android- oder Pushzustellung. Diese Abnahmen bleiben
separat. Er verwendet keine echten Kinderdaten und keinen externen Anbieter.
