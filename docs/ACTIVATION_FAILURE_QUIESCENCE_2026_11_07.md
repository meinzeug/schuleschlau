# Fehlgeschlagene Aktivierung: kein automatischer Wiederanlauf

Bei einem Fehler im Aktivierungsteil nach einem begonnenen Stopp der bisherigen
API und des Workers versucht `activate.py`, beide Einheiten anzuhalten. Auch
wenn der erste Stopp nur teilweise funktioniert hat, startet der Fehlerpfad
keinen der beiden Dienste automatisch. Ein möglicher neuer Foto-Prozess wird
über den vorhandenen Mechanismus gestoppt; der frühere Foto-Dienst wird nicht
implizit neu gestartet. Der tatsächliche Stopp ist vom Operator zu prüfen:
`systemctl stop` wird hier nach bestem Bemühen aufgerufen, sein Ergebnis ist
kein Cgroup- oder Datenbank-Drainnachweis.

Vor dem ersten Stopp bleibt ein noch laufender Dienst beim Fehlschlag erhalten.
Soweit keine Migration und kein Start neuer Writer versucht wurde, können die
alten Unitdefinitionen und der alte Current-Verweis wiederhergestellt werden;
das startet keine Dienste. Nach einem Migrationsversuch bleiben die neuen
Definitions-/Releasezustände für eine gesonderte Prüfung stehen: ein gleicher
Alembic-Stand kann bereits veränderte Daten nicht ausschließen. Dies gilt auch
bei Fehlschlag vor dem ersten neuen Writer. Nach einem möglichen neuen Writer
bleibt ebenfalls die neue Runtime erhalten. Ein Fehler vor oder nach dem
Unitstopp muss deshalb unter Beachtung des tatsächlichen Unit-, Cgroup-,
Prozess-, Schema-, Daten- und Timerzustands behandelt werden; erst eine
explizite vollständige Prüfung kann den passenden Wiederanlauf oder einen
geprüften Rückweg bestimmen. Dies verschlechtert bei einem Aktivierungsfehler
bewusst die Verfügbarkeit gegenüber einem automatischen Neustart. Timer werden
im Fehlerpfad weder garantiert gestoppt noch auf den früheren Aktivzustand
zurückgesetzt; im Erfolgsabschnitt bereits gestartete Timer können aktiv
bleiben. Ihre Zustände müssen vor einer Wiederaufnahme separat ermittelt und
wiederhergestellt werden. Die reguläre erfolgreiche Erstinstallation und
Aktivierung verwenden unverändert ihren normalen Startpfad.

Die Regressionstests führen den tatsächlichen Exception-Handler mit lokalen
synthetischen Dateien und gefälschten systemctl-Aufrufen aus, darunter
fehlgeschlagener Reload, begonnenes Stoppen und Migrations-/Writerfälle. Sie
prüfen kein echtes systemd, kein Herunterfahren/Neustarten des Hosts und keine
DB- oder Foto-Prozessdrainage. Ein SIGKILL oder Stromverlust führt nicht durch
den Exception-Handler. Bestehende systemd-Units, Timer oder direkte Zugriffe
können Writer wieder starten; diese Änderung implementiert **keinen dauerhaften
Startzaun, Zwei-Host-Koordinator oder automatischen sicheren Wiederanlauf** und
autorisiert allein keinen produktiven Cutover.
