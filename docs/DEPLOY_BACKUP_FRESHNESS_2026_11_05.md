# Backup-Frische vor Releasewechsel

Ein `systemctl start` auf einen laufenden `Type=oneshot` kann sich an dessen
bereits gestarteten Job anschließen. Ein anschließendes `Result=success` belegt
für sich deshalb nicht, dass die Sicherung erst nach dem Stoppen der API und
des Workers begann. Die zweite Sicherung vor Schema-/Pointerwechsel muss auch
während des Ablaufens bereits gestarteter Arbeit nach dem Drain neu beginnen.

Die Aktivierung erfasst unmittelbar vor dem Aufruf einen monotonen
Kernel-Zeitstempel und liest nach Ende die systemd-Zeitstempel desselben
Services. Nur ein erfolgreicher, abgeschlossener, jobfreier Prozess mit gültigen
Start- und Endzeiten und Start nach diesem Wasserstand gilt als frisch. War
bereits eine ältere Ausführung erfolgreich fertig, wird höchstens ein neuer
Start verlangt. Fehler beim Start, unklare/aktive Status oder ungültige Zeiten
führen zum Abbruch ohne erneute automatische Wiederholung. Der Wasserstand für
die zweite Prüfung wird erst nach erfolgreichem `systemctl stop` von API und
Worker erfasst. Die beiden weiterhin notwendigen Backups verwenden unverändert
die bestehende Backup-Sperre; der Deploy hält sie nicht exklusiv fest.

Der Frischenachweis attestiert ausschließlich die Serviceausführung. Insbesondere
kann `backup.py` auch bei fehlendem oder nicht verfügbarem Löschjournal mit
Exitstatus 0 enden. Ein erfolgreicher Service und seine Zeitstempel beweisen
weder, welches Archiv als Wiederherstellungspunkt vollständig ist, noch eine
Restaurierbarkeit oder dauerhaftes Bestehen nach Stromausfall. Die Archivdatei
und das Backup-Verzeichnis werden im vorhandenen Veröffentlichungspfad nicht
ausdrücklich synchronisiert. Die zuverlässige revisionsgebundene Verknüpfung von genau
dieser Ausführung mit Archividentität, Journalstatus und einem echten
Wiederherstellungstest bleibt eine eigene Aufgabe.

Isolierter Regressionstest mit synthetischen Dateien und gemocktem systemd:

```sh
TMPDIR=/dev/shm .venv/bin/pytest -q backend/tests/test_deploy_activation.py
```

Der Test ändert keine echten systemd-Dienste und belegt keine Live-Sicherung.
