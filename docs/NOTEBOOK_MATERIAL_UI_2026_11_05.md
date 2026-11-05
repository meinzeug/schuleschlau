# Hefte: synthetische Materialansichten

Stand 05.11.2026, isolierter Teststand auf `b3e5ba5`. Fünf eigens mit
Pillow und DejaVu-Schriften gezeichnete JPEGs liegen ausschließlich unter
`testdata/notebook_synthetic/`: Arbeitsblatt, Hefter, Arbeitsheft, Buchseite
und Klassenarbeit. Die Seiten sind sichtbar als künstlich gekennzeichnet;
sie sind keine realistischen Handyfotos und kein OCR-Qualitätsdatensatz. Die
Dateien sind weder Flutter-App-Assets noch öffentliche Produktinhalte. Ihre
Vorlage enthält nur künstliche Bruchbeispiele, keine persönlichen Daten.

Die UI-Prüfung verwendet `qa/notebook_material_ui_test.py`: Sie erzeugt eine
eigene temporäre Testdatei mit diesen JPEG-Bytes, führt Flutter-Widgettests
mit `MockClient` aus und entfernt die Testdatei anschließend. Wegen der
temporären Datei im Testverzeichnis den Runner in einem eigenen Checkout und
nicht parallel zu einer vollständigen Flutter-Testentdeckung starten. Bei
erzwungenem Prozessabbruch kann eine temporäre Testdatei zurückbleiben.
Zwei isolierte Python-Unittests prüfen die Bereinigung bei Schreib- und
Flutter-Aufruffehlern. Beispielsweise:

```sh
python3 qa/notebook_material_ui_test.py --flutter /pfad/zu/flutter
CHROME_EXECUTABLE=/pfad/zu/chrome python3 qa/notebook_material_ui_test.py \
  --platform chrome --flutter /pfad/zu/flutter
```

Je 12 Fälle bestanden auf der Flutter-VM und im Chrome-Webrunner. Sie
durchlaufen Kind- und Elternoberfläche bei 390 und 1280 logischen Pixeln. Sie prüfen Fachnavigation, Blättern, ein Suchwort, Seitensprung über
die 20er-Metadatengrenze und das jeweils zugehörige Bild im Flutter-Widget.
Sie starten eine simulierte Vorbereitung mit einer oder zwei ausgewählten
Quellen und kontrollieren deren IDs, Revisionen und Idempotenzschlüssel; vor
der bewussten Startaktion erfolgen nur GETs. Die künstlichen Notebook-Metadaten
verwenden `synthetic: false`, um den regulären Startpfad statt der gesperrten
Demo-Beispiele zu testen. Die Fotoantworten und der 202-Auftrag stammen aus
lokalen Mocks: Ein echter Upload, eine API-Autorisierung, eine KI-Verarbeitung
oder ein abgeschlossener Lernauftrag wird daraus nicht abgeleitet. Dass die
als Klassenarbeit gestaltete Testseite in diesem Test als Notebook-Quelle
behandelt wird, prüft nicht den eigenständigen Klassenarbeiten-Workflow.

Der Generator schreibt ausschließlich in ein neues, noch nicht vorhandenes, frei wählbares
Verzeichnis. Mit Pillow 10.2.0 und den lokalen DejaVu-Schriften erzeugte er am
05.11.2026 dieselben SHA-256-Werte wie die fünf eingecheckten JPEGs:

```sh
python3 qa/generate_notebook_fixtures.py --out /pfad/zu/neuem-leeren-ordner
sha256sum testdata/notebook_synthetic/*.jpg
```

Dies ist eine wiederholbare technische Teilprüfung. Die vollständige
Roadmap-Abnahme bleibt offen: insbesondere realistische Fotos und OCR,
produktive Quellen-/Rechteprüfung, getrennte Material- und Nacharbeitspfade,
Löschvorschau und Neu-Einlesen in allen relevanten Zuständen sowie eine
Bedienungs- und Barrierefreiheitsabnahme mit Menschen. Die Tests prüfen keine
Lesbarkeit fotografierter Handschrift und ersetzen keine Screenshots der
laufenden vollständigen App.
