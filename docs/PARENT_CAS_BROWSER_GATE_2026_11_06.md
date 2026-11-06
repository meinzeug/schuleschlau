# Zwei-Eltern-Konfliktprüfung im Browser-Gate

Der bestehende künstliche Zwei-Eltern-Fall wird durch den gemeinsamen
CI-Browserrunner zusätzlich zum Hefter- und Wiederholungsablauf aufgerufen.
Zwei getrennte mobile Chrome-Kontexte bearbeiten die Lernvorgaben desselben
Testkindes auf Basis derselben gespeicherten Revision. Ein Elternkonto
speichert ein anderes Tagesziel, Wiederholungsthema und den Entzug der
Push-Freigabe. Die nachfolgende veraltete Änderung des zweiten Kontos wird
mit HTTP 409 abgewiesen; sein Entwurf bleibt bis zur bewussten Entscheidung
sichtbar. Ein künstlicher Aufruf ohne Revisionsangabe erhält HTTP 428. Der
abschließende Datenbanktest kontrolliert den tatsächlichen Elternstand, den
Entzug des künstlichen Geräts, genau einen zugehörigen Lernauftrag sowie keine
KI-Jobs oder Anbieteraufrufe.

Der Test benutzt eine automatisch angelegte temporäre SQLite-Datenbank und
fest vorgegebene künstliche Konten. Eine von außen gesetzte Testdatenbank wird
vor den verändernden Fixtures abgewiesen; dieser Negativfall ist ebenfalls im
Runner verpflichtend. Der Browser sperrt fremde HTTP-Ursprünge, Redirects,
WebSockets und Service Worker. Playwrights separate API-Anfragen für den
gezielten Altclientvergleich sind auf den validierten Loopback-Ursprung und
feste Pfade beschränkt und folgen keinen Redirects. Diese Schutzmaßnahmen
sind keine Netzwerkisolierung des Betriebssystems oder von Chromium-Diensten.

Am 06.11.2026 bestanden der reale lokale Chrome-Fall und der Negativtest mit
zwei Tests. Der Test nutzte ein vorhandenes lokal gebautes Webartefakt; das ist
kein Nachweis eines neuen Releasebuilds. Der JUnit-Vertrag fordert beide Fälle
zusätzlich zu den bisherigen vier ohne Fehler oder Skip. Ein tatsächlicher
GitHub-Lauf und der kombinierte Runner sind für die entsprechende Revision
jeweils gesondert nachzuweisen. Weder reale Firebase-Zustellung noch eine
umfassende Eltern-, Datenschutz- oder Geräteabnahme wird damit behauptet.
