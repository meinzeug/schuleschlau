# Paketvorbereitung: HTTP-Fehler durch Adapter und Worker

Stand: 5. November 2026. Die Tests verwenden ausschließlich synthetische Daten
und einen lokalen `httpx.MockTransport`; es findet kein Netzaufruf statt. Der
reguläre Worker verarbeitet drei Paketabschnitte. Ein vorheriger und ein
anschließender Erfolg werden durch synthetische, validierte Ausgaben abgebildet;
für den Fehler im zweiten Abschnitt führt der Test den echten OpenRouter-
Adapter aus. Damit wird nicht die Verfügbarkeit eines realen Anbieters gemessen.

Abgedeckt sind HTTP 400 einschließlich `invalid_json_schema`, 408, 429, 500,
503 und 504, Lese-Timeout, Verbindungsfehler, ein 429-Fehler in einer HTTP-200-
Hülle, abgeschnittene Ausgabe, ungültiges JSON, leerer Inhalt, fehlerhafte
Schemaausgabe und eine ungültige äußere JSON-Hülle. Die 200er-Fälle mit
künstlichen gemeldeten Kosten werden abgerechnet; bei unbekannten Kosten
bleibt die Reservierung erhalten. Jede Verarbeitung wird nur einmal verbucht.
Der bereits validierte erste Abschnitt und frühere Antworten bleiben erhalten;
GETs und Workerläufe wiederholen die Anfrage nicht. Erst die ausdrückliche
Aktion startet den fehlenden Abschnitt; nachfolgend kann der letzte Teil
veröffentlicht werden. Synthetische vom Anbieter zurückgespiegelte Inhalte
erscheinen weder in Auftragsfehlern noch in der Telemetrie.

Zuvor wurden HTTP 429 und 5xx wegen des generischen Fehlertexts teilweise als
Konfigurationsfehler eingeordnet; ein Lese-Timeout wurde wie ein allgemeiner
Netzfehler behandelt, ungültiges äußeres JSON konnte als unleserliches Foto
erscheinen. Der Adapter vergibt nun explizite geschlossene Kategorien für
Auslastung, Timeout, Nichtverfügbarkeit und ungültige Ausgabe. Bei 400 und
anderen nicht gesondert klassifizierten HTTP-Fehlern bleibt der Hinweis zur
Konfigurationsprüfung erhalten. Dieses Mapping ändert weder Reservierungen noch
Providerwahl, Wiederholungsgrenzen, Verarbeitung früherer Ergebnisse oder
Transportinhalte.

Die Fehlerklassifikation prüft bei eingebetteten Fehlern ohne Metadaten auch
geschlossene numerische Fehlercodes als Integer oder exakt passende Zeichenkette:
429 bedeutet Auslastung, 408/504 Timeout. Fehlertexte bleiben ausgeschlossen.
Ungültige Formen des `usage`-Feldes werden als ungültige Ausgabe behandelt;
bei unbekannten Kosten bleibt die Reservierung erhalten. Die Tests prüfen die
Varianten im äußeren Fehler und im Fehler einer einzelnen Choice.

**Reichweite des Datenschutztests:** Die Testmarker in Fehlermeldung und
Fehlermetadaten erscheinen weder im Auftragsfehler noch in der Telemetrie.
Andere Felder wie Generierungs-ID, Modellname, Upstream und Request-ID nehmen
weiterhin formatgeprüfte, aber nicht inhaltlich verifizierte Anbieterwerte an.
Ein dort entgegen der Anbietersemantik hineingeschriebener privater Text lässt
sich damit nicht grundsätzlich ausschließen. Generierungskennungen dienen
zugleich der Kostennachbuchung; ohne nachgewiesenen Anbieterformatvertrag wäre
eine willkürliche ID-Whitelist keine verlässliche Lösung.

```sh
TMPDIR=/dev/shm .venv/bin/pytest -q backend/tests/test_package_http_failure_end_to_end.py
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_package_http_failure_end_to_end.py
```

Die simulierten Kosten sind keine echten Anbieterbelege. Siehe für tatsächliche
frühere künstliche Anbieteraufrufe und ihre gemessenen Kosten
[OPENROUTER_VISUAL_TEST_2026_11_04.md](OPENROUTER_VISUAL_TEST_2026_11_04.md).
Offen bleiben die sichere Vorabplanung initialer Bruch-Paketaufgaben, weitere
Fehlerursachen und belastbare repräsentative Produktivitätsnachweise.
