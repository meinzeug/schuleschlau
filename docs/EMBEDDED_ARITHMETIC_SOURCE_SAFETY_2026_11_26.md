# Eingebettete Rechnungen in Heftquellen

Beim mobilen Alltagstest fiel auf, dass eine Heftabschrift mehrere Aufgaben und
Rechnungen in einem Absatz enthielt. Der bisherige rationale Gleichungscheck
prüfte nur vollständig numerische Zeilen. Eine falsche Rechnung hinter einem
Arbeitsauftrag oder neben einer anderen Aufgabe konnte dadurch dieser einen
Schutzprüfung entgehen. Das ist kein Nachweis, dass eine konkrete Rechnung in
einer tatsächlichen Lernrunde verwendet wurde: Andere Quellenwarnungen und
Schülerarbeitsmarkierungen können denselben Absatz bereits ausschließen.

Die Quellenregel `literal-safety-4` erkennt zusätzlich begrenzte eigenständige
Zahlengleichungen in Textzeilen und vergleicht sie exakt rational. Ein erkannter
Widerspruch schließt den ganzen zugehörigen Quellenabschnitt aus dem Lernstoff
aus. Das Original, andere nutzbare Abschnitte und gespeicherte Antworten
werden nicht verändert. Diese Regel kann eine Rechnung weder automatisch
korrigieren noch ihre Herkunft oder den didaktischen Zusammenhang beurteilen.

Der zusätzliche Erkenner interpretiert insbesondere keine Variablen,
Einheiten, gemischten Zahlen, mehrdeutigen Tausender-/Dezimaltrennzeichen oder
vermutete Klammern aus abgeflachten Bruchdarstellungen. Zahl und Länge der
Terme sind beschränkt. Nicht erkannte Notation wird nicht als richtig erklärt;
der vorhandene Quellenstatus bleibt `not_assessed`. Eine unabhängige fachliche
Prüfung und die umfassende OCR-Abnahme bleiben erforderlich.

Beim automatischen Gegencheck wird die im ersten Lesebeleg gespeicherte Regel
für die Wiederholung der ursprünglichen Zusammenführung verwendet. Ein neuer
`literal-safety-4`-Beleg schützt auch solche erkannten eingebetteten Fehler vor
einem stillen Ersetzen durch den zweiten Leselauf; ältere Belege werden mit
ihrer früheren Regel rekonstruiert. Lernweg-Fingerabdrücke älterer Regeln
werden nur dann als kompatibel akzeptiert, wenn der aktuell freigegebene Inhalt
und sämtliche Ausschlüsse tatsächlich übereinstimmen.

Prüfungen verwenden ausschließlich künstliche Daten. Sie umfassen mehrere
Rechnungen in einer Zeile, unveränderte Quellen, getrennte Regelversionen,
Abweichungen der Lernwegquelle, Einheiten, Variablen und mehrdeutige Notation.
Ein simulierter Tutorauftrag überprüft, dass ein ausgeschlossener Text nicht
im Anbieterpayload erscheint und kein Antwortnachweis entsteht. Die Tests
belegen keine tatsächliche Bilderkennung oder Prüfung sämtlicher Fächer.

Am 26.11.2026 bestanden 147 Fälle auf isoliertem SQLite (zwei übersprungen)
und dieselben 149 Fälle auf einem getrennt erzeugten PostgreSQL-16-Cluster.
Enthalten sind Quellenhistorie, automatischer Gegencheck, Lernweg-Fingerabdruck
und künstlich simulierter Tutortransport. Die komplette Python-Lintprüfung für
Backend, Deploy und Skripte bestand. In der produktiven Installation ist diese
Regel damit noch nicht ausgerollt oder live geprüft.
