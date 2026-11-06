# Eltern-Lernkompass bei Sitzungswechsel und Rechteentzug

Der bisherige Lernkompass prüfte Benutzerobjekt und Familie, nicht den
Sitzungstoken oder eine neue Anmeldeabsicht. Drei künstliche Regressionstests
schlugen vor der Korrektur fehl: Ein gemeldeter Tokenwechsel ließ den alten
Bericht sichtbar, eine neue Anmeldeabsicht erlaubte einen alten KI-Auftrag und
bei Austausch des App-Zustands blieb der neue Lernkompass leer.

Die Ansicht bindet jetzt dieselbe Anfrageidentität wie der API-Client an den
Elternzugang. Gemeldete Sitzungswechsel entfernen zwischengespeicherte
Berichte, Vergleiche, Idempotenzschlüssel und Aktionen. Eine neue
Anmeldeabsicht verhindert Folgeaktionen und die Übernahme verspäteter
Antworten. Bei einem anderen `AppState` werden Listener und Identität neu
gebunden; Generationen verhindern, dass alte Anfragen den neuen Stand
überschreiben. Das gilt zusätzlich für Direktnavigation aus dem Bericht.

Meldet ein Berichtsabruf, Vergleich oder Schreibauftrag HTTP 401/403, werden
private Berichtsdaten und Vergleiche entfernt und parallele Antworten
invalidiert. Ein separater Test hält dabei eine ältere Aktualisierung zurück
und bestätigt, dass sie den Bericht nach der Ablehnung nicht wiederherstellt.
Ein bereits abgesendeter Auftrag bleibt serverseitig bestehen; die
Sitzungs-/Familienrechte dort bleiben maßgeblich.

Sieben künstliche Flutter-Widgettests bestanden auf der VM und im
Chrome-Webrunner. Sie prüfen Tokenwechsel, Anmeldeabsicht vor
und nach einer Aktion, verspätetes Lesen, Berechtigungsentzug mit parallelem
Refresh sowie den Ersatz des App-Zustands. Sie simulieren den HTTP-Transport;
sie sind kein Nachweis eines realen Serverwiderrufs oder eines unbemerkten
HttpOnly-Cookiewechsels in einem anderen Tab. Eine Anmeldeabsicht meldet selbst
keine Änderung an Listener; bereits abgeschickte Aktionen können nicht
zurückgenommen werden. Die vollständige geräteübergreifende Echtzeitabnahme
bleibt offen.

Nach der Korrektur bestanden zusätzlich 73 vorhandene Flutter-Widgetfälle
für den Lernkompass und benachbarte Elternansichten auf der VM.

Der Chrome-Webrunner meldete nach sieben bestandenen Fällen einen Fehler beim
Beenden seines Chromium-Prozesses; dies betrifft die Aufräumphase des Tests,
nicht einen Nachweis der Prozessbeendigung.
