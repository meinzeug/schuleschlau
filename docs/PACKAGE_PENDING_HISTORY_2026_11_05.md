# Verlauf noch nicht veröffentlichter Paketfragen

Stand 5. November 2026. Bislang erfasste der bestehende Dezimalplaner eigene
gespeicherte Einheiten und bestätigte Materialtexte, aber keine gültigen
Teilrunden, die bereits gespeichert und noch nicht veröffentlicht wurden.
Ein späterer Auftrag desselben Kindes konnte deshalb dieselben Zahlen erneut
auswählen. Die abschließende Prüfung sah diese Teilrunden ebenfalls nicht.

Der private Verlaufssammler berücksichtigt nun auch solche Teilrunden über alle
Schultage desselben Kindes und passend zum Fach. Er prüft bestehenden Teilplan,
Quellen- und Ausgabedigest sowie bei vorhandenen Aufträgen deren Auftrags- und
Abrechnungsbindung sowie Kind und Familie. Ein beschädigter relevanter Beleg
wird abgelehnt. Der vorhandene
Dezimalplaner verwendet daraus nur Zahlensignaturen; weder Antworten noch
vollständige alte Fragen werden dafür an den Anbieter weitergegeben. Vor der
Veröffentlichung wird die Historie erneut geprüft; dabei wird der eigene
Teilauftrag ausgeschlossen, fremde Teilaufträge bleiben wirksam. Vorhandene
Aufgaben und Antworten bleiben erhalten.

Die künstlichen Tests decken eigene und fremde Kinder, andere Fächer,
manipulierte Ausgaben, Quellenbindung, falschen Auftrag und Abrechnungsbeleg,
eigene Belegausnahme sowie die erneute Dezimalprüfung ab. Ein separater
PostgreSQL-Test lässt zwei simulierte Kandidaten unter der bestehenden
Kind-Zeilensperre dieselbe Bruchfrage vormerken und prüft, dass nur ein
Teilbeleg entsteht. Diese lokale Simulation belegt nicht den gesamten
Bruch-Paketablauf oder einen echten Anbieteraufruf.

Die Aufbewahrungsfristen bleiben unverändert: abgeschlossene nicht mehr
benötigte Jobs werden nach 30 Tagen, Usage nach 90 Tagen und Schultage nach
365 Tagen gelöscht. Bei einem mindestens 30 Tage alten, bewusst zurückgestellten
oder gespeicherten Schultag kann der Job bereits fehlen. Bei erkennbar alter
Usage beziehungsweise einem über 90 Tage alten Schultag ohne beide Belege sowie
bei einem über 90 Tage alten vorhandenen Job ohne Usage dient ein strukturell
intaktes altes Receipt ausschließlich als **unverifizierter negativer
Ausschluss** gegen Wiederholung. Es belegt weder Urheberschaft noch Leistung
und erlaubt keine Veröffentlichung. Ein fester inhaltsfreier Logcode weist auf
diesen Sonderfall hin. Fehlerhafte vorhandene Daten sowie fehlende Belege bei
aktiven oder jüngeren Aufträgen bleiben blockierend. Der reguläre Löschlauf für
31, 91 und 366 Tage wird isoliert getestet.

Die deterministische Planung initialer Bruchpakete ist **weiter offen**:
Der vorhandene isolierte Rechenprototyp ist nicht produktiv verdrahtet.
Insbesondere die feste gemeinsame Bindung von Aufgabenkern, Grafik und
Provider-Schema sowie deren erneute Prüfung vor Speicherung und Veröffentlichung
und die vollständige Abnahme mit echten künstlichen Anbieterfällen fehlen.
