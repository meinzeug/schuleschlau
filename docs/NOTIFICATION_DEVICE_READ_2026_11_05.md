# Synthetischer Lesestatus bei Gerätewechsel

Die neue Backendprüfung verwendet eine künstliche Familie und 60 Meldungen:
Zwei voneinander getrennte Sitzungen desselben Elternkontos lesen paginierte
Nachrichten. Wird eine ältere Meldung auf der zweiten Sitzung zweimal
quittiert, zeigen beide Sitzungen denselben Lesestatus und nur ein Lesebeleg
entsteht. Eine weitere berechtigte Person derselben Familie sieht die Meldung
weiterhin ungelesen. Andere alte Meldungen bleiben ungelesen; die Prüfung
erzeugt keine KI-Aufträge. Der Fall bestand auf isoliertem SQLite und
PostgreSQL 16. Ein erster SQLite-Lauf wurde wegen Dateisystemwartezeit
abgebrochen, der erste PostgreSQL-Versuch scheiterte an der SQL-ASCII-
Initialisierung; beide zählen nicht als Erfolg. Die erfolgreichen Läufe
verwendeten getrennte temporäre Datenbanken im Arbeitsspeicher, PostgreSQL
ohne Netzlistener und mit UTF-8.

Ein mobiler Flutter-Widgettest mit 390 × 760 logischen Pixeln und zwei
simulierten Gerätesitzungen prüft außerdem die Sichtbarkeit: Beim Scrollen
werden sichtbare Meldungen quittiert, die nicht erreichte letzte Karte bleibt
ungelesen. Beim Laden des zweiten simulierten Geräts ist der zuvor gelesene
Stand vorhanden. Der HTTP-Server des Widgettests ist künstlich; er ist kein
gemeinsamer Ende-zu-Ende-Lauf mit dem realen Backend oder zwei Geräten.
Ein Chrome-Webrunner wurde wegen überlanger Wartezeit abgebrochen; er ist
nicht Teil des bestandenen Nachweises.

Die vollständige Abnahme von Glocke und Mehrgerätebetrieb bleibt offen. Die
Scrollposition im virtuellen Glockenmenü, Zugriffswechsel während des Ladens,
echte Geräte und Pushzustellung sind durch diesen Teilnachweis nicht erledigt.
