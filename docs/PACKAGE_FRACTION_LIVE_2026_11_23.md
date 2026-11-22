# Paket-Bruchplanung: künstliche Live-Prüfung am 23. November 2026

Geprüfter Produktivstand: `b2094c425e24d173cd5eab503bf03ab871d0ff1a`,
Version 1.38.138. Die Aufträge nutzten zwei getrennte reguläre, ausdrücklich
als künstliche Tests angelegte Familien und je zwei selbst erzeugte Seiten.
Keine echten Kinderbilder oder Antworten wurden verwendet; die Testfamilien und
deren zeitweilige Beta-Freigaben wurden nach Abschluss entfernt. Die verwendeten
kurzlebigen lokalen Test-Administratoren wurden deaktiviert und ihre Sitzungen
widerrufen. Das ist kein Android- oder Browser-Sichttest.

| Fall | Ergebnis | Anbieterbetrag für den erfolgreichen Paketaufruf |
| --- | --- | --- |
| Brüche erweitern | Nach expliziter Wiederholung eine Runde mit einer vorab geplanten Aufgabe gespeichert; Planbindung und reguläre Veröffentlichung bestanden. | 0,003139 USD |
| Brüche kürzen | Nach expliziter Wiederholung eine Runde mit einer vorab geplanten Aufgabe gespeichert; der gespeicherte Grafik-Snapshot war `ready` und enthielt für diese Aufgabe zwei Lösungsbilder. | 0,034634 USD |

Die Sätze auf den künstlichen Kürzungsseiten waren jeweils über zwei Zeilen
umgebrochen. Der erfolgreiche Test verwendete dieselben vorher gespeicherten,
bestätigten Quellen wie der fehlgeschlagene erste Versuch. Der ursprüngliche
Auftrag war auf dem allgemeinen Pfad wegen Ausgabelänge fehlgeschlagen; sein
Anbieterbetrag betrug 0,005553 USD. Der Fix erkennt eine zusammengehörige,
wörtlich belegte Kürzungsregel auch über einen einzelnen Zeilenumbruch hinweg;
getrennte Absätze, Negationen und einschränkende Regeln bleiben ausgeschlossen.

Eine vorherige künstliche Erweiterungsprobe wurde wegen `invalid_schema`
abgewiesen; ihre Kosten waren unbekannt. Ein späterer Aufruf erreichte den
Anbieter, wurde aber bei der Planbindung abgelehnt (0,002978 USD). Da die
Modellantwort absichtlich nicht gespeichert wurde, ist deren konkreter
Fehler nicht nachträglich nachweisbar. Das Schema bindet seither jeden
Aufgabenplatz einzeln, und unzulässige Spezialrezepte werden nicht mehr für
normale Einführungsbilder angeboten. Beide Ablehnungen wurden nicht als Erfolg
gewertet. Die Beträge sind gemeldete Anbieterbeträge, keine Schätzungen; die
unbekannten Kosten des abgewiesenen Aufrufs bleiben unbekannt.

Die erfolgreiche Kürzungsrunde wurde mit Elternzugriff auf die künstliche
Testfamilie stichprobenartig gelesen: Eine kurze Vorwissensfrage zu Zähler und
Nenner ging einer Kürzungsaufgabe voraus; Hinweise und Erklärung beschrieben
die Division beider Bruchteile durch denselben Teiler. Es wurden keine
Antworten abgegeben. Die temporäre Kopie der künstlichen Ausgabe wurde danach
entfernt. Die Prüfung belegt nicht, dass jede künftig erzeugte Erklärung für
jedes Kind verständlich ist.

Die Wiederholungsdurchläufe dauerten anhand der lokalen Start-/Endzeit ihrer
Protokolle insgesamt ungefähr 47 Sekunden für Erweitern und 34 Sekunden für
Kürzen. Diese Zeiten enthalten Testanmeldung, Freigabe und Bereinigung; sie
sind keine reinen Modell-Latenzmessungen.

Lokale Regressionen verwendeten SQLite und isoliertes PostgreSQL: unter anderem
264 SQLite-Fälle für Transport, Bruchplanung und Grafikverträge sowie 147
PostgreSQL-Fälle für die Mathematik- und Paketprüfung; die zusätzliche
Workerprüfung für umgebrochene Regeln bestand mit 27 Fällen je Datenbank. Die
Tests decken feste und offene Vorwissensplätze, null bis zwei Übungsplätze,
Quell- und Rezeptbindung, fehlerhafte oder vertauschte Grafiken, mehrere Seiten,
Sitzungsentzug und konkurrierende Änderungen ab. Sie ersetzen keine allgemeine
Produktionsreife- oder Geräteabnahme.
