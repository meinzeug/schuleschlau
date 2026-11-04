# Paketvorbereitung: künstliche Fehler- und Wiederaufnahmeprüfung

Stand 4. November 2026; Basis `529c8d5` und die ergänzten Tests in
`backend/tests/test_package_parts_worker.py`. Die Daten und Providerantworten
sind künstlich; es wurde kein Anbieter kontaktiert.

Der reguläre Worker verarbeitet sieben bestätigte künstliche Seiten in drei
getrennt reservierten Teilen. Ein bereits validierter erster Teil bleibt
bei einem Fehler im zweiten Teil erhalten. Die Matrix injiziert getrennt die
Fehlerklassen ungültige Ausgabe, Auslastung, Zeitüberschreitung,
Nichtverfügbarkeit und Unterbrechung mit einem künstlichen Kostenbeleg. Der
öffentliche Status nennt die jeweilige Kategorie und die abgeschlossene sowie
gesamte Teilzahl. Wiederholte GETs und Workerläufe starten keinen neuen
Anbieteraufruf; erst die ausdrückliche Aktion startet den fehlenden Teil und
danach den letzten Teil. Vorhandene künstliche Antworten und Quellenbezüge
bleiben erhalten. Die Fehlerklassen simulieren die bereits klassifizierte
Adapterausgabe, nicht die tatsächlichen HTTP-Antworten der Anbieter.

Ein weiterer Fall markiert einen real vom Worker beanspruchten zweiten
Teilauftrag als zeitlich abgelaufen und führt die reguläre Wartungsroutine
als Wiederanlauf aus. Sie markiert ihn als unterbrochen, ohne automatisch
neu aufzurufen; die konservative Kostenbehandlung und der gespeicherte erste
Teil bleiben erhalten. Erst eine bewusste Wiederholung führt den zweiten und
dritten Teil aus. Der Test simuliert den abgelaufenen Auftrag und ersetzt
keinen Betriebssystem-Absturztest.

```sh
TMPDIR=/dev/shm .venv/bin/pytest -q backend/tests/test_package_parts_worker.py --tb=short
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py backend/tests/test_package_parts_worker.py --tb=short
```

Noch offen für die vollständige Abnahme: Ein aktueller echter freigegebener
Anbieteraufruf mit künstlichen Mehrseiteninhalten und dokumentierter
Abrechnung, sowie ein durchgehender Nachweis der tatsächlichen Adapterantworten
für sämtliche 400/429/5xx-, Timeout-, Schema- und Ausgabelängenfälle. Die
unklaren Kosten der Kontoanmeldung dürfen nicht als Nullkosten ausgegeben
werden. Ein einzelner erfolgreicher Lauf belegt keine generelle Verfügbarkeit.
