# Begrenzte Prüfung wörtlicher Einheitenumrechnungen

Eine erkannte Abschrift kann eine rechnerisch falsche Umrechnung enthalten.
Die Lernquellenprojektion prüft deshalb einzelne vollständig erkennbare Zeilen
mit zwei konkreten Größen derselben Dimension. Eine falsche Umrechnung wie
`⅔ Minute = 60 Sekunden` wird mit `false_unit_conversion` aus der Übergabe
als Lernstoff ausgeschlossen; die originale Abschrift bleibt unverändert.
Andere sichere Quellenabschnitte bleiben nutzbar. Die zulässige Form
`⅔ Minute = 40 Sekunden` wird nicht ausgeschlossen.

Der Check arbeitet lokal mit exakten rationalen Zahlen und einer begrenzten
Tabelle für Zeit, Länge, Masse und Volumen. Er unterstützt einfache ganze
Zahlen, kurze Dezimalzahlen und einige eindeutige Bruchschreibweisen. Er löst
keinen Anbieteraufruf aus und bearbeitet keine Aufgabe für das Kind. Die
Gegenprüfung behält bei neuen Erstlesungen (`literal-safety-6`) bei einer
abweichenden zweiten Lesung das Original und kennzeichnet die Unsicherheit.
Frühere Gegenprüfungen behalten ihre gespeicherte Regelversion. Ein geänderter
Lernquellenausschnitt kann nicht unter einem früheren Quellfingerabdruck
weiterverwendet werden.

Nicht unterstützte oder mehrdeutige Schreibweisen werden nicht interpretiert;
das schließt beispielsweise Aufgaben mit Variablen, gemischten Einheiten,
mehreren Gleichheitszeichen, unklaren Dezimal-/Tausendertrennzeichen und
Textfragen ein. Das Nichtanschlagen der Regel beweist weder eine richtige
Abschrift noch einen vollständigen oder fachlich richtigen Inhalt. Eine zwar
richtige, aber vom Foto abweichende Ersatzgleichung wird so nicht erkannt.
Die umfassende Referenzfoto- und Anbieterabnahme bleibt offen.
