# Offsite-Pull und Deployment: Sperrkonzept noch nicht freigegeben

Der lokale Offsite-Client hält `.pull.lock` exklusiv über Inventar, Kopien,
Journal und Bestätigung. Ein laufender `Type=oneshot` kann `activating/start`
melden und trotzdem bei `systemctl is-active` einen Nicht-Nullcode liefern;
`Result=success` kann dabei noch vom vorigen Lauf stammen. Ein Status-Snapshot
allein ist kein Ausschluss eines bereits eingereihten oder später gestarteten
Pulls. Ein belastbarer Guard muss mindestens den tatsächlich verwendeten,
vertrauenswürdigen Sperrdatei-Inode nichtblockierend erwerben und während der
gesamten kritischen Operation halten, Zustände und ausstehende Starts auswerten
und das Verhalten bei Abbruch sowie Zeitüberschreitung festlegen.

Die isolierten `flock`-Tests in
`scripts/tests/test_offsite_deploy_feasibility.py` zeigen: Eine nur kurz
geprüfte und freigegebene Sperre verhindert keinen späteren Pull. Eine
durchgehend gehaltene Sperre blockiert einen kooperierenden Pull auf demselben
Inode. Wird der Sperrpfad ersetzt, können zwei Inodes gleichzeitig gesperrt
werden; auch eine Guardprüfung ist daher allein keine Garantie, wenn der
bestehende Pull den Pfad später ohne Bindung an denselben Inode öffnet.

Ein ausschließlich lokaler Guard genügt dem Auftrag nicht. Während eines
Deployments kann ein reguläres Serverbackup starten und die jüngste
Archividentität ändern. Es genügt nicht, dies einmal zu Beginn auszuschließen.
Umgekehrt würde eine über das gesamte Deployment gehaltene exklusive
Backup-Operationssperre die vom Deployment selbst verlangten Backups sperren.
Der Test simuliert diese Inkompatibilität zwischen exklusivem Halter und
kooperierendem Shared-Lock-Nehmer; er startet keine Dienste.

Ein späterer integrierter Vertrag muss lokale Timer-/manuelle Starts,
Inode-Wechsel, verwaiste wartende Prozesse, Server-Timer und bereits laufende
Aufträge explizit abdecken. Die nach dem vollständigen Stoppen der schreibenden
Dienste benötigte Sicherung muss tatsächlich danach gestartet und erfolgreich
abgeschlossen sein; ein älterer zusammengefasster systemd-Auftrag oder ein
alter `Result=success` genügt nicht. Ein Token-/Leasemodell muss die eigenen
kontrollierten Backupstarts erlauben, ohne konkurrierende Zugriffe freizugeben.
Versionswechsel und ein abgebrochener SSH-Kanal brauchen eine nachvollziehbare
Fortsetzungs-/Abbruchregel, bevor Sperren freigegeben werden.

Diese Datei und die Tests implementieren **keinen** produktiven Guard und
erlauben keine Bereinigung, keinen Deploymentstart und keinen automatischen
Abbruch eines laufenden Pulls. Es gab keine Änderung am Server oder an einem
bestehenden Dienst. Ein vollständiger Zweihosttest sowie Review und ein
koordinierter Rollout beider Seiten bleiben Voraussetzung.
