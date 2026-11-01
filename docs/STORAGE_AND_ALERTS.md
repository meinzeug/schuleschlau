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
unmittelbare Nachlaufen auch für den getesteten Kalendertimer.

Der installierte Client aus `cee08c7` hält bei einem direkt vorangegangenen
Erfolg vor dem nächsten Abgleich einen Abstand von bis zu einer Minute ein.
Timer, vollständige Prüfsummenprüfung und Frischealarm bleiben unverändert;
ein fehlender, beschädigter oder zukünftiger Marker verzögert keinen Lauf.
Die künstlichen Tests prüfen außerdem, dass Warten und Abgleich unter derselben
exklusiven Offsite-Sperre stattfinden. Damit der Übertragung keine Zeit verloren
geht, beträgt die Standard-Servicefrist elf statt zehn Minuten und die lokale
Ausnahme 46 statt 45 Minuten. Der einstündige Frischealarm bleibt unverändert.
Nach der abgestimmten Installation bestand ein echter Abgleich: 381 Sicherungen
wurden prüfsummengeprüft, das verschlüsselte Journal kopiert und die lokalen
und serverseitigen Erfolgsmarker aktualisiert. Keine der Kopien benötigte einen
neuen Transfer; der Inhalt des verschlüsselten Journals wurde dabei nicht geprüft.
Die vorherigen Client- und Unit-Dateien liegen unter
`~/.local/share/schulpilot-operations/backups/pre-cee08c7/`. Fehlgeschlagene
Läufe und unerwartete Zeitänderungen sind weiterhin zu beobachten.

Eine weitere Prüfung am 01.11.2026 zeigte wiederholt zwölf beziehungsweise
vierzehn Archivdownloads pro Lauf: bereits abgelaufene Serverarchive wurden
übertragen und nach dem Journalabgleich lokal gleich wieder entfernt. Der
Client aus `6f1ef41` validiert das Inventar vor dem Download und überträgt nur
Archive innerhalb der 14-Tage-Frist. Alle verbleibenden Serverarchive werden
weiterhin anhand ihrer Prüfsummen geprüft. Der letzte Server-Archivstand muss
frisch sein; ungültige, doppelte oder zukünftige Inventare stoppen ohne
Bestätigung. Eine vorhandene lokale Altkopie wird weiterhin erst nach
erfolgreichem Journalabgleich entfernt. Der Server inventarisiert und hasht
auch seine älteren Archive; diese Änderung behebt deren Aufbewahrung nicht.

Der vorherige Client liegt unter
`~/.local/share/schulpilot-operations/backups/pre-6f1ef41/`. Der Timer wurde für
den atomaren Wechsel angehalten, ein bereits laufender Abgleich regulär beendet
und der Timer wieder gestartet. Der echte Nachlauf berücksichtigte 367
Sicherungen mit null neuen Archivdownloads und bestätigtem verschlüsseltem
Journal; beide lokalen Timer waren aktiv. Die lokalen und serverseitigen
Erfolgsmarker wurden aktualisiert und keine Transaktionsmarker blieben zurück.
Der Inhalt des verschlüsselten Journals wurde dabei nicht entschlüsselt geprüft.
Der Serverbestand enthielt am 01.11. um 16:39 UTC bereits ein Archiv älter als
14 Tage: Die tägliche serverseitige Bereinigung und der belegbare Spitzenbedarf
für Restore und Build müssen gesondert verbessert beziehungsweise gemessen werden.

### Produktiv: häufigere serverseitige Aufbewahrungsprüfung

Die bisherige tägliche Bereinigung wird durch einen eigenen Fünf-Minuten-Timer
ersetzt. Unter denselben Volume- und Archivsperren prüft der neue Dienst vor
jeder Löschung den jüngsten vollständigen Restore-Bericht, das dort benannte
Archiv mit vorhandenem Journalstatus, eine weitere aktuelle Sicherung und,
bei eingeschaltetem Offsite-Betrieb, eine höchstens eine Stunde alte Offsite-
Bestätigung. Unerwartete Dateinamen, Symlinks, ungültige Zeitstempel und andere
inkonsistente Metadaten stoppen die Bereinigung. Historische Archive ohne
separate Journalstatusdatei dürfen nur als auslaufende Altkopien entfernt
werden, nicht als Wiederherstellungsnachweis dienen. Der Wächter meldet einen
fehlgeschlagenen beziehungsweise inaktiven Timer und überalterte Archive.

Die Bereinigung beginnt zehn Minuten vor Ablauf der Höchstfrist; der Zeitpuffer
übersteigt das fünfminütige reguläre Prüfintervall. Bei ausgeschaltetem Host,
langen Sperren, fehlenden Nachweisen oder sonstigen Störungen kann die Frist
überschritten werden: Dann wird nicht blind gelöscht, sondern eine Störung
angezeigt. Die tatsächliche maximale Aufbewahrung bei Ausfällen ist daher
keine technische Garantie. Ein lesender, gesperrter Trockenlauf des neuen Codes identifizierte zunächst
18 Kandidaten. Nach regulärem Abschluss des laufenden Offsite-Abgleichs
entfernte die neue Prüfung diese 18 abgelaufenen Archive unter den vorgesehenen
Sperren und mit gültigem Restore- und Offsite-Nachweis. Release `534009f` wurde
anschließend aktiviert. Eine neue Sicherung wurde isoliert und authentifiziert
wiederhergestellt; 393 Löschjournal-Einträge wurden geprüft, Sitzungen
widerrufen und der KI-Notstopp gesetzt. Die Produktionsdatenbank wurde nicht
überschrieben. Nach dem Wechsel meldete der Server 366 Archive und keines über
14 Tagen. Der neue Dienst lief erfolgreich; sein Timer führte ihn am 01.11.2026 um
18:45 UTC auch planmäßig mit Status `success` aus. API, Worker und
Restore-Timer waren aktiv. Der Serverwächter meldete im Trockenlauf keine
Fehler. Der anschließende unabhängige Abgleich übertrug drei neue Archive,
bestätigte 366 Kopien und ein verschlüsseltes Journal; beide lokalen Timer
waren danach aktiv. Die verschlüsselte Journalkopie wurde dabei nicht auf ihren
Inhalt geprüft. Der lokale und der Server-UTC-Zeitstand unterschieden sich bei
der Prüfung um ungefähr eine Stunde, daher ist für die Aufbewahrung die
jeweilige Serverzeit maßgeblich. Eine spätere Überschreitung bei Ausfällen
bleibt möglich und muss überwacht werden.

