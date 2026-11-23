# Beta-Anmeldung: künstlicher Browserlauf, 23.11.2026

Der wiederholbare Test `qa/run_beta_local_browser.py` startet die echte API und
Flutter-Weboberfläche auf einer lokalen Loopback-Adresse mit einer eigens
angelegten SQLite-Datenbank. Vererbte Datenbank-, Provider- und Zugangsdaten
werden durch eine explizite Umgebungs-Whitelist ausgeschlossen. Die
Browser-Netzwerksperre verhindert externe Seiten und WebSockets; sie ersetzt
keine betriebssystemweite Netzwerksandbox.

Der künstliche Ablauf umfasst die öffentliche Startseite und Beta-Registrierung
bei 390 × 844 Pixeln, eine ausdrücklich bestätigte Erwachsenenberechtigung,
das Öffnen des Bestätigungslinks und die erfolgreiche Adressbestätigung. Danach
meldet sich ein künstlicher Administrator bei 1280 × 900 Pixeln an und gibt
den verifizierten Antrag über die tatsächliche Benutzeroberfläche frei. Der
künstliche Elternteil meldet sich an und sieht den Status `approved`; das
Testkind wird über die reguläre API angelegt, meldet sich im mobilen Browser an
und beantwortet in einer gespeicherten Runde eine Aufgabe. Die Antwort wird in
der Datenbank geprüft. Die gespeicherte Übung wird ausschließlich im Test
vorgegeben und als künstliche Beispielübung gekennzeichnet.

Anschließend prüfen reale Reservierungs- und Abrechnungsfunktionen in derselben
Testdatenbank die Beta-Ausnahme bei künstlich auf null gesetzten Kostenlimits,
die getrennte Erfassung eines gemeldeten und eines unbekannten Betrags und
den revisionsgebundenen Widerruf und eine erneute Bewerbung mit erneuter
Freigabe. In der Zwischenzeit ist der Zugang gesperrt; die ursprünglichen
Kostenbelege und die Antwort bleiben erhalten. Ein
separater Test verhindert die Ausführung mit einer externen Testdatenbank. Der
Runner betrachtet übersprungene oder fehlende Fälle nicht als Erfolg.

Das Testpostfach und die Übung sind ausschließlich lokale Fixtures. Es wird
weder E-Mail zugestellt noch ein Anbieter aufgerufen. Der Lauf belegt deshalb
keine echte Fotoerkennung, Modellqualität, reale Providerabrechnung oder
produktionsseitige Bewerbung/Freigabe. Auf der Zielinstallation zeigte die
öffentliche Katalogabfrage am 23.11.2026 `beta.enabled=true`; das ist kein
Nachweis einer vollständigen Produktionsreise. PostgreSQL-Konkurrenzfälle
werden separat in `backend/tests/test_beta.py` geprüft und sind beim
SQLite-Lauf bewusst übersprungen. Physische Geräte werden nicht behauptet.

```sh
/home/dennis/schulpilot/.venv/bin/python qa/run_beta_local_browser.py \
  --web-dir app/build/web --scratch-root /dev/shm
```

Die Beta-Modellliste zeigt höchstens zehn Einträge. Ein zusätzlicher Hinweis
kennzeichnet fortan, wenn weitere Modelle ausgelassen sind oder der Server
seine Modellliste gekürzt hat. Die Gesamtsumme bezieht sich weiterhin auf alle
erfassten Beta-Aufrufe; unbekannte Kosten bleiben getrennt ausgewiesen.

Kleine bekannte Beträge werden in der Adminansicht auf sechs USD-
Nachkommastellen angezeigt, entsprechend der gespeicherten Millionstel-Dollar-
Einheit. Das vermeidet eine Anzeige von null bei positiven Kleinstbeträgen.
