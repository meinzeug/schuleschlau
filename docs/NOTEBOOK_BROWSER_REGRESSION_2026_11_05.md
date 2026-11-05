# Wiederholbarer lokaler Hefte-Browserlauf

Dieser Opt-in-Test ergänzt die früheren [UI-Mocktests](NOTEBOOK_MATERIAL_UI_2026_11_05.md)
und den [einmaligen lokalen Lauf](NOTEBOOK_LOCAL_BROWSER_2026_11_05.md).
Er startet einen echten FastAPI-Prozess mit einer neuen isolierten SQLite-
Datenbank und einem eigenen Uploadverzeichnis auf einem zufälligen Loopback-Port.
Es werden ausschließlich künstliche Eltern- und Kinderzugänge sowie die fünf
JPEG-Layoutseiten aus `testdata/notebook_synthetic/` verwendet. Ein eigener
Launcher entfernt ererbte Datenbank-, Provider- und Zugangseinstellungen aus
der Umgebung. Ein früher Test-Guard verweigert das Browser-Opt-in, falls
`TEST_DATABASE_URL` gesetzt ist. Der Server wird nach dem Lauf beendet.

Der Test importiert die Fotos regulär über die lokale API. **Es läuft keine
OCR:** Für die Testvorbereitung werden künstliche Texte als Kandidaten im
Status `review` eingesetzt und anschließend über die reguläre API bestätigt.
Eine lokal angelegte künstliche Lernrunde mit einem künstlichen Versuch dient
als Beleg für die Löschvorschau. Der Browser prüft Fachnavigation und die
fünf authentifiziert geladenen Fotos, die Elternvorschau mit verknüpfter Runde
und Antwort und deren Abbruch. Er startet eine Einzel- und eine Mehrseitenauswahl
für zwei Kinder; deren wartende Aufträge werden auf Kind und Quellenrevision
geprüft. Ein drittes Kind löscht nach ausdrücklicher Vorschau ausschließlich
seine eigene unbestätigte Seite. Es laufen weder KI-Worker noch externe
Provider; die beiden Aufträge bleiben in der Warteschlange und sind kein
Nachweis erzeugter Aufgaben.

Am 05.11.2026 bestand der Lauf mit dem Schutzfix `67d90d5` und einem
zugehörigen Flutter-Webrelease: zwei Pytest-Fälle einschließlich des
Isolations-Guards bestanden. Die Browseraktionen liefen bei 390 und
1280 Pixeln; die Löschvorschau und Kinderlöschung wurden bei 390 Pixeln
geprüft. Die künstlichen Bildschirmfotos wurden mit dem Testverzeichnis
entfernt. Ein unabhängiger Review prüfte die Isolation des Testtreibers,
nicht dessen Ausführung.

## Reproduzieren

Vorausgesetzt werden ein lokal aus dem zu prüfenden Quellstand gebautes
Flutter-Webrelease, Chrome und die Node-Abhängigkeiten in `qa/`:

```sh
/pfad/zur/projekt-python qa/run_notebook_local_browser.py \
  --web-dir "$PWD/app/build/web" --scratch-root /dev/shm
```

Der Launcher verwendet den aufrufenden Python-Interpreter. Die Ausgabeordner,
SQLite-Daten und künstlichen Sitzungen werden nach Testende gelöscht. Ein
erzwungener Prozessabbruch kann temporäre Verzeichnisse hinterlassen. Der
Browser verwendet einen echten Webrelease-Build und echte lokale API-Antworten;
der Test setzt aber keinen Produktionsserver ein. Screenshots liegen nur
während des Laufs im Testverzeichnis. Für sichtbare Vorabbelege siehe den
früheren Bericht; ein erneuter Build muss vor dem Test zum Quellstand passen.

Der Hefte-Hauptpunkt bleibt offen: realistische Fotoqualität, OCR, fachlich
geprüfte KI-Aufgaben, weitere Materialpfade und eine vollständige
Bedienungs-/Barrierefreiheitsabnahme werden hiervon nicht bewiesen. Der
Klassenarbeit-Layoutbogen wird hier wie ein Heftfoto behandelt und prüft nicht
den eigenständigen Klassenarbeiten-Workflow.
