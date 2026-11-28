# Mehrdeutige Zahlentrenner bei Einheiten

Eine künstliche Abschrift wie `1.000 m = 1 km` wurde bisher nicht als
rechnerischer Fehler bezeichnet, konnte aber trotz möglicher Dezimal- oder
Tausenderlesung in die gesicherte Lernprojektion gelangen. Aus der Abschrift
allein ist weder die Schreibkonvention noch die Übereinstimmung mit dem Foto
sicher ableitbar.

`literal-safety-10` erkennt begrenzte vollständige Umrechnungen derselben
unterstützten Dimension mit ein- bis dreistelligem positiven Vorkommawert und
genau drei Nachkommastellen. Der Originalblock bleibt unverändert und wird
als `ambiguous_numeric` von gesichertem Lernstoff getrennt. Die Nacharbeit
kennzeichnet die Lesart als ungeklärt, ohne eine Note oder einen Rechenfehler
zu behaupten. Alte Gegenlesungen behalten ihre aufgezeichnete Policy; ein
geänderter Quellausschluss ändert den Lernweg-Fingerabdruck.

Dies ist keine allgemeine Einheiten-, Kontext- oder Bilderkennung. Texte mit
vorgestelltem Fließtext, unbekannten Einheiten, verschiedenen Dimensionen,
Variablen oder anderen Schreibweisen werden durch diese Regel nicht beurteilt.
Auch eine eindeutige Zahl kann falsch vom Foto übernommen worden sein.

Jeweils 172 künstliche Fälle für Quellenprojektion, Gegenlesung, Lernweg,
Tutor, Mathematik und Nacharbeit bestanden auf einem temporären SQLite- und
einem separaten PostgreSQL-Testsystem. Sie enthalten keine echten Kinderdaten
und belegen keine Bilderkennung durch einen Anbieter.
