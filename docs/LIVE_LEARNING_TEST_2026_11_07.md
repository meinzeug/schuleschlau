# Live-Test: Lernrunden, Hinweise und Rückblick

Stand: 07.11.2026. Ausgangsversion 1.38.103; kgV-Korrektur in 1.38.104, Quellstand `3848bde`. Der Betreiber hat ausdrücklich Live-Tests im bestehenden Kinderkonto und das Speichern von Testantworten beauftragt. Die Testantworten und die erfasste Lernzeit wirken sich auf dieses Konto aus; sie sind keine Aussagen über das tatsächliche Können des Kindes. Dieser Bericht enthält keine privaten Fotos, Antworten, Kontokennungen oder Quelltexte.

## Vorgehen und Ergebnisse

- Neue Lernrunden in Mathematik und Deutsch mit regulären, kostenpflichtigen Anbieteraufrufen erzeugt und im Browser bearbeitet. In beiden abgeschlossenen Runden wurden eine korrekte Antwort nach Hinweisen und eine ohne Hinweis im Rückblick als unterstützt beziehungsweise selbstständig ausgewiesen. Die gespeicherten Unterstützungs- und Nachweiskennzeichen wurden bei diesen beiden Runden zusätzlich lesend im Backend geprüft. Die KI-Rückblicke waren bereit.
- Den Ablauf erneut sichtbar im Browser wiederholt: Die neue Deutschrunde ließ sich erstellen, beantworten und auswerten. Der Hinweis „Deine Antwort zählt mit Tipp“ war sichtbar; das Ergebnis unterschied eine unterstützte und eine selbstständige Antwort.
- Eine neu angeforderte kgV-Wiederholung schlug vor dem Anbieteraufruf mit `visual_unavailable` fehl. Der belegte Grund war, dass der geprüfte Review-Grafikplaner für diese Wiederholungsart zwei unterschiedliche Lernziele erwartete, während die angeforderte Runde nur ein kgV-Lernziel hatte. Der abgewiesene Auftrag wurde nicht an den Anbieter gesendet.
- In Version 1.38.104 unterstützt der Planer diesen belegten Fall mit zwei neuen Aufgaben für dasselbe vorhandene Ziel; Quell-, Verlaufs-, Rechen- und Grafikprüfungen bleiben aktiv. 25 gezielte automatisierte Tests einschließlich simuliertem Anbietertransport und Worker-Adapter bestanden. Eine private, rein lesende Trockenprüfung mit der betroffenen bestätigten Quelle und dem bisherigen Verlauf ergab einen gültigen Plan.
- Nach dem Deployment wurde die kgV-Wiederholung einmal regulär neu angefordert und im Browser erfolgreich geöffnet. Die erste richtige Antwort nach Hinweisen wurde als unterstützt gewertet; eine passende schrittweise Grafik ließ sich öffnen. Die zweite richtige Antwort wurde nicht als selbstständiger Nachweis gewertet, da eine frühere Erklärung die Antwort möglicherweise vorweggenommen hatte. Der fertige Rückblick zeigte entsprechend „unterstützt“ und „noch unklar“.

## Befunde für die Bedienung

1. **Hinweise und Wertung:** Die Kennzeichnung vor und nach der Antwort ist hilfreich und muss bei jeder angezeigten Hilfe erhalten bleiben. Auch eine richtige Antwort nach Hilfe ist kein selbstständiger Erstnachweis. Bereits gespeicherte modellgenerierte Hinweise können die Lösung sehr deutlich enthalten; nicht behaupten, alle KI-Hinweise seien lösungsfrei.
2. **„Noch unklar“ erklären:** Der Zustand bedeutet im beobachteten Fall nicht, dass die Antwort falsch ist. Die Oberfläche muss knapp zwischen fachlicher Richtigkeit und noch offenem Nachweis der Selbstständigkeit unterscheiden, ohne eine tatsächliche Prüfung oder Unsicherheit zu verschweigen.
3. **Rückblick:** Ein Kind braucht zuerst ein verständliches Ergebnis und eine nächste Aktion. Wiederholte Statusformulierungen und technische Begriffe im Lernweg erhöhen die Leselast; Details zu Antworten und Nachweisen gehören in aufklappbare Bereiche.
4. **Fehlgeschlagene Vorbereitung:** Eine fehlende Darstellung soll verständlich erklärt werden, ohne einen erfolgreichen KI-Aufruf oder eine automatische Wiederholung vorzutäuschen. Der konkrete Fehler ist repariert; eine allgemeine Erfolgsgarantie für alle Fächer und Quellen wurde nicht nachgewiesen.
5. **Erklärungsgrafik:** Die geprüfte kgV-Darstellung und ihre schrittweise Ansicht waren im Desktopbrowser erreichbar. Damit sind weder eine vollständige mobile/Android-Abnahme noch didaktische Wirksamkeit belegt.

