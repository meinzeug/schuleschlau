# Wiederholter Text und Korrekturmarkierungen

Stand: 7. November 2026. Im künstlichen Test enthielten eine oder beide
Abschriften mehrfach denselben Text. In mindestens einer Abschrift trug ein
Vorkommen eine Korrekturmarkierung. Bisher wurde das erste exakt passende
Vorkommen der zweiten Lesung ausgewählt, ohne seine Identität auf dem Foto zu
belegen. Ein weiteres Vorkommen konnte ungewarnt in die Lernquelle gelangen;
war es nur in der ersten Lesung vorhanden, konnte es auch verlorengehen.

Der Gegencheck behandelt solche Fälle konservativ: Bei mehrfachem Text und
mindestens einem geschützten Vorkommen werden alle möglichen Vorkommen mit
einem prüfpflichtigen Hinweis versehen. Eine ausschließlich in der ersten
Lesung enthaltene zusätzliche Instanz bleibt erhalten. Die vollständigen
Rohlesungen bleiben in den bestehenden Revisionsbelegen. Ein anderer,
unabhängiger Abschnitt ohne Warnung kann weiterhin als Lernquelle dienen.
Der bestehende ausdrückliche Bestätigungsablauf und die übrigen Quellfilter
bleiben maßgeblich; die Anwendung errät keine räumliche Zuordnung.

Sechs synthetische Fälle variieren, in welcher der Lesungen Text mehrfach
erscheint und welche Lesung die Korrektur enthält. Mit dem alten Code
scheiterten alle sechs; mit dem neuen Code bestanden sie. Die Tests erzeugen
keinen Anbieteraufruf und sind keine Bewertung der tatsächlichen OCR-Qualität.
Ein nicht erkannter Hinweis, andere Formulierungen, grafisch identische statt
textgleiche Stellen und echte Lehrkraftkorrekturen benötigen weiterhin die
übergreifende Bild- und Fachabnahme. Temporäre Dateien sind künstlich.

Ein weiterer künstlicher Gegenfall enthält zwei gleiche geschützte Absätze
mit derselben Aufgabennummer in der Erstlesung sowie einen anderslautenden
Absatz mit derselben Nummer in der Zweitlesung. Bei mehrdeutigen Vorkommen ist
auch eine einzelne solche Nummer kein Nachweis für dieselbe Bildstelle: Die
abweichende Zweitlesung bleibt erhalten und wird als unsicher gekennzeichnet.
Der betreffende Inhalt wird bis zur ausdrücklichen Prüfung nicht als
Lernquelle verwendet. Bei eindeutigen Fällen bleibt das bestehende Verhalten
unverändert.

Die breite lokale SQLite-Regression für Gegenprüfung, Bildbefunde und
Erkennung bestand mit 117 Fällen und zwei PostgreSQL-spezifischen Skips; zwei
zusätzliche Worker-Fälle bestanden auf SQLite und isoliertem PostgreSQL.
Diese Worker-Fälle prüfen getrennte Lesesnapshots, erhaltene Textvorkommen und
den Quellausschluss mit simuliertem Anbietertransport. Überschreitet der
Zusammenbau die bestehende begrenzte Schemakapazität, wird das Ergebnis weiter
verworfen, nicht still gekürzt oder als vollständig ausgegeben.
