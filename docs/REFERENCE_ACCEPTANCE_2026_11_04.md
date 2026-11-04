# Referenzen und Medien: Prüfstand vom 4. November 2026

Die folgenden Prüfungen verwenden ausschließlich künstliche Inhalte und
simulierte Modellantworten. Sie belegen den technischen Datenweg, keine
fachkundige Prüfung aller Inhalte und keinen echten Modellaufruf.

`backend/tests/test_reference_multisubject_path.py` legt bestätigte künstliche
Quellen in einer Testdatenbank an und führt die echte Referenzsuche, die an
zulässige Vorlagen gebundene Antwortdekodierung, Schemaprüfung, Speicherung
und öffentliche Projektion aus. Für Deutsch wird
`german.word_formation.parts`, für Biologie und Geografie
`general.source_relation.phases`, jeweils Version 1, erwartet. Dabei werden
auch Rezept- und Parameterfingerabdrücke sowie die Quellzuordnung geprüft;
der private Quellenwortlaut wird nicht in den öffentlichen Grafikblock
übernommen. Die drei Fälle bestanden auf SQLite und isoliertem PostgreSQL.

Die vorhandenen Referenz-, Paket-, Katalog- und Medienregressionen bestanden
mit 289 SQLite-Fällen. Sie prüfen unter anderem fehlende, geänderte und
fachfremde Referenzen, erlaubte Medienkandidaten und den getrennten
Linknachweis ohne Antwort-, Kompetenz- oder Zeitbuchung. Weitere 34
Flutter-VM-Fälle prüften gespeicherte Erklärungen und Lerntipps. Der neue
Chrome-Webrunner-Test `app/test/reference_multisubject_web_test.dart` zeigt
sechs künstliche Erklärgrafiken für Deutsch, Geschichte und Geografie bei
390 und 1024 Pixeln. Diese Rendererbeispiele sind separate öffentliche
Fixtures, keine Aufzeichnung des Backendtests. Zusammen belegen die
Backend- und Webtests die Schnittstelle in getrennten Schritten; sie ersetzen
keine vollständige KI- oder Bildqualitätsabnahme im Browser.

Reproduzierbare Aufrufe aus dem Repositoryverzeichnis:

```sh
TMPDIR=/dev/shm .venv/bin/pytest -q backend/tests/test_visual_references.py backend/tests/test_package_part_graphics.py backend/tests/test_catalog_ai.py backend/tests/test_learning_tips.py backend/tests/test_controller_media.py backend/tests/test_package_part_catalog.py
TMPDIR=/dev/shm .venv/bin/pytest -q backend/tests/test_reference_multisubject_path.py
.venv/bin/python scripts/test_postgres.py backend/tests/test_reference_multisubject_path.py -q
cd app
flutter test --no-pub test/learning_tips_test.dart test/visual_learning_room_107_test.dart test/saved_visual_explanation_107_test.dart
flutter test --no-pub --platform chrome test/reference_multisubject_web_test.dart
```

Die genannten Dateien sind repräsentative Fälle; fehlende oder fachlich
ungeeignete Referenzinhalte müssen weiterhin fallweise ergänzt und die
Grafiken eigenständig fachlich geprüft werden. Diese Prüfung behauptet weder
Videoansicht noch Kompetenzzuwachs.