## Grenzen der Prüfung

Die Live-Durchläufe betrafen wenige Aufgaben und Themen in einem Konto. Sie belegen keine allgemeine Fehlerfreiheit, keine vollständige mobile oder Android-Geräteabnahme und keine tatsächliche Lernwirksamkeit. Nachweise aus abgeschlossenen Einheiten wurden nicht überschrieben; lokale Screenshots mit Inhalten des Kontos liegen außerhalb des Repositories und gehören nicht in Git. Fehlgeschlagene und erfolgreiche Aufträge bleiben nachvollziehbar erhalten. Testantworten dürfen nicht als echte Leistungen des Kindes interpretiert werden.

## Nachbearbeitung

- Die Zusammenfassung im Rückblick behauptet bei offenen Einordnungen keine laufende Prüfung mehr. Bei möglicher früherer Lösungsansicht wird die richtige Antwort ausdrücklich als richtig bezeichnet und die offene Selbstständigkeit kindgerecht erklärt. Gespeicherte Ergebnisse werden nicht verändert.
- In Grafiken bleiben die wichtigsten Schritte und die Wiedergabe direkt sichtbar. Vergleich, Zurücksetzen und Elementliste sind unter „Mehr zur Grafik“ erreichbar. Die Änderung bestand Widgetprüfungen für schmale und breite Fenster, große Schrift und reduzierte Bewegung. Nach Deployment von Version 1.38.105 wurden der gespeicherte Rückblick und das Aufklappen von „Mehr zur Grafik“ im Desktopbrowser tatsächlich geprüft; dabei wurden keine neuen Antworten abgegeben. Eine mobile Browser- oder Android-Abnahme dieses Releases ist damit nicht belegt.
- Ein Folgeergebnis kann bereits als Zwischenwert in einer früheren Grafik erscheinen. Eine sicherere Auswahl und ein revisionsgebundener Nachweis tatsächlich angezeigter Zustände sind künftige Arbeiten; die konservative Bewertung wurde nicht umgangen.

## Kindersicht: Abschluss und Lernweg

Im vorhandenen Rückblick fiel auf: Die primäre Aufforderung zum Weiterüben wirkte verpflichtend; „Pause machen“ erklärte nicht klar, dass eine abgeschlossene Runde bereits gespeichert ist und verlassen werden kann. Die Aufgaben waren bereits einzeln ausgebreitet, obwohl ihre Details zusätzlich zugänglich waren. Im Lernweg konnte nach Abschluss eine zuletzt bearbeitete Frage noch als aktuelle Position erscheinen; nicht angesehene Erklärungen durften außerdem nicht als bearbeitet gelten.

Die überarbeitete Kinderansicht bietet nach einer abgeschlossenen Runde direkt „Zur Startseite“ und optionales Weiterüben. Aufgabendetails werden bewusst geöffnet. Der Lernweg verwendet für die aktuelle Position die tatsächlich sichtbare Phase und kennzeichnet bearbeitete sowie nicht angesehene Schritte getrennt. Der differenzierte Lernstand bleibt auf Wunsch erreichbar; Lesen oder Überspringen einer Erklärung wird nicht zum Kompetenznachweis. Der Ausgang erzeugt keine neue Aufgabe und keine KI-Anfrage. Die bisherige Elternansicht bleibt erhalten.

Isolierte Prüfungen verwenden künstliche Daten. Die Browserprüfung der deployten Fassung und ihre Grenzen werden gesondert berichtet; die Simulation einzelner Bildschirmgrößen ersetzt keine vollständige Geräteabnahme oder einen Test mit einem Kind.
