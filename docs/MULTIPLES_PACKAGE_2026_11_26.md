# Belegte Vielfachenreihen in Paketabschnitten

Ein konkreter Mathematikabschnitt ließ sich nicht vorbereiten: Er scheiterte
vor dem ersten Anbieteraufruf, weil kein verwendbares Grafikrezept zu einer
wörtlichen Vielfachenreihe gefunden wurde. Der reservierte Auftrag wurde als
`failed_not_sent` abgerechnet; eine durch den Anbieter erzeugte falsche Grafik
war hier nicht die Ursache.

Das neue versionierte Rezept erkennt ausschließlich vollständige, ausdrücklich
als Vielfache bezeichnete Reihen der Form `V_{4} = {4; 8; 12; 16…}` mit zwei
bis sechs korrekten aufeinanderfolgenden positiven Vielfachen. Es akzeptiert
auch die entsprechende begrenzte LaTeX-Schreibweise. Zahlenfehler, unklare
Ausdrücke und Teilermengen führen nicht zu einer daraus erfundenen Darstellung.
Verwendet wird nur die bestehende für die jeweilige Paketgruppe freigegebene
Quellenprojektion. Unleserliche oder ausgeschlossene Stellen bleiben draußen.

Die Einführung visualisiert die belegte Reihe in zwei örtlich steuerbaren
Phasen. Der Server plant unterschiedliche Folgefragen und berechnet ihre
Lösungen und Lösungsbilder vor dem Anbieteraufruf. Bereits sichtbare
Quellzahlen und frühere Aufgaben desselben Kindes dienen als konservativer
Ausschluss; unveröffentlichte Paketabschnitte und Änderungen zwischen Planung
und Speichern werden ebenfalls geprüft. Die private Historie wird nicht an
den Anbieter geschickt. Bestehende Aufgaben, Ergebnisse und Nachweise bleiben
unverändert. Vorgegebene feste Vorwissensaufgaben werden nicht umgeschrieben;
für solche gemischten Fälle wird dieses Rezept zunächst nicht eingesetzt.

Die Quelle, die konkrete Frage, der sichtbare Text, die Aufdeckstufe und die
Parameter des Bildes werden nach dem Transport unabhängig erneut geprüft.
Der feste Hinweis nennt kein Ergebnis, die Lösungsgrafik ist vor dem Freigeben
nicht öffentlich. Andere Reihen, Fächer und Grafikarten fallen weiterhin unter
ihre bestehenden strengen Prüfungen; der Schritt löst keine allgemeinen
Bildgenerierungs- oder OCR-Probleme.

Ein lesender Abgleich mit dem ausdrücklich freigegebenen fehlgeschlagenen
Auftrag fand eine passende bestätigte Reihe und plante drei Grafikschritte für
zwei neue Aufgaben. Dabei wurden keine Kinderdaten ausgegeben, keine Daten
geändert und kein KI-Aufruf gestartet. Ein synthetischer Anbietertest prüft
den realen Transport mit Mock; ein echter Anbieteraufruf und eine neue
produktive Runde sind damit noch nicht nachgewiesen. Flutter-Widgettests
prüfen 390 und 320 Pixel sowie vergrößerte Schrift und reduzierte Bewegung.
