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
