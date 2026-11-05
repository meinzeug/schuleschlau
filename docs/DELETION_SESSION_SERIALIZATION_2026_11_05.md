# Sitzungsschutz bei Löschungen

Die gezählten Heftseiten-, Einzelmaterial-, Tagesseiten- und Lernrundenlöschungen
sichern nach den bisherigen Unit- und Child-Sperren die tatsächlich verwendete
Sitzung bis zum Datenbankcommit. Unter PostgreSQL verwendet der gemeinsame Guard
`FOR UPDATE NOWAIT`: Ist die Session belegt, wird die gesamte Transaktion
zurückgerollt und die Aktion mit 409 beendet. Es gibt keine automatische
Wiederholung. Der Guard prüft anschließend Nutzer, Zuordnung, Widerruf, Ablauf
und Inaktivität erneut. Familien- und Schreibrechte sowie Quellrevisionen
werden danach wie bisher geprüft. Eine erfolgreiche Session-Zeilensperre
serialisiert den Gerätewiderruf mit dem Löschcommit.

Das nichtwartende Verhalten ist nötig: Die Annahme eines Familienanrufs sperrt
zuerst Session, danach Unit/Child. Ein wartendes Child→Session könnte gegen diese
Reihenfolge blockieren. Eine echte PostgreSQL-Gegenprobe startet beide Pfade
parallel und beobachtet den kontrollierten Konflikt statt Deadlock. SQLite hat
hier keinen Zeilenlock; der bereits vor dem Guard ausgeführte Child-Update hält
jedoch die SQLite-Schreibtransaktion. Eine getrennte SQLite-Verbindung mit
Busy-Timeout null bestätigt den Writer-Konflikt und den möglichen Widerruf nach
Commit. Diese Aussage gilt für die getesteten vier Löschpfade; sie behauptet
keine globale Deadlockfreiheit oder den Schutz aller anderen Schreibendpunkte.

`backend/tests/test_deletion_session_lock.py` prüft für jeden der vier
Löschpfade ein gehaltenes, uncommittiertes Widerrufs-Update: 409 ohne
Datei-/Antwort-/Journalverlust und nach Abschluss des Widerrufs 401. Für den
Einzelmaterialpfad prüfen zusätzliche reale API-Rennen beide Richtungen mit
Gerätewiderruf, Elternwiderruf und Logout, beide Reihenfolgen mit echtem
Familienentzug sowie den Familienanruf. Die erfolgreichen Löschungen und die
anschließende Widerrufswirkung werden aus den gespeicherten Zeilen überprüft.
SQLite und PostgreSQL werden getrennt ausgeführt; PostgreSQL-spezifische Fälle
sind auf SQLite ausdrücklich übersprungen.
