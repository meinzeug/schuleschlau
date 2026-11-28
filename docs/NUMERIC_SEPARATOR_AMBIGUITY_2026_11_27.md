# Mehrdeutige Zahlentrenner in Abschriften

**Ergänzung 28.11.2026:** Die Nachfolgeregel `literal-safety-9` erfasst auch
bestimmte isolierte Gleichungen innerhalb von Text, etwa `Beispiel: 1.000 =
1000`. Dabei wird die Bedeutung des Trennzeichens weiterhin nicht geraten;
frühere Gegenchecks bleiben an ihre ursprüngliche Regelversion gebunden. Die
nachfolgenden Angaben beschreiben den ursprünglichen Umfang von Version 8.

Bei vollständig numerischen Gleichungen konnte die bisherige Prüfung etwa
`1.000 = 1000` als falsch melden, weil sie den Punkt als Dezimalzeichen las.
Umgekehrt konnte `1,000 = 1` ohne Hinweis als belegter Stoff durchgehen. Ohne
weitere Angaben kann das Trennzeichen aber je nach Schreibweise eine andere
Bedeutung haben. Das tatsächliche Foto wurde durch diese Rechnung nicht geprüft.

Die begrenzte Regelversion `literal-safety-8` kennzeichnet solche Gleichungen
als ungeklärt und lässt ihren ursprünglichen Wortlaut unverändert. Sie werden
aus der gesicherten Lernprojektion ausgeschlossen; die Nacharbeit einer
Klassenarbeit nennt das Trennzeichen als Prüfpunkt, ohne einen Fehler oder eine
Note zu behaupten. Eine automatische Umdeutung oder Korrektur findet nicht
statt. Bei einer Gegenlesung schützt die neue Regel den ursprünglichen
unsicheren Abschnitt; frühere gespeicherte Regelversionen behalten ihre bisherige
Gegencheck-Logik. Geänderte Ausschlüsse ändern den Lernweg-Fingerabdruck;
inhaltlich unveränderte Quellen bleiben kompatibel.

Der Check betrachtet nur vollständig vom vorhandenen begrenzten Zahlenparser
akzeptierte Gleichungen mit einem ein- bis dreistelligen positiven Vorkommawert
und genau drei Ziffern nach Punkt oder Komma. `0,125` und andere nicht so
erkannte Formen werden nicht allein durch diese Regel ausgeschlossen. Sie ist
keine vollständige Lokalitäts-, Zeichenerkennungs- oder Fachprüfung; gemischter
Text, Maßeinheiten und andere Schreibweisen bleiben gesondert zu untersuchen.
Eine Bestätigung der Abschrift löst die Zahlenmehrdeutigkeit nicht automatisch.

Die Tests verwenden künstliche Materialien und prüfen Quelle, Gegenlesung,
Klassenarbeitswarnung und Fingerabdrücke. Auf isoliertem SQLite bestanden
229 Fälle; zwei PostgreSQL-spezifische Fälle wurden dort übersprungen. Auf
einem separaten temporären PostgreSQL-Cluster bestanden alle 231 Fälle. Die
vollständige OCR-Abnahme sowie Tests mit den regulären Fotoimporten bleiben
offen.
