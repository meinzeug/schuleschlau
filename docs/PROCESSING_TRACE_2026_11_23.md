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
bereit. Seit 25.11.2026 werden bei Einzelaufträgen ohne Quellenliste auch die
ausdrücklich gespeicherten Felder `material_id` und `material_revision`
ausgewertet; fehlende oder ungültige Revisionen werden nicht aus dem aktuellen
Material ergänzt. Seiten anderer Kinder bleiben ausgeschlossen. Eine
Abschriftversion wird nur zugeordnet, wenn Material, Kind und die
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

Am 25.11.2026 wurden zusätzlich feste Phasen für Rückblick, Entscheidung,
Grafik und Grafikprüfung, Klassenarbeit, Wortschatz, Sprache, Lernhilfe und
Elternüberblick ergänzt; unbekannte Auftragsarten bleiben allgemein. Ein
Klassenarbeitsauftrag kann seine ausdrücklich gespeicherten Seitenrevisionen
zeigen, ohne Ausschnitte oder Zuordnungen auszugeben. Ein regulär angelegter
künstlicher Auftrag wurde vor und nach Verarbeitung mit simuliertem Transport
geprüft. Neue Lernrückblickaufträge speichern die bereits geprüften
Quellenkennungen und Revisionen direkt am Auftrag; alte Aufträge werden nicht
nachträglich ergänzt. Ein künstlicher Rückblick wurde vor und nach Verarbeitung
und nach einer späteren Quellenänderung geprüft. Die
Phasenbezeichnung allein belegt weder fachliche Qualität noch, dass zu jedem
Auftrag Quellen- oder Vorlagenbelege existieren.

Neu fehlgeschlagene Rückblick- und Anschlussübungsaufträge speichern die
begrenzte Fehlerklasse. Ein künstlicher Timeout-Fall prüft die Anzeige ohne
Anbietertext und den Erhalt bereits gespeicherter Antworten. Historische
Fehler ohne vorhandene Klasse bleiben `unknown`; aus Texten wird keine
nachträgliche Diagnose erfunden.

Die abschließende Regression für Auftragsspur und Lernrückblick bestand mit
je 89 Fällen auf isoliertem SQLite und PostgreSQL. Die Elternansicht bestand
18 Widgetfälle auf der Flutter-VM und im Chrome-Webrunner. Die
Anbieterantworten und Fehler waren künstlich.

Bei neuen Fehlern der Klassenarbeitsnacharbeit wird die vorhandene begrenzte
Fehlerklassifizierung ebenfalls gespeichert. Ein künstlicher Timeout im
regulären Worker ist mit der gebundenen Quellenrevision über die Elternspur
nachvollziehbar; Anbietertext und Aufgabeninhalt werden dort nicht ausgegeben.
Wiederholte Spurabrufe erzeugen keine Aufträge oder Lernnachweise. Der Test
wurde auch mit isoliertem PostgreSQL ausgeführt. Frühere Fehler bleiben
unverändert; die vollständige Abnahme aller Verarbeitungsschritte ist offen.

Grafikvorbereitungen speichern für neue Aufträge die im Grafikkontext
verwendeten Materialkennungen und Revisionen. Eine ältere Anfrage ohne diese
Metadaten bleibt mit demselben Idempotenzschlüssel wiederaufnehmbar; ihre
Quellen werden nicht rückwirkend geraten. Wird eine Modellantwort bei der
Schema- oder inhaltlichen Prüfung der Grafik verworfen, erhält der Auftrag die
begrenzte Klasse `invalid_output`. Ein künstlicher Fehlerfall prüft den
regulären Worker, die Elternspur und den Erhalt der gespeicherten Aufgabe und
Antwort. Die Prüfung ist kein fachlicher Qualitätsnachweis für alle Grafiken.
Ein weiterer künstlicher Fall ändert die Seite während des Anbieteraufrufs:
Das Ergebnis wird verworfen und die Elternspur zeigt die gebundene alte
neben der aktuellen Revision sowie `source_changed`. SQLite und isoliertes
PostgreSQL bestehen diesen und drei weitere Autoritäts-/Kontextwechsel.

Für Heftfragen liest die Elternspur gespeicherte Quellenrevisionen aus dem
zugehörigen Tutorvorgang, sofern dessen Auftrags- und Kindzuordnung
übereinstimmen. Frage, Antwort, Zitat und gespeichertes Quellenlabel werden
nicht ausgegeben. Verwirft die Quellenprüfung eine Antwort oder ein Zitat,
speichern neue Fehler die Klasse `invalid_output`. Vier künstliche Fälle mit
unpassenden Quellenbelegen und ein erfolgreicher, später geänderter
Quellenstand wurden auf SQLite und isoliertem PostgreSQL geprüft. Entferntes
oder unpassendes Bindeglied ergibt eine leere Quellenliste. Die Fälle
belegen keine generelle fachliche Qualität von Tutorantworten.

Neue Lernentscheidungs- und Anschlussübungsaufträge speichern die geprüften
Quellenkennungen und Revisionen. Ein künstlicher Timeout der Anschlussübung
erhält die bestehenden Antworten und den fertigen Rückblick; unbekannte
Anbieterkosten bleiben unbekannt. Alte idempotente Anschlussaufträge ohne
Quellenmetadaten erzeugen durch Wiederholung keinen weiteren Auftrag und
erhalten keine nachträglich geratene Quelle. Ein künstlicher
Verarbeitungsweg prüft außerdem die Ablehnung einer unbekannten Frage ohne
neuen Antwort- oder Lernstandsbeleg. Die genannten Fälle bestanden auf SQLite
und isoliertem PostgreSQL.

Wortschatzimporte und Sprachprojekte können ihre ausdrücklich gespeicherten
Seitenrevisionen anzeigen, solange der jeweilige Datensatz noch mit genau
diesem Auftrag und Kind verbunden ist. Frühere ersetzte Aufträge erhalten
keine nachträglich geratene Zuordnung. Neue Fehler speichern eine begrenzte
Klasse; unzulässige Wortvorschläge und ungültige Sprachprojekt-Ausgaben
werden als `invalid_output` geführt. Künstliche Erfolgs-, Quellenänderungs-,
Schema- und Belegfehler wurden über getrennte Eltern- und Kindersitzungen
auf SQLite und isoliertem PostgreSQL geprüft. Das belegt keine allgemeine
sprachdidaktische Qualität oder Verfügbarkeit eines echten Anbieters.

Bei mehrteiligen Paketen wird jetzt ausschließlich eine Verletzung des
Ausgabevertrags des einzelnen Teils als `invalid_output` klassifiziert;
Fehler der gespeicherten Planung werden nicht als Modellfehler umetikettiert.
Drei künstliche Workerfälle mit fehlenden Einheiten, falscher Fachgruppe oder
doppelten Aufgabenkennungen prüfen auf SQLite und isoliertem PostgreSQL den
erhaltenen vorherigen Teil, ältere Antworten, den tatsächlichen Kostenbeleg
und eine rein lesende Elternspur. Der Transport ist simuliert.
