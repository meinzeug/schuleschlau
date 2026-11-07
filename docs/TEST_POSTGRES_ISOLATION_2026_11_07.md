# Isolierter PostgreSQL-Testläufer

`scripts/test_postgres.py` startet PostgreSQL nur auf einem privaten temporären
Unix-Socket. Für `initdb`, `pg_ctl`, `createdb`, `psql` und pytest werden
Kindumgebungen aus einer kleinen Allowlist neu aufgebaut: geerbte libpq-,
Python-, Loader- und Servicevariablen gelangen nicht hinein. Das Home und die
Passwortdatei verweisen in den privaten Testbereich. Datenbank, Benutzer,
Socket und Port werden explizit gesetzt. Vor pytest müssen Datenbankname,
Unix-Verbindung und tatsächliches Datenverzeichnis mit dem neuen Cluster
übereinstimmen. Explizit auf SQLite angewiesene Browser-Opt-ins werden vor
Anlage des Testverzeichnisses mit Fehlermeldung abgewiesen.

Nach bestätigtem Start entfernt der Läufer das Testverzeichnis ausschließlich,
wenn `pg_ctl stop -w` erfolgreich und anschließend `pg_ctl status` mit dem
Code für einen nicht laufenden Server zurückkehrt. Ein fehlgeschlagener oder
abgebrochener Start sowie ein fehlgeschlagener, abgebrochener oder unklarer
Stopp lassen das Verzeichnis zur Untersuchung erhalten; die Fehlermeldung
nennt den Pfad. Vor manueller Bereinigung sind Prozess und Datenverzeichnis
separat zu prüfen; ein Name allein ist kein Nachweis für einen gestoppten
Server.

Die Tests führen einen echten isolierten Cluster mit absichtlich gesetzten
fremden libpq- und Loaderoptionen aus und prüfen die tatsächliche
Unix-Verbindung. Zusätzlich werden Start-/Stopp-Fehler und die Browser-Opt-ins
synthetisch geprüft. Diese Verfahren setzen eine vertrauenswürdige aufrufende
UID und einen geeigneten privaten `TMPDIR` voraus. Sie können keine Bibliothek
zurücknehmen, die bereits vor dem Start des Python-Läufers in dessen eigenen
Prozess geladen wurde; auch Root oder andere Prozesse derselben UID gelten
nicht als Angreiferabwehr. Der Läufer ist kein Werkzeug für produktive Daten.
