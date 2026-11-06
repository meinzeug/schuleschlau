# Vorbereiteter Offsite-Pull mit beaufsichtigter Sperrübergabe

Dieser interne Clientpfad ist **keine Freigabe für eine Runtime-Umschaltung**.
Er ist lokal mit künstlichen Dateien und Prozessen geprüft; ein vollständiger
Supervisor, koordinierte Server-/Client-Sperren, rebootfeste Timermaskierung,
echte Offsite- und Restoreläufe sowie deren Abnahme fehlen. Er wurde nicht auf
dem Offsite-Rechner installiert.

Der normale Aufruf ohne zusätzliche Optionen verwendet unverändert seinen
selbst geöffneten `.pull.lock`, die bestehende Ablaufbremse und `pull()`. Ein
vertrauenswürdiger lokaler Supervisor kann den vorbereiteten internen Modus
verwenden, indem er die **von ihm selbst bereits exklusiv gesperrte** offene
Dateibeschreibung, ein pidfd für sich selbst und ein Unix-`SOCK_SEQPACKET`-Ende
mittels `pass_fds` übergibt. Die internen Argumente heißen
`--supervised-lock-fd`, `--supervised-pid-fd`, `--supervised-channel-fd` und
`--supervised-run-id` (32 hexadezimale Kleinbuchstaben). Alle vier Angaben sind
notwendig. Der Supervisor muss dieselbe offene Dateibeschreibung während des
gesamten Pulls halten und darf sie nicht entsperren. Gleichberechtigte
böswillige Hostprozesse sind nicht Teil dieses begrenzten Betriebsvertrags.

Der Worker prüft Peer-PID/-UID, pidfd, Elternerhalt, privaten Zielordner und
Lock-Inode, verweigert einen versehentlich ungesperrten FD und setzt alle drei
FDs unmittelbar auf nicht vererbbar. Vor dem Pull wird
`.offsite-handoff.pending` exklusiv geschrieben und samt Verzeichnis
synchronisiert; danach folgen `READY <run-id>`, die reguläre Ablaufbremse und
der reguläre Pull über dieselbe offene Sperre. Zwischen Remoteaufrufen sowie
vor sicherheitsrelevanten Dateiaktionen werden Supervisor und Sperre erneut
geprüft. Nach Erfolg sendet der Worker `DONE <run-id>`, **entfernt den Marker
aber nicht**. Der Watchdog meldet den Marker, sobald die Pull-Sperre frei ist.
Ein Standardpull verweigert einen vorhandenen oder als Symlink vorhandenen
Marker vor jedem Netzaufruf.

Der Marker bleibt bei Fehlern, Signal, verlorener Verbindung und auch nach
`DONE` bestehen. Ein bereits begonnener Remoteaufruf kann nach dem Verlust des
Supervisors noch laufen oder seinen ACK bereits gesetzt haben; sein Ergebnis
ist dann ungeklärt. Der Marker ist keine Vollständigkeitsgarantie. Ohne einen
geprüften Supervisor und nachvollziehbaren Recoveryablauf ist der Modus nicht
für echte Backups einsetzbar.

## Vorbereiten eines späteren Clientwechsels

1. Geprüften Client **und Watchdog** aus demselben unveränderten Quellstand mit
   Versions-/Hashbeleg bereitstellen. Vor Umstellung regulären laufenden Pull,
   seine systemd-Unit und sämtliche Nachfahren mit eindeutiger Invocation und
   Cgroup nachweisbar auslaufen lassen. Alte oder bereits gestartete Clients
   kennen den Marker nicht. Bestehenden Client und Konfiguration sichern.
2. Beide Host-Seiten einschließlich Release-Lease, Backup-/Offsite-Sperren und
   ursprünglich aktiver, aktivierter und maskierter Timerzustände koordinieren.
   Timer benötigen eine rebootfeste Sperre; bloßes `stop` reicht nicht. Keine
   pauschalen `disable`-/`enable`-Aufrufe, die zusätzliche `.wants`-Links
   verlieren können. Direkte Service-Starts bleiben gesondert zu koordinieren.
3. Supervisor, PID-/FD-Übergabe, Unit-/Cgroup-Identität und Recovery auf
   künstlichen Systemd-Units und künstlichen Sicherungen unabhängig prüfen.
   Den echten Pull erst nach sicherer Sperrübergabe starten; der Supervisor
   hält die OFD und darf keinen zweiten Self-locking-Pull darunter starten.
   Backup-/Restoreproben dürfen nicht unter einer exklusiven Operationssperre
   gestartet werden, die sie selbst benötigen.

## Recovery eines vorhandenen Markers

Keinen automatischen Retry starten und den Marker nicht allein wegen `DONE`
entfernen. Ursprüngliche Sperren/Timerzustände und die protokollierte Run-ID,
Boot-/Unit-/Invocation-Identität und Cgroup auf beiden Rechnern prüfen.
Alle begonnenen SSH-/systemd-Jobs einschließlich fremder Units müssen
nachweisbar beendet sein. Anschließend serverseitigen ACK, den lokalen
verschlüsselten Journalstand, `last-success.json` sowie eventuell vorhandene
`.erasure-ledger.pending`, `.erasure-ledger.previous` und
`.offsite-status.previous` anhand des vorhandenen Wiederherstellungsablaufs
abgleichen. Unklare Ergebnisse bleiben gesperrt; kein blindes Wiederholen oder
Löschen. Erst nach dokumentierter Klärung darf ein geprüfter Operator den
korrekten Marker entfernen und das Verzeichnis synchronisieren. Timer und
Release-Lease erst nach überprüfter Rückkehr zum jeweiligen Ursprungszustand
freigeben.

Die Tests simulieren Netzantworten, verwenden künstliche Daten und prüfen keinen
produktiven Pull, keinen echten Neustart und keinen vollständigen Zwei-Host-
Wechsel. Insbesondere ist die Herkunft des vererbten FD durch den
vertrauenswürdigen startenden Supervisor herzustellen; zwei lokale
`flock`-Versuche allein sind kein kryptographischer Herkunftsnachweis.
