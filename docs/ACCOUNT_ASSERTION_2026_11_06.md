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
