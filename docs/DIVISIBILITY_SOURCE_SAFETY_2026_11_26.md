# Teilbarkeitsaussagen in Lernquellen

Bei der Sichtung der ursprünglichen Heftbeispiele wurde eine fehlerhafte
Teilbarkeitsaussage als mögliches OCR-Problem genannt. Der bisherige lokale
Gleichungscheck erkannte solche Aussagen nicht: Ein irrtümlich fehlendes
Nichtteilbarkeitszeichen kann die Bedeutung ins Gegenteil verkehren. Ob eine
konkrete historische Aussage tatsächlich einen KI-Auftrag beeinflusste,
wurde durch diesen Test nicht festgestellt.

Die Quellenregel `literal-safety-5` prüft vollständige einzelne Zeilen der
Form `3 teilt 25`, `3 teilt 24 nicht` sowie die mathematischen Symbole `∣`
und `∤` für begrenzte nichtnegative Ganzzahlen. Ein eindeutiger Widerspruch
schließt den betroffenen Abschnitt aus der Lernprojektion aus. Die
Originalabschrift, andere Abschnitte und frühere Antworten bleiben unverändert;
die App erhält den konkreten Ausschlussgrund. Der Schutz korrigiert kein Foto
und erkennt nicht, ob der Wortlaut von der Lehrkraft oder dem Kind stammt.

Nicht unterstützte Schreibweisen bleiben **ungeprüft**, darunter Variablen,
eingebettete Fragen, größere Zahlen, negative Zahlen, Fließtext und ein
einfacher ASCII-Strich als mögliches Tabellenzeichen. Der Wert null als
Divisor wird nicht interpretiert. Eine nicht erkannte Aussage gilt deshalb
nicht als fachlich richtig. Die neue Regel ist keine vollständige OCR- oder
Fachprüfung.

Ein Gegencheck neuer Lesungen schützt erkannte falsche Aussagen vor stillem
Ersetzen und erhält nicht eindeutig zuordenbare Lesungen samt Unsicherheit.
Bei bestehenden Belegen wird weiterhin die jeweils gespeicherte ältere
Regelversion verwendet. Lernweg-Fingerabdrücke bleiben nur kompatibel, wenn
der tatsächlich für die KI freigegebene Quelleninhalt unverändert ist.
Künstliche Tutor- und Projektionstests prüfen, dass ein ausgeschlossener
Abschnitt nicht an den Modelltransport gelangt und keine Antworten entstehen.
Die Quellen-, Gegencheck-, Tutor- und Lernwegregression bestand mit 157 Fällen
auf isoliertem SQLite (zwei PostgreSQL-spezifische Fälle übersprungen) und
159 Fällen auf isoliertem PostgreSQL. Ein produktiver Anbieteraufruf oder
Release wurde hierfür nicht ausgeführt.
