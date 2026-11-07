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
