# Schulbuddy: technische Teilprüfung

Stand 04.11.2026, Quellstand `529c8d5`. Ausschließlich künstliche Daten und
simulierte Modellantworten; keine tatsächliche Modellabnahme oder Aussage über
alle möglichen Antworten. Der Roadmap-Hauptpunkt bleibt offen.

Die Backendtests verwenden reguläre Familien-/Kinderberechtigungen, Aufträge,
Worker und gespeicherte Quellen bei künstlichem Anbietertransport. Sie decken
unter anderem bestätigte und unklare Quellen, angezeigte Grafikzustände,
Aufgabenrevisionen, Rechte- und Quellenentzug während eines Aufrufs sowie
Anrechnung tatsächlicher Hilfen ab. Ungültige Quellenzitate werden abgelehnt;
beim Lesen und Anzeigen entsteht keine Antwort oder Lernzeit. Die Widgettests
prüfen die Darstellung und Bedienung mit künstlichen Antworten. Die Ergebnisse
sind technische Regressionsbelege, keine inhaltliche oder pädagogische Garantie.

Insbesondere „nicht ungefragt Lösungen verraten“, kindgerechte Reaktionen auf
unangemessene Eingaben und Widerstand gegen manipulierte Quellinhalte werden
über den Systemtext angestrebt, sind aber ohne eigene adversariale Prüfung am
tatsächlich eingesetzten Modell nicht belegt. Ein solcher Test muss künstliche,
vom Betreiber freigegebene Inhalte verwenden, Modellbindung, Zeitpunkt,
Ergebnisse und Kosten beziehungsweise unbekannte Kosten erfassen und auch
Fehlverhalten berichten. Fachliche und kinderschutzbezogene menschliche
Sichtung bleibt davon getrennt. Auch korrekte Zitatvalidierung bestätigt nicht
pauschal die Richtigkeit des restlichen Modelltexts.

Ergebnis: 194 Backendfälle auf SQLite bestanden, zwei PostgreSQL-spezifische
Fälle dort übersprungen. 38 Flutter-Widgetfälle bestanden auf der lokalen VM;
ein Browser- oder echter Gerätetest wird daraus nicht abgeleitet. Befehl für die
Backendprüfung: `pytest -q backend/tests/test_schulbuddy*.py backend/tests/test_tutor.py`.
Die vier Flutterdateien sind `schulbuddy_integration_test.dart`,
`schulbuddy_current_context_test.dart`, `schulbuddy_saved_explanation_131_test.dart`
und `tutor_sheet_test.dart`.
