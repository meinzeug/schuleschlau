# Lesende Vorbereitung des Restore-Runtime-Wechsels

`scripts/restore_cutover_preflight.py` prüft ausschließlich den bekannten
Ausgangsstand auf dem Zielserver: die inaktiven systemd-Oneshots für Backup und
Restore, deren hinterlegte Kommandos und die Existenz zweier Dateien in der
vorbereiteten Runtime `45b66d20dc3b4c9b504eb8bb38f2b54dfc2fb86f`. Das Skript
führt `systemctl show` aus und liest Dateimetadaten. Es verändert keine Unit,
keinen Timer, keine Sperre und keine Sicherung. Ein Ergebnis ist nur eine
Momentaufnahme; `activation_authorized` ist immer `false`.

Dieser Vorabcheck ist **keine Freigabe für den Wechsel**. Er prüft weder
Integrität der vorbereiteten Runtime noch Eigentum und Symlinkziele, die
Laufzeitversion, laufende oder später gestartete Nebenprozesse, Lockbesitz,
Timerzustände, Offsite-Client, Backupinhalte oder Wiederherstellung. Zwei
unabhängige `systemctl show`-Aufrufe sind nicht atomar. Auch ein erfolgreiches
Resultat erlaubt daher keinen Start und keine Umschaltung.

Für einen künftigen betrieblichen Supervisor müssen die vorgegebenen
Release-/Backupsperren und rebootfesten Timerzäune mit dauerhaftem
Recoveryzustand auf beiden Rechnern nachgewiesen werden. Vor jedem Start ist
die berechtigte bestehende Unit eindeutig an den eigenen Auftrag zu binden;
bei fehlendem oder unklarem Ergebnis bleibt die Anlage im Recoveryzustand und
es gibt keinen automatischen Neustart. Eine exklusive Backup-Operationssperre
wird nicht während Backup- oder Restore-Units gehalten, die sie selbst nehmen.
Ein vollständiger Abschlussbeleg entsteht erst nach gesichertem Abschluss aller
Proben und wiederhergestellten Timern; danach dürfen keine kritischen Aktionen
mehr folgen, außer der abschließenden Lease-Freigabe. Die tatsächliche
Zwei-Host-Koordination und diese Nachweise sind noch nicht implementiert.

Die künstlichen SSH-Systemd-Laborversuche vom 6. November verwendeten eigene
Sleep-/Fehler-Units und einen separaten Supervisor mit `RemainAfterExit` und
synchronem `systemctl start --wait`. Sie belegen unter anderem eine fortgesetzte
Supervisor-Invocation nach SSH-Abbruch, aber keinen echten Backup-, Restore-,
Reboot- oder Stromausfalltest. Ein zu kurzer Oneshot kann seine Invocation-ID
vor der nachträglichen Beobachtung verlieren; ein erfolgreicher Shell-Exit
allein beweist deshalb nicht die eindeutige Bindung an einen eigenen Auftrag.
Bei einem Supervisorkill kann die gesonderte Zielunit weiterlaufen.
