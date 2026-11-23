# Datensparsame Auftragsspur vom 23.11.2026

`GET /api/jobs/{id}/trace` liefert ausschließlich berechtigten Eltern der
zugehörigen Familie technische Metadaten zu einem vorhandenen Auftrag. Kinder,
fremde Familien und Betriebsadministratoren erhalten keinen Zugang. Die
Antwort enthält Phase, Status, eine beschränkte Fehlerklasse und, falls genau
ein zugehöriger Verbrauchsbeleg vorhanden ist, Anbieter, Modell und
Konfigurationsrevision. Mehrdeutige Belege werden als solche gekennzeichnet.
Für fehlgeschlagene Aufträge können genau zugeordnete, geschlossene Diagnosen
zusätzlich ein erreichtes Ausgabelimit oder bestimmte Bruchprüfungsfehler
benennen. Unbekannte, manipulierte oder mehrdeutige Telemetrie wird nicht
übernommen. Die Elternansicht übersetzt diese Gründe in kurze Sätze.

Für bekannte zugehörige Quellen stehen angeforderte und aktuelle Revision
bereit. Eine Abschriftversion wird nur zugeordnet, wenn Material, Kind und die
im gespeicherten Beleg vermerkte Auftrags-ID übereinstimmen. Bei abgeschlossenen
Runden sind die tatsächlich gespeicherten, noch im Referenzkatalog vorhandenen
Grafikreferenzen und Versionen erreichbar. Pro Anfrage sind Quellen, Runden
und untersuchte Referenzbelege begrenzt; gekürzte Listen werden markiert.
Alte, fehlende, fremde oder nicht eindeutig zuordenbare Informationen bleiben
leer und werden nicht ergänzt oder geraten.

Der lesende Endpunkt erstellt keine Aufträge, Antworten, Aktivitäten oder
Lernnachweise. Er gibt weder Quelltext, Foto, Antwort, Anbieterfehlertext noch
ungesichtete Telemetrie aus. Künstliche Tests prüfen Berechtigung, manipulierte
Zuordnungen und wiederholte GETs. Der zusammenhängende Worker-Test führt
Erkennung, Gegenprüfung und Paketverarbeitung durch und prüft gespeicherte
Referenzen; separate provozierte Fehler betreffen beide Leseschritte und eine
ungültige Paketantwort mit erhaltenem Kostenbeleg. Modelltransporte sind dabei
simuliert. Auf der Vorbereitungsseite können Eltern die Details ausdrücklich über
„Verarbeitung ansehen“ öffnen; Kinder sehen diesen Bereich nicht. Die
vollständige fachübergreifende Phasenabnahme bleibt offen.
