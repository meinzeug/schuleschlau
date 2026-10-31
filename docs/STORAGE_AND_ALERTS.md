# Speicher und Störungsüberwachung

Messung vom 31.10.2026, nur eine Momentaufnahme: Auf dem Server sind auf der
Systemplatte 15.812.423.680 Byte und auf dem 50-GB-Sicherungsvolume
37.292.425.216 Byte für normale Nutzer verfügbar. PostgreSQL meldete
74.087.447 Byte Datenbankgröße; private Uploads belegten 55.291.999 Byte,
Releaseverzeichnisse 700.092.222 Byte und das Sicherungsverzeichnis
12.518.189.907 Byte. Der unabhängige Rechner meldete auf seinem
Offsite-Dateisystem 4.328.330.723.328 Byte frei. Das Backup-Verzeichnis enthielt
377 Archive mit insgesamt 12.515.985.184 Byte, das größte 60.661.792 Byte.
Dateisystem- und Verzeichniswerte sind nicht unmittelbar addierbar.
Die größten einzelnen Archive pro Tag stiegen vom 18. Oktober
(10.362.912 Byte) bis 31. Oktober (60.661.792 Byte); die Anzahl und Größe
schwankten stark, am 30. Oktober etwa 59 Archive mit zusammen 3.561.402.208
Byte. Daraus lässt sich weder ein konstanter täglicher Zuwachs noch ein
langfristig sicherer Füllzeitpunkt ableiten. Die Messung umfasst nur die
aktuell erhaltenen Sicherungen.

Für die aktuelle Größenordnung plant die neue Sicherungsvolume-Warnung den
Platz für zwei größte beobachtete Archive plus 1 GiB Reserve ein; zusätzlich
warnt sie bei mehr als 90 Prozent nutzbarer Belegung. Das sind zum Messzeitpunkt
1.195.065.408 Byte und keine Prognose für künftiges Wachstum. Für Root-reservierte
Blöcke zählt nur der tatsächlich verfügbare Platz. Der Backup-Prozess erstellt
Datenbank-Dump und unverschlüsseltes Zwischenarchiv im temporären Verzeichnis
der Systemplatte; die Archivgröße allein ist daher keine belastbare Obergrenze
für einen Restore oder Releasebuild. Deren konkreter Spitzenbedarf und der
langfristige Wachstumstrend bleiben zu messen.

Der unabhängige Wächter meldet fehlenden, beschädigten, zukünftigen oder mehr
als eine Stunde alten Offsite-Erfolgsstand sowie mangelnden oder nicht
ermittelbaren Platz des Offsite-Dateisystems. Der Serverwächter meldet
Speichermangel und fehlgeschlagene Platzabfragen getrennt für System- und
Sicherungsdateisystem. Ist eine Volume-UUID eingerichtet, prüft der
Serverwächter außerdem, ob genau dieses Volume am vorgesehenen Mountpunkt
eingehängt ist. Meldungen enthalten neutrale Fehlercodes. Die Tests
verwenden ausschließlich künstliche Dateisystemwerte und simuliertes SMTP;
sie belegen weder die tatsächliche Mailzustellung noch eine Überwachung des
vollständig ausgefallenen unabhängigen Rechners.

Nach einem Alarm: zunächst Dateisystem, Mount und aktive Backup-/Restore- und
Offsite-Prozesse prüfen; niemals Archivkopien oder Löschjournal ungeprüft
entfernen. Bei Mountfehlern den Backupbetrieb nach `docs/OPERATIONS.md`
absichern, Kapazität und Aufbewahrung koordinieren und nach Behebung beide
Wächter sowie eine neue Sicherung und den unabhängigen Abgleich prüfen.
Zuständig ist der Betreiber; bei Ausfall des Alarmwegs sind die Dienste und
Statusdateien über einen unabhängigen Zugang zu prüfen.

Die hier beschriebenen neuen Checks sind erst nach abgestimmtem Serverrelease
und Aktualisierung des unabhängigen Clients im Betrieb wirksam. Dabei den
bisherigen Offsite-Client bis zur Übernahme erhalten. Eine lokale Simulation
und diese Stichtagsmessung sind keine Produktionsabnahme. Ein lesender
Trockenlauf des neuen Serverchecks auf dem Zielhost und ein Trockenlauf des
neuen unabhängigen Wächters meldeten am 31.10.2026 keine Fehler; dabei wurde
keine Alarmmail versandt und kein installierter Dienst verändert.
