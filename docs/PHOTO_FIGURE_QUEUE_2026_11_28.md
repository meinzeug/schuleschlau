# Parallele Heftabbildungen

Beim realen Browserdurchlauf auf Version 1.38.168 wurden auf einer künstlichen
Klassenarbeitsseite drei Ausschnitte gleichzeitig angezeigt. Zwei zeigten
„Die Abbildung ist gerade beschäftigt“: Der Backend-Dekodierplatz schützt
absichtlich vor paralleler speicherintensiver Bildverarbeitung und antwortet
bei Belegung mit HTTP 503.

Die Flutter-Oberfläche lädt Ausschnitte im selben App-Prozess jetzt
nacheinander. Bei einer weiterhin belegten Ressource, etwa durch ein anderes
Gerät oder einen Upload, wiederholt sie den lesenden Abruf nach je zwei
Sekunden höchstens zweimal. Andere HTTP-Fehler werden nicht automatisch
wiederholt. Bei anhaltendem Fehler bleibt die ausdrückliche Schaltfläche zum
erneuten Laden erhalten. Der serverseitige Speicher- und Zugangsschutz bleibt
unverändert; Bildbytes werden nicht global zwischengespeichert. Vor jedem
Abruf und nach jeder Wartezeit prüft die Oberfläche erneut Konto und Sitzung.
Ist die Seite durch eine andere Route verdeckt, startet sie keine wartenden
Ausschnittabrufe. Eine bereits gestartete Anfrage kann nicht garantiert
abgebrochen werden; ihre Antwort wird verworfen. Beim Zurückkehren werden
noch fehlende Ausschnitte erneut angefordert.

Isolierte Widgettests decken serielle Abrufe, kurzzeitige und dauerhafte 503,
andere Fehler, ein manuelles erneutes Laden und Kontowechsel bei wartenden
beziehungsweise vorübergehend verzögerten Abrufen ab. Zusätzlich decken sie
eine verdeckte, weiterhin gemountete Route und das Zurückkehren zu ihr ab.
Die Änderung wurde
noch nicht auf der Live-Installation getestet; der real beobachtete Fehler
und die künstlichen Regressionstests belegen keine allgemeine Lastfestigkeit.
