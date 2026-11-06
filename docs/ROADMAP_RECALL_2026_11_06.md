# Abruf und Lernplanung: synthetische Mehrtagesabnahme

Am 06.11.2026 wurde ein künstliches sechstklassiges Testkonto in einer
isolierten SQLite-Datenbank mit einem lokalen Flutter-Webbuild und Chrome bei
390 × 844 Pixeln bedient. Der Testserver lief nur auf `127.0.0.1`. Der Browser
blockierte Anfragen außerhalb des Testservers. Für jeden simulierten Tag
wurde eine frische Sitzung des künstlichen Kontos angelegt; die Testuhr lief
innerhalb des jeweiligen Tages weiter. Die Uhr des Rechners und des
Produktionsservers wurde nicht verändert.

Die Bedienung folgte den fälligen Vorschlägen unter „Heute“ über den
Vorbereitungsbildschirm in die Übungsrunde. Jede Runde wurde ausdrücklich
angefordert; der reguläre Worker verarbeitete einen **simulierten**
Anbietertransport. Alle Antworten wurden über die Oberfläche eingegeben; ihre
gespeicherten Ergebnisse wurden unabhängig in der isolierten Testdatenbank
kontrolliert. Vor dem Weitergehen blieb das Antwortfeedback sichtbar. Am Ende
waren alle auswertbaren Lernziele mit mindestens drei unabhängigen Prüftagen
über mindestens sieben Tage gefestigt. Der spätere künstliche Elternauftrag
behielt sein Startdatum. Ein Durchlauf absolvierte sechs Wiederholungen am
07., 08., 09., 12., 15. und 22.11.2026; ein vorheriger unabhängiger Lauf
bestand denselben vollständigen Ablauf ebenfalls.

Die zugehörigen automatisierten API-Fälle prüfen außerdem das
idempotente erneute Anfordern, neue Fragen, gespeicherte Quellenrevisionen,
Quellenänderung ohne Umschreiben von Antworten, einen zukünftigen
Elternauftrag, freiwillige Fortsetzung trotz Pause und erfülltem Mindestziel
sowie die nicht doppelt gezählte Aktivitätszeit zweier Geräte. Die 18 Fälle
`test_recall_generated_journey.py`, `test_recall_planning_journey.py` und
`test_learning_controller.py` bestanden auf SQLite und isoliertem PostgreSQL.

Screenshots ausschließlich künstlicher Testdaten:

- [Heute am ersten Prüftag](images/recall-20261106/tag-1-heute.png)
- [Heute am dritten Prüftag](images/recall-20261106/tag-3-heute.png)
- [Gespeicherte Antwort und Feedback](images/recall-20261106/rueckmeldung.png)
- [Rückblick nach Abschluss am dritten Prüftag](images/recall-20261106/tag-3-rueckblick.png)

Der Rückblick-Screenshot zeigt den Zustand direkt nach der Antwort, bevor die
Oberfläche den simulierten Bericht erneut geladen hat. Die angezeigte
fehlende quellengebundene Grafik ist eine bekannte Grenze dieses künstlichen
Modelltransports; sie ist keine Abnahme fachlicher Grafikqualität.

Reproduzierbar mit lokal installiertem Chrome, den QA-Abhängigkeiten und einem
zum Quellstand passenden Flutter-Webbuild:

```sh
RECALL_MOBILE_BROWSER=1 WEB_DIR=/absoluter/pfad/zum/flutter-webbuild \
  TMPDIR=/dev/shm .venv/bin/python -m pytest -q -s \
  backend/tests/test_recall_mobile_browser.py --tb=short
TMPDIR=/dev/shm .venv/bin/python -m pytest -q \
  backend/tests/test_recall_generated_journey.py \
  backend/tests/test_recall_planning_journey.py \
  backend/tests/test_learning_controller.py --tb=short
TMPDIR=/dev/shm .venv/bin/python scripts/test_postgres.py \
  backend/tests/test_recall_generated_journey.py \
  backend/tests/test_recall_planning_journey.py \
  backend/tests/test_learning_controller.py --tb=short
```

Der Browsertest ist ausdrücklich opt-in und verweigert eine vorgegebene
externe Testdatenbank vor dem Import der Anwendung. Seine temporären
Steuerungsrouten existieren ausschließlich im Testprozess, sind an Loopback
und ein zufälliges Testtoken gebunden und werden nach dem Lauf entfernt.

Diese Abnahme belegt **keine** fachliche Prüfung echter Modellausgaben, keine
Pushzustellung, keine getestete Erklärungsgrafik und keinen Android-Gerätetest.
Die betreffenden weitergehenden Roadmap-Punkte bleiben davon unberührt.
