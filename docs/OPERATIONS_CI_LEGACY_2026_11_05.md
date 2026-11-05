# Historische Release-Bereinigung im Operations-CI

Am 05.11.2026 schlug im GitHub-Lauf
[41978459752](https://github.com/meinzeug/schulpilot/actions/runs/41978459752)
der Operationsjob beim Rollback-Koordinationstest fehl. Der Job verwendet den
standardmäßig flachen Checkout; der Test verlangte mit `git show` den dort nicht
vorhandenen historischen Commit `534009f`. Ein anderer Regressionstest hatte bei
fehlender Historie denselben Prüffall übersprungen. Das ist ein Testumgebungs-
und Nachweisfehler, kein Nachweis für einen fehlgeschlagenen Produktionsrollback.

Die beiden Tests verwenden nun das bytegenaue historische
`deploy/prune_releases.py` aus `534009f` als Fixture. Vor dessen Ausführung wird
SHA-256 `22d6e9210c6c9966e678d0945246927a24396cf697923c0338c6631b0bddae47`
geprüft; ein manipulierter oder fehlender Snapshot schlägt fehl. Im lokalen
Vergleich stimmte die Fixture byteweise mit `git show` überein. Ein aus
`git archive` erstelltes Arbeitsverzeichnis ohne Git-Historie reproduzierte
vorher den Fehler und den Skip; nach der Änderung bestanden beide Tests und der
zusätzliche Integritätstest ohne Skip. Ein zukünftiger CI-Lauf bleibt separat
abzuwarten.

Die Prüfungen zeigen, dass die alte Bereinigung **nach** Anlage des Markers
keine neue Löschliste anlegt. Sie beweisen nicht, dass eine bereits **vor** dem
Marker aufgestellte Löschliste gestoppt wird. Bei Rollbacks auf ältere Ziele
außerhalb von `current` und `previous` muss vor Einsatz des Legacy-Werkzeugs
sichergestellt sein, dass kein solcher alter Bereinigungslauf mehr aktiv ist.
Die Fixture repariert keine Race Condition und ändert keinen Produktionscode.
