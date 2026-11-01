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

Seit Release `1.38.56+211` sind die Serverprüfungen aktiv; der unabhängige
Wächter und seine Monitorbibliothek wurden anschließend aktualisiert, der
vorherige Code bleibt lokal erhalten. Ein lesender Trockenlauf des neuen
Serverchecks und des unabhängigen Wächters meldete keine Fehler; dabei wurde
keine Alarmmail versandt. Die Stichtagsmessung und simulierte Alarme belegen
weder einen langfristigen Wachstumstrend noch eine tatsächliche Alarmzustellung.

Am 01.11.2026 benötigte ein erfolgreicher Offsite-Abgleich ungefähr 19 Minuten.
Da der Timer 15 Minuten nach Laufstart auslöst, startete anschließend sofort ein
weiterer vollständiger Prüfsummenlauf; dieser war nach rund elf Minuten
erfolgreich. Bei langsamer Platte kann das hohe dauerhafte I/O-Last erzeugen.
Ein isolierter Vergleich mit kurzen künstlichen systemd-Läufen zeigte dasselbe
unmittelbare Nachlaufen auch für den getesteten Kalendertimer. Eine Änderung
des Zeitplans oder der vollständigen Prüfsummenprüfung wurde nicht vorgenommen;
eine spätere Lösung muss den bestehenden Frischealarm und die Integritätsprüfung
erhalten und bei langen und fehlgeschlagenen Läufen praktisch geprüft werden.

Lokal vorbereitet ist ein Abstand von höchstens einer Minute, falls direkt
zuvor ein erfolgreicher Abgleich abgeschlossen wurde. Timer, vollständige
Prüfsummenprüfung und Frischealarm bleiben unverändert; ein fehlender,
beschädigter oder zukünftiger Marker blockiert und verzögert keinen Lauf.
Die künstlichen Tests prüfen außerdem, dass Warten und Abgleich unter derselben
exklusiven Offsite-Sperre stattfinden. Der installierte Client wird erst nach
Ende des laufenden Abgleichs gewechselt und danach erneut geprüft.
