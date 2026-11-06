# Kontolöschung: Sperren und Grenzen

Stand: isolierter Entwicklungskandidat, nicht produktiv freigegeben. Zwei echte
PostgreSQL-Gegenbeispiele zeigten Deadlocks: Family → Child gegen Child →
Usage/Family-Fremdschlüssel und Child → Session-Cascade gegen Session → Child
bei der Annahme eines Familienanrufs.

Der Kandidat behält die bestehende Reihenfolge Token → Family → Unit → Child
bei. Nach einer Family-Sperre werden Unit und Child auf PostgreSQL ohne Warten
gesperrt. Bei Kontolöschung werden betroffene User in stabiler Reihenfolge
voll und deren Sessions ebenfalls ohne Warten gesperrt. Ein Konflikt führt nach
Rollback zu 409. Volle User-Sperren verhindern bis zum Commit neue Sessions
über deren User-Fremdschlüssel. SQLite verwendet weiterhin seine Writer-Sperre.

Die isolierten Tests decken synthetische konkurrierende Usage-FKs, tatsächlich
angenommene Familienanrufe und das blockierte Einfügen später Sessions für
Eltern und Kinder ab. Es wurden weder produktive Daten noch echte Konten
verwendet. Ein abgewiesener Konflikt löscht keine Daten; die Aktion muss bewusst
wiederholt werden.

Dies ist kein Beweis für alle indirekten FK-Cascades und Sperrfolgen. Die lange
Worker-Retention, weitere gleichzeitige Aktionen und die vollständige
Journalsnapshot-Pfadabdeckung bleiben gesondert zu prüfen. Prototyp nicht
installieren, bevor die beteiligten Server-, Client- und Restoreversionen sowie
der übrige Sperrinventar gemeinsam geprüft sind.
