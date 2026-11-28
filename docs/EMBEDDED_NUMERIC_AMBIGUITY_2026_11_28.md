# Mehrdeutige Zahlentrenner innerhalb von Text

Ein künstlicher Quellblock wie `Beispiel: 1.000 = 1000` enthielt eine
isolierte numerische Gleichung, die bisher weder als mehrdeutig noch als
falsche Gleichung erkannt wurde. Ohne Kenntnis der Schreibkonvention kann
`1.000` für eine Dezimalzahl oder für eine Tausenderzahl stehen. Eine
automatische Entscheidung aus dem Abschriftstext wäre nicht zuverlässig.

Die begrenzte Quellenregel `literal-safety-9` schließt auch solche isolierten
Gleichungen aus der gesicherten Lernprojektion aus und kennzeichnet den Grund
als `ambiguous_numeric`. Das Original bleibt erhalten. Schulbuddy erhält den
Abschnitt nicht als belegten Stoff; die Klassenarbeitsnacharbeit nennt die
Mehrdeutigkeit als Prüfpunkt. Ein geänderter Ausschluss verändert den
Fingerabdruck des Lernwegs. Historische Gegenchecks der Version 8 behalten ihre
bisherige Prüfung und werden nicht rückwirkend umgedeutet.

Der Parser ist absichtlich begrenzt: Variablen, Einheiten, unvollständige
Ausdrücke, uneindeutige Klammerung und beliebige Mathematik werden nicht als
isolierte Zahlengleichung interpretiert. Die Regel erkennt weder alle
mehrdeutigen Schreibweisen noch falsche oder ersetzte Fotoabschriften. Sie
prüft nicht das Bild und ersetzt keine OCR-Abnahme oder fachliche Prüfung.

Auf einem separaten temporären PostgreSQL-Cluster bestanden 157 künstliche
Fälle zu Quellenprojektion, Lernweg-Fingerabdruck, Gegenprüfung, Mathematik,
Nacharbeit und Schulbuddy. Die Tests verwenden keine echten Kinderdaten und
keinen Anbieteraufruf. Ein zusätzlicher Versuch mit derselben Testumgebung im
Sandbox-Modus konnte den benötigten lokalen Unix-Socket nicht anlegen; die
erfolgreiche Wiederholung lief außerhalb dieser Einschränkung im isolierten
Testcluster.

Weitere 24 künstliche Fälle zur Mehrdeutigkeit und zu eingebetteten
Gleichungen bestanden auf isoliertem SQLite.
