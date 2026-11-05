# Verspätete 401-Antworten und Sitzungswechsel

Ein alter Request darf nach einem Kontowechsel, Tokenwechsel oder Beginn einer
neuen Authentifizierung die neue Sitzung nicht abmelden. Der Client bindet
seine 401-Seitenwirkung an Benutzerobjekt, Bearertoken und lokale
Authentifizierungsrevision. Letztere unterscheidet im Web auch zwei
Cookie-Sitzungen, bevor das neue Benutzerobjekt eintrifft. Der asynchrone
Abmeldeweg prüft denselben Auftrag nach seinen Warteschritten erneut. Das gilt
auch für Foto-, Noten-PDF-, Datei-, Profilbild- und Klassenarbeitsfoto-Requests.

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
Antwort. Tests auf VM und im Chrome-Webrunner ersetzen keinen Test echter
Server-Cookies und mehrerer Browser-Tabs.

**Offen:** Ein vor einer neuen Web-Anmeldung bereits abgesendeter Logout kann
später eintreffen und sein serverseitiges `Set-Cookie` zum Löschen nach dem
neuen Login im Browser anwenden. Der Browser verarbeitet diesen Header
unabhängig vom Flutter-Response-Handler; die lokale Revisionsprüfung löst das
nicht. Dies betrifft insbesondere mehrere Tabs und erfordert eine gesonderte
Server-/Browserlösung mit echtem Race-Test. Auch bereits gestartete native
Ressourcenbereinigungen lassen sich durch diese nachgelagerten Checks nicht
rückwirkend abbrechen.
