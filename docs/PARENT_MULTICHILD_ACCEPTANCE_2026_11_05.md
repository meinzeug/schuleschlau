# Elternübersicht: künstliche Mehrkind-Prüfung vom 05.11.2026

Der Roadmap-Hauptpunkt bleibt offen. Diese Prüfung deckt einen zusammenhängenden Teil mit zwei künstlichen Kindern derselben Familie ab; sie ist keine vollständige Freigabe der Elternoberfläche.

## Tatsächlich geprüft

`backend/tests/test_parent_multichild_acceptance.py` legt in der isolierten Testdatenbank zwei Kinder mit unterschiedlichen Fächern, Noten und verpflichtenden Terminen an. Gespeichert sind ein selbstständiger Erstversuch, ein fehlgeschlagener und anschließend unterstützter Versuch, ein Hinweis sowie unterschiedliche Zeitbelege an zwei Tagen. Für ein Kind ist der aktuelle Tag als freier Lerntag eingestellt. Wiederholte Eltern-GETs für Überblick, Lernfortschritt, Lernplan und Noten liefern die erwarteten, voneinander getrennten Fakten. Das Kind kann weder die eigenen elterngebundenen Noten oder Pläne noch den Lernstand des Geschwisters lesen; eine fremde Familie erhält keinen Zugriff. Ganze Zeilen von Aktivität, Auftrag, Versuch, Auftragsschlange, Einheit, Lernstand, Material, Note und Verbrauch werden vor und nach den lesenden Aufrufen verglichen. Authentifizierungssitzungen sind ausgenommen, weil ein authentifizierter Zugriff deren Aktivitätszeit aktualisieren kann. Der Providertransport ist ersetzt; er wurde nicht aufgerufen. SQLite und ein isolierter PostgreSQL-16-Cluster bestanden.

Der ausdrücklich aktivierte Browsertest startet denselben FastAPI-Prozess auf `127.0.0.1` mit wegwerfbarer SQLite-Testdatenbank und lokalem Flutter-Web-Releasebuild. Ein Elternteil meldet sich in echtem Chrome an; die Routen für Fortschritt, Noten und Lernplan werden für beide Kinder bei 390 und 1440 Pixeln direkt geöffnet. Die sichtbaren Fach-, Aufgaben-, Hilfs-, Noten-, Themen-, Pflicht- und Terminangaben werden mit den künstlichen gespeicherten Werten verglichen. Der Browser beobachtet die tatsächlichen lokalen API-Antworten; ausschließlich der reguläre Login darf schreiben. Vorher und nachher bleiben die genannten vollständigen Datenbankzeilen unverändert. Die Bildschirmfotos liegen nur im temporären pytest-Verzeichnis und enthalten ausschließlich künstliche Inhalte. Kein produktiver Server und keine externen KI-Anbieter wurden verwendet. Der getestete Releasebuild stammte aus Worktree bb2bf24; der Browsertest verwendet echte Serverantworten und keine HTTP-Mocks.

Der zusätzlich separat ausgeführte bestehende PDF-Test `test_grade_pdf_imports.py` prüft lokale Extraktion eines künstlichen Noten-PDFs, Vorschau, ausdrückliche Bestätigung, wiederholte Bestätigung und erneuten Import ohne doppelte Noten; er prüft außerdem den ausbleibenden KI-Aufruf. Drei einschlägige Fälle bestanden jeweils auf SQLite und isoliertem PostgreSQL. Es handelt sich hierbei um API- und Parserprüfungen, nicht um einen neuen Mehrkind-PDF-Browserlauf.

## Reproduzieren

Voraussetzung sind die Projekt-Python-Umgebung, Node mit den Abhängigkeiten aus `qa/package.json`, Chrome und ein zuvor aus dem zu prüfenden Quellstand gebautes Flutter-Web-Release in `app/build/web`. Der Browserfall ist standardmäßig übersprungen; die Testdatenbank-Schutzprüfungen in `backend/tests/conftest.py` bleiben aktiv. `WEB_DIR` muss vor dem Laden der Python-Anwendung gesetzt sein.

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_parent_multichild_acceptance.py
.venv/bin/python scripts/test_postgres.py backend/tests/test_parent_multichild_acceptance.py
WEB_DIR="$PWD/app/build/web" PARENT_MULTICHILD_BROWSER=1 PYTHONPATH=backend \
  .venv/bin/python -m pytest -q backend/tests/test_parent_multichild_acceptance.py::test_parent_multichild_local_flutter_browser
```

Der Browser startet ausschließlich, wenn `PARENT_MULTICHILD_BROWSER=1` gesetzt ist. Seine Zugangsdaten sind feste künstliche Testdaten und werden nur über stdin an den lokalen Browserprozess weitergegeben. Er akzeptiert nur eine HTTP-Loopback-Adresse. Die temporäre Testdatenbank wird vom bestehenden pytest-Testaufbau angelegt; der lokale Server wird beendet und sein Socket geschlossen.

## Noch offen

Die Browserprüfung öffnet Routen direkt; sie ist keine vollständige Navigation durch sämtliche Elternansichten und keine Prüfung separater Freizeitkalenderereignisse in der Oberfläche. Getestet ist der freie **Lerntag**, nicht ein gesondertes Freizeitkalenderereignis. Das PDF wurde im hier dokumentierten Lauf nicht über den Browser importiert, und die Mehrkindfamilie wurde nicht im selben Browserlauf für alle Rollen durchgespielt. Die historischen Browserberichte und separaten PDF- und Rechtefälle dürfen nicht zu einer lückenlosen aktuellen Mehrkindabnahme zusammengezogen werden. Auch Android, assistive Technologien und eine vollständige Prüfung aller Anzeigewerte sind damit nicht nachgewiesen.
