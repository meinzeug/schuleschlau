# Lernplan: überholte Antworten nach neuer Anmeldung

06.11.2026, künstliches Elternkonto in Flutter-Widgettests. Beginnt während
laufender Anfragen eine neue Anmeldeabsicht, werden ältere Antworten eines
Lernplan-GETs nicht mehr übernommen. Der Lernplan fordert einen ausdrücklichen
neuen Leseabgleich, bevor die alten Themenkarten wieder angeboten werden.
Dasselbe gilt, wenn eine bereits abgesendete Abschluss-/Löschaktion während
einer neuen Anmeldung zurückkehrt: Ihr Ergebnis kann serverseitig bereits
vorliegen; es wird keine Mutation automatisch wiederholt. Bei einer ungewissen
Rundenvorbereitung bleibt der bisherige Idempotenzschlüssel für den bewussten
Abgleich erhalten. Ein bereits geöffneter Bestätigungsdialog schließt ohne
Änderung, falls seine Anmeldeabsicht veraltet ist.

Die Prüfung verwendet `app/test/parent_plan_auth_race_test.dart` und die
bestehenden Eltern-Lernplan- und Listenfälle. Sie ist kein Nachweis für alle
Elternansichten. Insbesondere sind andere Wochen-, Karten- und Editoraktionen
nicht vollständig an eine Anmeldeabsicht gebunden; der Anmeldebeginn sendet
kein separates Aktivitätssignal. Bereits vom Server ausgeführte Änderungen
werden nicht rückgängig gemacht, sondern anschließend lesend abgeglichen.

Die vier gezielten Widgetfälle bestanden auf Flutter-VM und im Chrome-Webrunner
bei 390 Pixeln. Zusammen mit den beiden bestehenden Eltern-Lernplan-/Listentests
bestanden 18 VM-Fälle. Der Chrome-Runner benötigte beim Beenden seines
Testprozesses nach erfolgreichem Lauf SIGKILL. Ein unabhängiger Code-Review
bestätigte die begrenzte Abdeckung; die oben genannten anderen Callbackwege
bleiben offen.

## Ergänzung: sichtbare Karten, Wochenansicht und Auftragseditor

Die zuletzt erfolgreich geladene Planansicht speichert zusätzlich die
Anmeldeabsicht ihres GETs. Ein späterer Anmeldebeginn oder Abbruch verändert
diese Revision. Themenaktionen, Runden- und Quellenlinks, die Wochenansicht,
Filter und die untersuchten Dialogstarts dürfen dann nicht mehr auf den alten
Plan wirken. Das Kind und seine bestehenden Daten bleiben dabei unverändert.
Die erste blockierte Aktion fordert einen ausdrücklichen erneuten Leseabgleich;
nach erfolgreichem GET funktionieren Aktionen unter der neuen Revision wieder.
Ein im Moment der Änderung bereits abgesendeter Auftrag wird nicht wiederholt.

Ein bereits offener Auftragseditor prüft die gebundene Revision vor dem
Speichern. Wird eine veraltete Speicherung oder ein veraltetes Schließen
angestoßen, wird der zugehörige Editor entfernt. Trifft das Ergebnis eines
bereits abgeschickten Speichervorgangs spät ein, schließt der veraltete Editor
ebenfalls und der Plan verlangt einen lesenden Abgleich; der Server kann den
Auftrag bereits gespeichert haben. Eine offen gebliebene Rundenvorbereitung
behält beim anschließenden Abgleich ihren Idempotenzschlüssel.

Grenzen: `beginAuthentication()` sendet weiterhin kein eigenes AppState-Signal.
Ein passiv offener Dialog wird deshalb nicht allein beim Anmeldebeginn entfernt,
sondern sobald eine reguläre Identitätsbenachrichtigung erfolgt oder die hier
geprüfte Editoraktion ausgeführt beziehungsweise die bereits laufende Antwort
abgeschlossen wird. Auch ist ein stiller Cookiewechsel durch einen anderen Tab
ohne gemeldete Anmeldeabsicht damit nicht erkannt. Der Nachweis beschränkt sich
auf die beschriebenen Lernplanwege und ersetzt keine vollständige Prüfung aller
Anwendungsdialoge.


Weitere offene Grenze aus dem unabhängigen Review: Die Ansicht kann nicht
unterscheiden, ob eine neue Anmeldeabsicht noch läuft oder bereits beendet ist.
Wird während einer noch laufenden Anmeldung ausdrücklich neu geladen, kann der
GET noch mit der alten Sitzung erfolgreich sein und die Planaktionen wieder
freigeben. Eine zuverlässige Sperre erfordert ein sitzungsübergreifend sauber
verwaltetes Pending-Signal; sie ist hier nicht implementiert. Daher belegen die
Tests keinen vollständigen Schutz während einer laufenden Anmeldung. Die beiden
Paginierungsbuttons prüfen vor dem Seitenwechsel ebenfalls die alte Revision.

Im abschließenden VM-Lauf bestanden neun gezielte Fälle einschließlich der
Paginierung und der verspäteten Editorspeicherung. Der unmittelbar davor
geprüfte Stand ohne den zusätzlichen Paginierungsfall bestand acht gezielte
Chrome-Webrunner-Fälle; die Läufe sind keine echte tabübergreifende
Cookieprüfung. Die bestehende Plan-/Listen-/Editorsuite bestand im vorigen
Stand zusammen mit den damals sieben gezielten Fällen mit 36 VM-Fällen.

Nachlauf: Ein fehlgeschlagener gefilterter Abruf auf älteren Backends muss
weiterhin ein Zurücksetzen der Suche erlauben, obwohl absichtlich keine
ungefilterten Karten geladen wurden. Der Filter-Neuversuch ist daher an die
Revision des fehlgeschlagenen Abrufs gebunden; nach einem Anmeldebeginn ist
zuerst ein erneuter Leseabgleich nötig. Die vollständige Filter- und die
Anmelde-Rennsuite bestanden zusammen mit 23 VM-Fällen einschließlich beider
Grenzen. Das zuvor beschriebene fehlende Pending-Signal bleibt offen.
