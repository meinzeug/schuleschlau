# Restore-Runtime vor dem Wortschatz-Release umstellen

Diese Anleitung beschreibt den vorgesehenen Betriebsablauf, keine bereits
erfolgte Abnahme. Sie darf erst mit einem unveränderten, erfolgreich geprüften
und nach `main` gepushten Commit ausgeführt werden, der den neuen
Wortschatz-Löschabgleich, `deploy/restore_check.py` und
`deploy/verify_restore_runtime.py` gemeinsam enthält. Ein uncommitteter
Arbeitsbaum ist keine geprüfte Releasequelle.

1. Betreiber prüft den aktiven Release, freie Kapazität, den Zustand der
   Backup-/Restore-Dienste und der Sperren sowie die Offsite-Übertragung. Den
   Restore-Timer für den Wechsel koordinieren und eine bereits laufende Probe
   auslaufen lassen; vorhandene Drop-ins, Units und Timerzustände vor
   Veränderungen sichern. Auch Backup, Aufbewahrung, Offsite und Deployment
   dürfen während des Wechsels keine konkurrierende Änderung ausführen.
2. Einen neuen, unveränderlichen Restore-Runtimeordner **außerhalb** von
   `/opt/schulpilot/releases` mit der vollständigen Commit-ID benennen. Ein
   vorhandenes gleichnamiges Verzeichnis niemals überschreiben: Inhalt,
   Quelle, Berechtigungen und Abhängigkeiten prüfen und nur bei vollständiger
   Identität wiederverwenden; andernfalls abbrechen. Backend, Deployment- und
   Restore-CLI-Dateien aus genau dem gepushten Commit (`git archive`) aufnehmen.
   Kein Arbeitsverzeichnis oder Git-Zugang auf den Server übertragen.
3. Eigenes venv herstellen und gepinnte `backend/requirements.lock` darin
   installieren. Falls stattdessen ein bestehendes venv kopiert wird, muss
   dessen Requirements-Lock mit dem des Commits bytegleich sein; danach das
   verschobene `sys.prefix`, den Python-Stand und die importierten Pakete
   kontrollieren. Keine Pip-Skripte mit alten Shebangs verwenden. Laufzeit und
   Dateien root-owned und für den App-Benutzer lesbar, aber nicht beschreibbar
   halten. Eine Quell- und Hashliste außerhalb der produktiven Daten ablegen.
4. Auf dem Server als `schulpilot` mit einer **leeren Prozessumgebung** den
   künstlichen Test ausführen. `DATA_DIR` ist ein neuer temporärer Testpfad;
   es wird kein echtes Journal oder Passwort übergeben:

   ```bash
   env -i PATH=/usr/bin:/bin \
     PYTHONPATH="$RUNTIME/backend" DATABASE_URL=sqlite:// ENVIRONMENT=test \
     MASTER_KEY=synthetic-key-not-a-production-secret DATA_DIR="$SYNTHETIC_DIR" \
     "$RUNTIME/venv/bin/python" "$RUNTIME/deploy/verify_restore_runtime.py"
   ```

   Der Test verweigert andere DB-/Umgebungswerte, kontrolliert die tatsächlich
   importierte Engine und prüft drei signierte, künstliche Löschtypen samt
   wiederholtem Abgleich. Eine zusätzliche Prüfung mit falschem `DATABASE_URL`
   muss vor jeglicher DB-Verbindung fehlschlagen. Das ist kein
   Wiederherstellungsnachweis und prüft keine Vollständigkeit echter Journale.
   Auf dem unabhängigen Offsite-Rechner den Restore-CLI-Pfad ebenfalls mit
   Backend und Abhängigkeiten aus demselben Commit bereitstellen und denselben
   synthetischen Test ausführen. Der laufende Offsite-Pull verschiebt nur
   Chiffretext und wird dadurch weder angehalten noch zu einem Restoretest.
5. Erst danach einen zuvor gesicherten, dedizierten Systemd-Drop-in verwenden,
   der `ExecStart` auf `"$RUNTIME/venv/bin/python
   $RUNTIME/deploy/restore_check.py"` setzt. Dabei den alten `ExecStart`
   zunächst mit einer leeren `ExecStart=`-Zeile zurücksetzen. Vorhandene
   fremde Drop-ins nicht überschreiben. `daemon-reload`, effektiven Dienstpfad
   und Timerstatus prüfen. Der Checker verwendet für seine Unterprozesse die
   Runtime seines eigenen Dateipfads, nicht `/opt/schulpilot/current`.
6. Echte Sicherung, erneuten Offsite-Pull und isolierte Restoreprobe getrennt
   ausführen und jeweils `Result`/Status prüfen. Bericht nur aggregiert
   ausgeben; keine Journalzeilen, Datenbankinhalte, Zugangsdaten oder
   Dateipfade aus privaten Daten protokollieren. Sicherungs- und Offsite-ACK
   belegen keine semantische Vollständigkeit des Journals. Die Probe darf nur
   eine von ihr zufällig erstellte Testdatenbank ändern und entfernen.
   Anschließend den koordinierten Timerzustand wiederherstellen.
7. Erst nach diesen Erfolgen das Anwendungsrelease aktivieren. Bevor der
   temporäre Drop-in entfernt wird, muss der produktive Release denselben
   kompatiblen Restorecode enthalten. Dienst im Ruhezustand prüfen, Drop-in
   entfernen, `daemon-reload` und effektiven Pfad kontrollieren, danach den
   isolierten Restorelauf mit dem neuen Release erneut ausführen. Bei Fehlern
   den geprüften kompatiblen Drop-in wiederherstellen und die Ursache beheben.
   Sobald neue Wortschatz-Löschbelege entstanden sein können, darf nie auf
   einen Interpreter ohne die drei neuen Typen zurückgeschaltet werden.

Ein Rollback des Anwendungsreleases ist nach neuen Löschbelegen hinsichtlich
des Restorepfads nur zulässig, solange die separate kompatible Runtime aktiv
bleibt und die übrige Schema-/Datenkompatibilität unabhängig belegt ist. Der
alte Interpreter darf auch für historische Sicherungen nicht als Ersatz
angenommen werden. Die eigene Runtime erst nach einer nachgewiesenen neuen
Probe, intakter Offsite-Kette und gesichertem Rückweg entfernen.
