# JSON-Antworten bei Anmeldewechsel

Der gemeinsame Flutter-JSON-Transport bindet Antworten von bereits angezeigten
Konten an dieselbe lokale Kontoidentität, denselben Token und dieselbe
Anmeldeabsicht wie die Anfrage. Wird eine dieser drei Angaben vor oder während
des Lesens der Antwort geändert, liefert der Transport weder alte Antwortdaten
noch den alten Fehlermeldungstext an den Aufrufer. Ein überholter 401 löst keine
Abmeldung des neuen Kontos aus. Ein Transportfehler nach dem Wechsel erhält
denselben neutralen Fehlercode `authentication_changed`.

Bei GET bittet der Hinweis um erneutes Laden. Bei Schreibanfragen ist das
Ergebnis ausdrücklich unbekannt: Der Server kann die Änderung bereits
angenommen haben. Der lokale Fehler verwendet Status `0`, keinen behaupteten
serverseitigen 4xx-Fehler, und löst selbst keinen erneuten Versuch aus. Dadurch
können bestehende explizite Wiederholungen ihren Idempotenzschlüssel behalten.
Eine neue Anmeldung während einer laufenden Abmeldung darf durch deren alten
Fehler nicht entfernt oder blockiert werden.

## Prüfumfang und Grenzen

Künstliche Fluttertests verzögern GET-, POST-, PUT- und DELETE-Antworten für
Konto-, Token- und Absichtswechsel; zusätzlich prüfen sie stückweise gelesene
Antworten, einen veralteten 401 und einen Transportfehler. Die reguläre
Anmeldung, Abmeldung und die Verwendung des erwarteten Kontos sind separat
abgedeckt. Der Chrome-Webrunner führt dieselbe Flutter-Logik mit synthetischem
HTTP-Transport aus; er ist **kein** Test realer Browser-Cookies.

Der Schutz gilt nur für `Api.call` mit bei Anfragebeginn angezeigtem Konto.
Direkte Ressourcen, Datei-/Foto-Uploads, Binärabrufe, Streaming außerhalb dieses
JSON-Pfads, anonym oder während des Wiederaufnehmens eröffnete Anfragen,
Familienwechsel ohne Identitätsänderung und ältere Clients sind damit nicht
allgemein abgedeckt. Der Browser kann einen verspäteten `Set-Cookie` trotzdem
übernehmen. Eine nachträgliche lokale Prüfung kann eine bereits angenommene
Servermutation oder eine Cookieänderung nicht rückgängig machen. Die
[gesonderte Cookie-Race-Untersuchung](WEB_LOGIN_COOKIE_RACE_2026_11_06.md)
bleibt offen. Keine privaten Inhalte oder Kennungen sind für diese Prüfungen
notwendig.

Rückblick, Materialaktionen und Fachstufenwahl behandeln die neue neutrale
Abbruchmeldung ebenfalls: Überholte Aktionen öffnen keinen fremden Dialog und
laufen nicht im neuen Konto weiter. Bestehende Fehler bei weiterhin gültiger
Sitzung bleiben sichtbar. Der gezielte Arbeitsstand bestand 113 Fluttertests;
70 einschlägige Fälle liefen zusätzlich mit Chrome und künstlichem Transport.
Der umfangreiche Gesamtlauf wurde nach Korrektur der dabei gefundenen neun
Folgefehler erneut gestartet und ist zum Zeitpunkt dieses Eintrags noch nicht
abgeschlossen.
