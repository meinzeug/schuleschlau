# Automatisierte Abnahmen: Umfang und Nachweise

Stand 24.11.2026. Die maßgebliche Pipeline ist
[checks.yml](../.github/workflows/checks.yml); sie prüft die jeweilige
Git-Revision. Der vollständige GitHub-Lauf
[45375138665](https://github.com/meinzeug/schuleschlau/actions/runs/45375138665)
bestand für `49efc8b`. Er enthält noch nicht die nachfolgend ergänzten
Schulbuddy- und Foto-Browsertests. Der Erfolg einer späteren Revision ist
an deren eigenem Lauf abzulesen.

| Bereich | Automatisierter Nachweis | Grenzen |
| --- | --- | --- |
| Fotoimport | `test_photo_local_browser.py`: künstliches Foto über mobile Dateiauswahl und Zuschnitt zur gespeicherten Seite; ohne Abgabe kein KI-Auftrag | Keine Kamera, Android, OCR-Qualität oder Freigabe echter Fotos |
| Aufgabenbewertung und Lernstand | `test_recall_mobile_browser.py`: mehrere künstliche Lerntage, explizite Aufgabenantworten, Rückblicke und festgehaltener Lernstand; begrenzte Testuhr | Ein künstlicher Mathematikpfad, simulierte Anbieterantworten |
| Schulbuddy | `test_schulbuddy_local_browser.py`: Heftkontext, explizite Frage, Worker, Quellzitat, Wiederaufnahme und fremde Familie | Simulierter Anbieter, kein fachlicher Qualitätsnachweis für beliebige Themen |
| Benachrichtigungen | `test_notification_cross_device_browser.py`: Glocke, sichtbare Lesebelege, Cursor, getrennte Sitzungen und Rundenziel | Webkontexte, keine FCM- oder native Zustellung |
| Rollen und Hefte | `test_notebook_local_browser.py` und `test_preferences_browser_cas.py`: Eltern-/Kinderzugänge, Familiengrenzen und konkurrierende Einstellungen | Repräsentative Fälle, keine vollständige Rechte- oder Barrierefreiheitsprüfung |
| Datenbank und Betrieb | vollständige Backendpartitionen, isolierter PostgreSQL-Rennlauf und Operationsjob; unter anderem Migrations- und Rollbacktests | Testdaten und isolierte Umgebung, keine echte Produktivwiederherstellung |
| Flutter und Web | vollständige Flutter-Testpartitionen, Analyse, Webbuild und Browsergate | Keine vollständige physische Geräteabnahme |

Der Browserrunner verwendet ein eigenes temporäres Verzeichnis und einen
lokalen SQLite-Testserver. Er gibt nur eine erlaubte Umgebung an die Prozesse
weiter und lässt keine fremde `TEST_DATABASE_URL` zu. Seine JUnit-Prüfung
verlangt sämtliche aufgeführten Pflichtfälle genau einmal ohne Skip oder
Fehler. Browserkontexte blockieren fremde HTTP-Ziele; dies ist keine
Netzwerkisolierung des gesamten Betriebssystems. Simulierte Anbieter, echte
Anbieterprüfungen, Emulatoren und physische Geräte bleiben getrennte
Nachweise. Die CI erfasst außerdem vorhandene Skips; ein fehlgeschlagener oder
abgebrochener Lauf gilt nicht als Erfolg.

Wiederholung: Flutter-Webbuild mit der fixierten Toolchain erzeugen und dann
`python qa/run_notebook_local_browser.py --web-dir app/build/web` ausführen.
Der PostgreSQL-Rennlauf verwendet `scripts/test_postgres.py` mit isoliertem
temporärem Cluster. Die exakten CI-Kommandos stehen in der Workflowdatei.
