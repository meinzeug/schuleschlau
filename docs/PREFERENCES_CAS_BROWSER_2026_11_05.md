# Lernvorgaben: künstlicher Zwei-Eltern-Browserlauf

Am 05.11.2026 wurde ein Webrelease mit zwei regulären, künstlichen
Elternkonten in einem isolierten lokalen Chrome-/SQLite-Lauf geprüft. Beide
öffnen denselben Stand der Lernvorgaben bei 390 Pixeln. Elternteil A ändert
das Tagesminimum, entzieht die künstliche Push-Elternfreigabe und setzt ein
Wiederholungsziel. Elternteil B versucht seinen älteren Entwurf zu speichern:
Der echte Server antwortet mit dem gekennzeichneten Konflikt 409, die App
behält den Entwurf und zeigt den Hinweis. Auch nach „Entwurf behalten“ ist
der eingegebene Wert vorhanden. Der Screenshot des künstlichen Konflikts wurde
angesehen; er liegt nur im temporären Testverzeichnis.

Die Datenbankprüfung belegt, dass A's Einstellungen und der daraus erstellte
Pflichtauftrag erhalten bleiben und die zuvor künstlich angelegte
Push-Registrierung entfernt ist. Es gibt keinen KI-Auftrag oder Provideraufruf.
Ein separater HTTP-Aufruf ohne `If-Match` liefert 428 mit lesbarem
Updatehinweis; dabei wird kein alter APK-Client ausgeführt. Für Rechte- und
Sperrrennen sowie die Migration sind die gesonderten PostgreSQL- und
SQLite-Backendtests maßgeblich. Ein produktiver Server, echte Konten und echte
Geräte wurden nicht verwendet.

Der Browserfall ist standardmäßig abgeschaltet. Er benötigt einen Flutter-
Webreleasebuild desselben Quellstands, Node und die Projektabhängigkeiten in
`qa/node_modules`. Ein Guard lehnt für diesen Lauf `TEST_DATABASE_URL` vor der
Initialisierung ab. Beispiel für einen isolierten Aufruf:

```sh
WEB_DIR="$PWD/app/build/web" PARENT_PREFS_CAS_BROWSER=1 PYTHONPATH=backend \
  .venv/bin/python -m pytest -q backend/tests/test_preferences_browser_cas.py
```

Die Testzugänge sind künstlich und werden dem Node-Prozess über stdin
übergeben. Für begrenzte temporäre Daten kann `TMPDIR` auf ein privates
Wegwerfverzeichnis zeigen. Das ist keine umfassende Android-, Screenreader-
oder Mehrfamilienabnahme.
