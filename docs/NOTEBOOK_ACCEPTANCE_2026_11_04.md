# Digitaler Ranzen: künstliche Regression, 04.11.2026

Der Test `backend/tests/test_notebook_readonly_acceptance.py` lädt fünf
künstliche JPEGs unter den Bezeichnungen Arbeitsblatt, Hefter, Arbeitsheft,
Buchseite und Testseite hoch und ergänzt 42 künstliche Metadatensätze. Über
47 Seiten hinweg prüfen drei paginierte GETs, Suche, geschützte Fotoausgabe
(`Cache-Control: no-store`) und die Abweisung eines Geschwisterkontos. Die
Zahl der KI-Aufträge, Kostenbelege, Runden, Antworten und Aktivitäten bleibt
unverändert. Die Bilder sind einfache weiße Testbilder: Dies ist keine
inhaltliche OCR-Abnahme der fünf Materialarten.

`test_notebook_practice.py` prüft mit simuliertem Provider die ausdrücklich
ausgewählte einzelne Seite einschließlich Revision 3 sowie zwei Seiten über
verschiedene Schultage einschließlich beider exakter Revisionen. Ein
bestehender Versuch bleibt erhalten; abweichende oder veraltete Quellen
werden vor Veröffentlichung abgewiesen. Weitere künstliche Fälle in
`test_notebook_actions.py` prüfen gezählte Löschvorschau einschließlich
Antworten, erneutes Einlesen als Kopie, Idempotenz und konkurrierende Zugriffe.
Die vollständigen vier Backenddateien bestanden auf isoliertem PostgreSQL
mit 77 Fällen; auf SQLite bestanden vor Ergänzung des Einzelseitentests 74
Fälle, drei PostgreSQL-Sperrentests wurden dort übersprungen. Beide neuen
Quellenrevisionstests bestanden anschließend separat auf SQLite.

99 bestehende Flutter-Widgetfälle prüfen unter anderem Suche, Filter,
Blättern, Zoom, 320-Pixel-Ansichten, Seitenwechsel und Reaktion auf Konto-
oder Sitzungswechsel. Ein zusätzlicher künstlicher Test unterbricht den ersten
GET, lädt nach ausdrücklichem Klick erneut und prüft, dass ausschließlich GETs
stattfinden. Dieser einzelne Netztest bestand zusätzlich im Chrome-Webrunner;
das Framework beendete den Testbrowser beim Schließen per SIGKILL.
Die Tests simulieren Netzwerk und Daten; sie belegen weder echte
Fotoinhalte noch ein Offline-Heft nach App-Neustart oder einen Android-Gerätetest.
Die UX-Prüfungen ersetzen keine Beobachtung mit Kindern.
