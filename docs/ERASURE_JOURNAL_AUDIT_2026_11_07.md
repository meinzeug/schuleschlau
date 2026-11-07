# Löschjournal mit Outbox vergleichen

`scripts/audit_erasure_journal.py` liest mit der vorhandenen geteilten
Journalsperre die signierten Einträge und eine Datenbankmomentaufnahme. Es
prüft jede Signatur mit dem bestehenden Verfahren und vergleicht beide
Richtungen innerhalb der Aufbewahrungsfrist von 35 Tagen: ID, Art, Ziel,
Zeitstempel und bei Noten die Löschdetails. Nicht veröffentlichte Einträge,
fehlende und widersprüchliche Datensätze sowie Duplikate werden gezählt.
Gültige doppelte Datensätze können nach einem unterbrochenen Flush entstehen;
verschiedene Datensätze mit gleicher ID sind dagegen ein Fehler.

Das Werkzeug benötigt die reguläre geschützte Anwendungsumgebung und
Leserechte auf Journal, Sperrdatei und Datenbank. Der CLI-Pfad akzeptiert
ausschließlich PostgreSQL; SQLite ist nur mit explizit übergebener
In-Memory-Testengine zulässig. Es startet keinen Worker, führt keinen Flush
aus und schreibt keine Daten. Der dedizierte DB-Zugang wird vor der zeitlich
begrenzten Journalsperre geöffnet; die PostgreSQL-Transaktion ist explizit
schreibgeschützt und besitzt Statement-/Sperrtimeouts. Das Journal ist auf
64 MiB, die Abfrage auf 10.000 Einträge und ihre Einzel-Details auf 8 KiB
begrenzt; PostgreSQL überträgt Zeilen über einen Servercursor. Bei
unterbrechbaren Operationen beendet eine harte CLI-Frist nach zwölf Sekunden
den Prozess und gibt gehaltene Dateideskriptoren frei. Bei ununterbrechbarem
Kernel-I/O garantiert ein Signal keinen punktgenauen Abbruch; ein Betreiber
muss diesen Zustand gesondert untersuchen. Der Vergleich und die
Signaturprüfung laufen außerhalb der Sperre.

Die 8-KiB-Grenze ist eine konservative **Betriebsgrenze dieses Werkzeugs**,
keine fachliche Gültigkeitsgrenze: Reguläre Löschdetails für umfangreiche
Notenimporte können größer sein. Dann bricht das Audit mit Exitcode 1 ab und
liefert keinen vollständigen Vergleich. Das beweist weder einen beschädigten
Datensatz noch einen Journalfehler; die Ursache muss mit einem gesondert
geprüften Verfahren untersucht werden. Auch die 10.000-Zeilen- und
64-MiB-Grenzen können einen ansonsten gültigen Bestand zurückweisen. Aus den
Begrenzungen folgt keine feste RSS-Obergrenze: Datenbanktreiber, Python-Objekte,
Dekodierung und Signaturprüfung können zusätzlichen Speicher benötigen.

Die JSON-Ausgabe enthält nur
Summen und keine Kennungen, Inhalte oder Schlüssel. Signatur-, Datenbank- und
Lesefehler führen ohne Ausgabe des Fehlerinhalts zum Exitcode 1. Ausstehende,
fehlende, abweichende oder widersprüchlich doppelte Einträge ergeben ebenfalls
Exitcode 1. Fehlende Sperrdatei und ein nicht konfigurierter Schlüssel sind
Fehler, keine leeren Bestände. Das Programm ist eine **punktuelle Diagnose**:
Es erteilt niemals eine Restore- oder Deployfreigabe.

Am 07.11.2026 wurde diese Logik zuerst unabhängig und ausschließlich lesend
gegen die laufende Installation geprüft; es wurden nur Summen ausgegeben:
501 gültige eindeutige Signaturen und 501 passende veröffentlichte
Outbox-Einträge, keine ausstehenden Einträge, fehlenden IDs oder Feldkonflikte.
Dieser Befund dokumentiert den damaligen Augenblick, nicht spätere Zustände.
Synthetische Tests umfassen beschädigte Signaturen, fehlende und abweichende
Datensätze, Notendetails, alte Einträge, Duplikate sowie SQLite und eine
separate echte PostgreSQL-Datenbank. Dort wurden tatsächliches `read_only`,
der Abbruch einer durch andere Transaktion blockierten Tabellenabfrage und die
anschließende Freigabe der Journalsperre geprüft. Ein eigener Kindprozess
belegt, dass der harte Timeout eine gehaltene Dateisperre freigibt. Ein
falscher SQLite-Pfad wird nicht angelegt.

Ein passender Vergleich kann nicht erkennen, ob früher ein Löschvorgang ohne
Outbox-Eintrag stattfand oder eine Löschung in **beiden** Beständen verloren
ging. Die ältere produktive Laufzeit erzwingt die Journalsperre noch nicht an
jedem DB-Schreibpfad. Ohne dauerhaften Writer-Fence kann sich ein unmittelbar
danach gestarteter oder schon offener Writer ändern. Ebenso sagt eine gültige
Signatur nichts über die Aktualität einer kopierten Datei. Für die tatsächliche
Freigabe bleiben ein gesicherter hostübergreifender Schreibstopp, geprüfte
Verbindung zu Archiv und Journal, eine separate Wiederherstellung und ein
Verfahren zum Umgang mit ungeklärter älterer Historie notwendig.