Der unabhängige Wächter enthält zusätzlich eine lokal getestete Prüfung auf
unvollständige Offsite-Journaltransaktionen. Bleiben `.erasure-ledger.pending`
oder `.erasure-ledger.previous` nach Freigabe der Pull-Sperre liegen, meldet er
`offsite_transaction_incomplete`. Während ein normaler Pull die exklusive
Sperre hält, meldet er diese kurzzeitig erwarteten Dateien nicht als Fehler;
der bestehende Frischealarm bleibt als Schutz gegen einen dauerhaft hängenden
Pull bestehen. Fehlende oder nicht vertrauenswürdige Sperren bei vorhandenen
Transaktionsdateien gelten als Störung. Der Watchdog aus Commit `96c43ca` wurde nach dem erfolgreichen Offsite-Lauf
atomar installiert; der vorherige Stand liegt unter
`~/.local/share/schulpilot-operations/backups/pre-96c43ca/`. Der installierte
Wächter meldete bei einem künstlich unterbrochenen Journalwechsel in einem
separaten temporären Home-Verzeichnis die erwartete neutrale Störung; bei
synthetisch gehaltener Pull-Sperre blieb er ohne Fehlalarm. Es wurde keine
Nachricht versandt. Der reale lesende Trockenlauf war fehlerfrei und
beide lokalen Timer waren aktiv. Die Transaktionsdateien dürfen nicht
automatisch gelöscht werden.

### Uhrzeit des unabhängigen Rechners

Am 01.11.2026 zeigte die UTC-Systemuhr des unabhängigen Rechners bei der
lesenden Prüfung rund 59 Minuten mehr als die per NTP synchronisierte Serveruhr
und eine unabhängige UTC-Zeitabfrage. Lokal meldete `timedatectl` sowohl
`NTP=no` als auch `NTPSynchronized=no`; auf dem Server waren beide Werte `yes`.
Die lokalen Erfolgs- und Alarmzeitstempel verwenden die lokale Uhr, die
Aufbewahrungsentscheidung verwendet ausdrücklich die Serverzeit. Der
Timestamp im Namen von Release `20261101T193953Z-534009f` stammt von der
lokalen Uhr und ist daher keine verlässliche UTC-Zeitangabe für die
Aktivierung. Der unabhängige Rechner ließ keine nichtinteraktive
Administratorausführung zu; seine Systemuhr wurde nicht verändert. Eine
Korrektur muss Auswirkungen auf andere lokale Prozesse berücksichtigen. Nach
einer Rückstellung können vorhandene lokale Erfolgsmarker vorübergehend in der
Zukunft liegen; ein neuer erfolgreicher Offsite-Abgleich und der Wächter sind
dann ausdrücklich zu prüfen, statt Marker manuell umzuschreiben.

Bei einer weiteren regulären isolierten Wiederherstellungsprobe am 01.11.2026
wurden während des Dienstlaufs in 100-ms-Abständen verfügbare Bytes auf `/`
und die Größe der Dateien im privaten temporären Dienstverzeichnis gemessen.
Die erfolgreiche Probe dauerte 5,1 Sekunden (50 Messpunkte). Beobachtet wurden
höchstens 125.487.528 Byte temporäre Dateien und ein Rückgang des auf `/` für
normale Nutzer verfügbaren Platzes um bis zu 193.060.864 Byte gegenüber dem
Startwert. Der zweite Wert kann auch gleichzeitige andere Aktivitäten enthalten;
kurze Spitzen zwischen den Messpunkten bleiben unsichtbar. Die Messung gilt nur
für diese Sicherung und ersetzt weder eine garantierte Platzobergrenze noch die
Messung von Backup, Releasebuild und künftigem Datenwachstum.

Eine anschließend ebenfalls in 100-ms-Abständen beobachtete reguläre
Sicherung dauerte 1,4 Sekunden (14 Messpunkte). Im privaten temporären
Dienstverzeichnis wurden bis zu 68.055.520 Byte beobachtet; der verfügbare
Platz sank auf `/` gegenüber dem Ausgangswert um bis zu 68.087.808 Byte und
auf dem Sicherungsvolume um bis zu 62.812.160 Byte. Auch diese Werte sind
Stichproben mit möglicherweise verpassten kurzen Spitzen und gleichzeitigen
Fremdaktivitäten, keine zulässigen Höchstwerte für spätere größere Datenmengen.
Der nach dieser Messsicherung eigens angestoßene Offsite-Abgleich war
erfolgreich, kopierte ein zusätzliches Archiv und meldete 367 Kopien sowie
ein verschlüsseltes Journal. Es blieben keine angefangenen Journaltransaktionen
zurück; beide lokalen Timer und die lesenden Trockenläufe von Server- und
unabhängigem Wächter waren fehlerfrei.
