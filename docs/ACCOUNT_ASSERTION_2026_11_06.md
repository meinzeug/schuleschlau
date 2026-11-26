# Begrenzte Absicherung bei Kontoänderung im Browser

Die gemeinsame Flutter-API sendet bei bekanntem Konto dessen Kennung als
`X-Schulpilot-Account`. `authenticated()` prüft nach der bestehenden
Sitzungs- und Nutzerprüfung, ob der optionale Header zum tatsächlich über
Cookie oder Bearer authentifizierten Konto passt. Bei Abweichung antwortet der
Server vor privaten Nutzdaten oder zustandsändernden Aktionen mit 409 und
„Das Konto auf diesem Gerät hat sich geändert. Bitte melde dich erneut an.“
Der Header ist lediglich eine zusätzliche Ablehnungsbedingung: Er berechtigt
zu nichts und beeinflusst weder Kontoauswahl noch Familien- und Rollenrechte.
Alte Clients ohne Header behalten ihr bisheriges Verhalten.

Die Antwort markiert diesen Konflikt zusätzlich mit
`X-Schulpilot-Account-Changed: 1`. Führt der Benutzer danach ausdrücklich
„Abmelden“ aus, verwirft der Client nur die alte lokale Kontoansicht, wenn die
Antwort noch zu derselben lokalen Anmeldung gehört. Er wiederholt den Logout
nicht mit dem möglicherweise fremden Cookie. Die andere serverseitige Sitzung
wird nicht widerrufen. Ein allgemeiner 409 oder eine verspätete Antwort nach
einem weiteren Kontowechsel darf den neuen lokalen Zugang nicht löschen. Beim
späteren Kaltstart kann der vorhandene Browsercookie weiterhin die dort
bestehende Sitzung melden; dies ist keine Lösung des Cookie-Races.

Ein isolierter echter Chrome-/SQLite-Test lässt die ältere Loginantwort nach
einer neueren eintreffen. Der Cookie wechselt weiterhin; ein anschließender
`/auth/me`-Aufruf und ein Logout mit der vom neueren Konto erwarteten Kennung
werden mit 409 zurückgewiesen. Ein unmarkierter Request zeigt die tatsächliche
ältere Sitzung und bestätigt, dass der zurückgewiesene Logout sie nicht
widerrufen hat. Die Flutter-Tests prüfen die Headerbildung beim Kaltstart und
nach Login, den ausdrücklichen lokalen Logout, andere 409-Antworten und eine
verspätete Antwort nach einem weiteren Kontowechsel. Die Flutter-Tests nutzen
Mocktransporte; der Cookie-Test nutzt die echte HTTP-API, aber keine
Flutter-Oberfläche und ausschließlich künstliche Konten.

Grenzen bleiben: Bei unbekanntem Konto, älteren Clients und Pfaden ohne diesen
Header gilt kein zusätzlicher Kontovergleich. Unterschiedliche Sitzungen
**desselben** Kontos werden nicht unterschieden. Ein noch laufender Login kann
den Lernplan mit dem bisher passenden Cookie erneut laden. Google-Flow- und
Demo-Anmeldungen sowie direkte Browsernavigationen erhalten dadurch keine
serverseitige Anmeldegeneration. Die Einführung dieser begrenzten Prüfung
schließt deshalb weder die in `WEB_LOGIN_COOKIE_RACE_2026_11_06.md`
beschriebene Ursache noch den gesamten Roadmap-Hauptpunkt.

Bei `/notifications/config` fällt nur eine fehlende oder ungültige Sitzung
(401) auf die öffentliche Konfiguration zurück. Ein Konto-Konflikt (409) darf
insbesondere die Push-Freigabeprüfung eines Kindes nicht umgehen. Ein
synthetischer Test prüft Kind ohne Freigabe, falschen Kontoheader und anonymen
Zugriff. Die Foto-Annahme weist einen falschen Kontoheader bereits vor der
Verarbeitung zurück; der Test prüft unveränderte Material- und Auftragszahlen.

Der untersuchte Eltern-Auftragseditor behält Eingaben nach dem 409 sichtbar im
offenen Formular und fordert zum Kopieren vor der erneuten Anmeldung auf. Das
Kontomenü bietet anschließend einen erreichbaren Abmeldeweg. Das ist kein
kontenübergreifend gespeicherter Entwurf: Beim ausdrücklichen Abmelden gelten
weiterhin die bestehenden Datenschutzregeln zum Löschen lokaler Daten. Andere
Editoren sind durch diesen einzelnen Test nicht auf Eingabenerhalt geprüft.

## Zusätzliche Sitzungsprüfung vom 26.11.2026

Eine erfolgreiche Anmeldung und `/auth/me` liefern zusätzlich einen aus der
internen Sitzungskennung abgeleiteten, nicht authentifizierenden Vergleichswert.
Die gemeinsame Flutter-API sendet ihn, solange sie eine gültige aktuelle
Sitzung kennt, als `X-Schulpilot-Session`. Die API vergleicht ihn erst nach der
regulären Authentifizierung mit der tatsächlich gewählten Sitzung; eine
Abweichung wird vor privaten Daten oder Aktionen mit 409 zurückgewiesen.
Der Vergleichswert kann keine Sitzung auswählen, verlängern oder ersetzen.
Fehlt er bei älteren Clients oder direkter Browsernavigation, gilt weiterhin
die bisherige Sitzungskontrolle.

Ein isolierter Chrome-Test mit künstlichem Konto hielt eine erfolgreiche alte
Loginantwort zurück, ließ eine neuere Anmeldung **desselben Kontos** eintreffen
und gab anschließend die alte Antwort frei. Der Browser übernahm weiterhin den
alten Cookie. Mit dem Vergleichswert der neueren Sitzung wurden der folgende
Lesezugriff und Logout jedoch abgewiesen; ein unmarkierter Zugriff belegte,
dass die ältere Sitzung dadurch nicht widerrufen wurde. Der bestehende Test
für verschiedene Konten blieb ebenfalls bestehen. Künstliche API-Tests prüfen
korrekte, fehlende und ungültige Vergleichswerte sowie die Nicht-Autorisierung.

Dies ist eine begrenzte zusätzliche Ablehnung, keine Lösung der Cookie-Ursache:
Der alte Cookie kann die neue Sitzung weiterhin verdrängen und eine erneute
bewusste Anmeldung erfordern. Nicht markierte Zugriffe, Altclients, direkte
Browserressourcen, getrennte Transporte und Bootstrap-/Google-/Demo-Rennen
sind damit nicht vollständig abgesichert. Kein Produktions-Release wurde für
diese Ergänzung ausgeführt.

Die zugehörigen künstlichen Konto-, Google- und Adminfälle bestanden mit 72
Fällen auf isoliertem PostgreSQL. Ein zusätzlicher SQLite-Lauf bestand 14
Konto- und Sitzungsfälle. Flutteranalyse und 51 VM-Widgetfälle zu den
vorhandenen Authentisierungsabläufen bestanden; die ergänzte Headerprüfung
bestand danach separat. Alte und neue Browser-Cookiefälle bestanden mit zwei
tatsächlichen lokalen Chrome-Instanzen und künstlichen Daten. Diese Prüfungen
belegen keinen geschützten Zugriff ohne den neuen Header und keine vollständige
Endgeräteabnahme.
Auch der Flutter-Webrunner bestand 44 künstliche Konto-/401-Clientfälle in
Chrome; er verwendet Mocktransporte und ersetzt den getrennten Cookie-Test
nicht.
