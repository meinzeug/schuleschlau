# Offsite-Client getrennt vorbereiten

`scripts/stage_offsite_client.py` legt einen Offsite-Client-Kandidaten
revisionsgebunden in einem bereits vorhandenen privaten Verzeichnis ab. Es
liest ausschließlich drei feste reguläre Git-Blobs aus dem ausdrücklich
genannten vollständigen Commit: Client, Service und Timer. Uncommittierte
Änderungen des Checkouts werden nicht übernommen. Dateibytes und Manifest werden
einzeln synchronisiert; ein angefangener Ordner bleibt nach Fehlern bestehen und
wird beim nächsten Staging nicht überschrieben.

Der Operator muss Repository, Commit und Ziel selbst unabhängig prüfen. Beispiel
mit einem bereits vorhandenen privaten Zielverzeichnis und vollständig
angegebener, vertrauenswürdig ermittelter Commitkennung:

```sh
python3 scripts/stage_offsite_client.py stage --repo /pfad/zum/repo \
  --destination /pfad/zum/privaten/staging --revision VOLLSTAENDIGER_COMMIT
python3 scripts/stage_offsite_client.py verify --repo /pfad/zum/repo \
  --destination /pfad/zum/privaten/staging --revision VOLLSTAENDIGER_COMMIT
```

`verify` vergleicht die Dateien und das Manifest erneut byteweise mit den
Git-Blobs und synchronisiert nach erfolgreichem Vergleich alle geprüften Dateien
sowie Kandidaten- und Elternverzeichnis. Ein Abbruch nach dem Schreiben des
Manifests kann so erst nach erneutem vollständigen Vergleich und erfolgreicher
Synchronisierung geprüft werden; ein fsync-Fehler verweigert den Erfolg. Ein
nicht vertrauenswürdiges oder geändertes Git-Repository, ein
manipulierter Prüfer oder nachträgliche Änderungen derselben UID sind damit
nicht ausgeschlossen. Der Schutz gilt nur für kooperierende Stagingaufrufe,
nicht für fremde gleichberechtigte oder privilegierte Prozesse. Ein
unvollständiges Verzeichnis muss nach Ursachenklärung gesondert geprüft und
entfernt werden; automatisches Überschreiben ist absichtlich nicht möglich.

Das Werkzeug ändert weder installierte Units noch Clientdateien, SSH oder
Server; es startet keine Dienste und führt kein `daemon-reload` aus. Es
entscheidet nicht, ob ein Kandidat ausführbar oder mit Gegenstelle, Sicherung,
Löschjournal und Wiederherstellung kompatibel ist. Der Service enthält weiterhin
die Git-Vorlage und ist nicht als installierte Unit vorbereitet. Insbesondere
sind alte laufende Pulls, Timer, SSH-Verbindungen und Schreibprozesse damit nicht
gestoppt. Es gibt keine Aktivierung und keine Freigabe für den Zweihost-Wechsel.
