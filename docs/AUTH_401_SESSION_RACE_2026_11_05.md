# Verspätete 401-Antworten und Sitzungswechsel

Ein alter Request darf nach einem Kontowechsel, Tokenwechsel oder Beginn einer
neuen Authentifizierung die neue Sitzung nicht abmelden. Der Client bindet
seine 401-Seitenwirkung an Benutzerobjekt, Bearertoken und lokale
Authentifizierungsrevision. Letztere unterscheidet im Web auch zwei
Cookie-Sitzungen, bevor das neue Benutzerobjekt eintrifft. Der asynchrone
Abmeldeweg prüft denselben Auftrag nach seinen Warteschritten erneut. Das gilt
auch für Foto-, Noten-PDF-, Datei-, Profilbild- und Klassenarbeitsfoto-Requests.
Wiederhergestellte Fotos ohne eigene Kontobindung werden vor dem Entfernen des
Benutzers synchron gelöscht. Die anschließende Bereinigung alter lokaler
Uploads, Entwürfe und Gerätezugänge bildet eine Barriere: Die Übernahme eines
neuen Kontos wartet darauf und scheitert geschlossen, falls sie fehlschlägt.

401 beim expliziten Login, bei der unabhängigen Ersteinrichtung und bei den
gesonderten Web-Bezahldokumenten beweist keinen Widerruf der App-Sitzung.
Eine HTML- oder sonst nicht als JSON lesbare 401 löst keinen globalen Logout
aus: Ein Proxy kann diese Antwort ohne Kenntnis des Sitzungszustands erzeugen.
Eine 401 eines passenden laufenden normalen API-Requests behält den bisherigen
Widerrufsweg. Responses werden weiterhin als Fehler an ihre Aufrufer gemeldet.

Die Tests verwenden ausschließlich künstliche Daten und lokale Mocktransporte.
Sie prüfen identische und geänderte Identitäten, den Cookie-Fall mit leerem
Token, neue Loginabsichten vor und während laufender asynchroner Abmeldung,
Absage vor einem Logout-Request und den Erhalt des neuen Logins nach dessen
Antwort. Der blockierte Bereinigungsfall prüft einen wirklichen Kontowechsel,
Speicherlöschung und den Fehlermodus. Tests auf VM und im Chrome-Webrunner ersetzen keinen Test echter
Server-Cookies und mehrerer Browser-Tabs.

**Sitzungscookie, 06.11.2026:** Ein Logout widerruft weiterhin zuerst die
zugehörige Sitzung in der Datenbank, sendet aber keinen Löschheader für
`sp_session`. Die zurückgehaltene Antwort einer alten Sitzung kann dadurch
einen zwischenzeitlich gesetzten Login-Cookie nicht entfernen. Der alte,
widerrufene HttpOnly-Cookie bleibt bis zum normalen Ablauf oder einem neuen
Login im Browser gespeichert; er berechtigt serverseitig nicht mehr zum
Zugriff. Ein lokaler Chrome-Test hielt die echte Logout-Antwort zwischen zwei
Tabs zurück, meldete ein zweites künstliches Konto an und prüfte, dass es
angemeldet blieb. Ein weiterer Logout ergab anschließend bei `/auth/me` 401.
Der Browserlauf verwendet isoliertes SQLite, keine produktiven Konten und keine
Flutter-Oberfläche. Login und Widerruf wurden zusätzlich in API-Tests geprüft.

**Weiter offen:** Ein älterer Logout kann noch den Cookie eines neu begonnenen
Google-Anmeldeflows löschen; umgekehrt darf ein laufender, ungebundener alter
Flow durch einen Logout nicht unbemerkt fortbestehen. Beide Fälle benötigen
eine gesonderte Lösung und echte Flow-Racetests. Bereits gestartete native
Ressourcenbereinigungen lassen sich durch diese nachgelagerten Checks nicht
rückwirkend abbrechen. Die Änderung garantiert weder die Handhabung aller
parallelen Loginantworten noch einen geräteübergreifenden Widerrufshinweis.
