# Messbare Prüf- und Betriebsziele

Stand 31.10.2026. Diese Zielwerte gelten zunächst für den betreuten
Übungsbetrieb mit künstlichen Prüffällen und der bestehenden Installation.
Sie sind Arbeits- und Alarmziele, keine gemessenen Leistungen und keine
allgemeine Produktionsfreigabe. Für einen größeren Pilot müssen Umfang,
Stichprobengröße und Grenzwerte vor dessen Beginn neu festgelegt werden.

| Ziel | Messung und Zeitraum | Grenzwert | Zuständig / bei Verfehlung |
| --- | --- | --- | --- |
| Kritische fachliche Fehler | Fachkundige Sichtung eines vorab festgelegten künstlichen Korpus je freigegebenem Fach vor Release; Quelle, Lösung und Erklärung gemeinsam prüfen. | Kein bekannter kritischer Fehler im geprüften Umfang. | Fachliche Abnahme; betroffene Funktion sperren oder Freigabe aufschieben, korrigieren und denselben Fall erneut prüfen. |
| Unbekannte Bewertung | Isolierte Tests mit eindeutigen, mehrdeutigen und unbelegten Antworten pro Release. | Keine unbelegte Antwort als gesicherte Beherrschung ausgeben; unbekannt ausdrücklich als unbekannt führen. | Entwicklung; Freigabe des Bewertungspfads aussetzen und Regression ergänzen. |
| Sichere Wiederherstellung | Mindestens alle 14 Tage authentifizierte Sicherung getrennt einspielen; Journal, Sitzungsentzug und Bericht prüfen. | Eine erfolgreiche, höchstens 14 Tage alte Probe ohne ungeklärte Lösch- oder Integritätsfehler. | Betrieb; Alarm bearbeiten, frische Probe durchführen, keine automatische produktive Rücksicherung. |
| Sicherungsstand | Alle fünf Minuten Alter der letzten vollständigen verschlüsselten Serversicherung prüfen. | Höchstens 30 Stunden alt. | Betrieb; Backup- und Mountfehler beheben und neue Sicherung überprüfen. |
| Unabhängige Kopie | Alle fünf Minuten neutralen Zeitstempel des letzten bestätigten Offsite-Abgleichs prüfen. | Höchstens 60 Minuten alt; Sollintervall 15 Minuten. | Betrieb; zweiten Rechner, Netzwerk und Quittung prüfen. Bei fehlendem unabhängigen Rechner gilt der Weg als nicht nachgewiesen. |
| Auftragszuverlässigkeit | Pro Release künstliche erfolgreiche und fehlgeschlagene Erkennung, Paket- und Einzelrundenaufträge einschließlich Neustart auswerten. | Kein unvollständiges Ergebnis als bereit und kein stiller oder unbegrenzter Retry; Wiederholungen idempotent. | Entwicklung/Betrieb; fehlerhafte Verarbeitung begrenzen, gespeicherte Antworten erhalten und gezielt nachtesten. |
| Wartezeit | Bei freigegebenen synthetischen Anbieterprüfungen Anfang, Ende, Modell, Ergebnis und unbekannte Kosten erfassen; mindestens fünf erfolgreiche Fälle pro repräsentativem Typ vor einer zugesicherten Zeitaussage. | Bis dahin keine feste Erfolgsdauer versprechen; während der Verarbeitung aktuellen Status und sicheren Rückweg zeigen. | Entwicklung; Ausreißer untersuchen, keine gefälschten Fortschrittswerte. |
| Benachrichtigung | Vor Freigabe eigene künstliche Konten mit In-App-Zustellung, Zielberechtigung, Duplikaten und Gerätewechsel prüfen. | Kein falscher Familienempfänger oder fremder Direktlink; native Zustellung nur nach sichtbarer Gerätebeobachtung als Erfolg zählen. | Entwicklung/Betrieb; Versand für betroffene Funktion aussetzen und Rechte erneut prüfen. |
| Gleichzeitige Nutzung | Pro Release künstliche konkurrierende Sitzungen bei Antwort, Import und Löschung auf PostgreSQL ausführen. | Keine doppelte Antwort, kein doppelter Import und keine Überschreibung durch veraltete Revision. | Entwicklung; betroffenen Schreibpfad sperren oder korrigieren und Paralleltest wiederholen. |
| Datenschutzvorfall | Kontinuierliche Betriebsmeldung ohne Inhalte; auffällige Zugriffe und bestätigte Zwischenfälle im Operatorprozess erfassen. | Kein bekannter unberechtigter Zugriff; bei Verdacht sofortige Eindämmung statt Abwarten auf eine Quote. | Betreiber/Datenschutzverantwortliche; Zugang begrenzen, Belege sichern und nach verbindlichem Meldeprozess bewerten. |

Testberichte nennen Quellcommit, Plattform, Zeit, Testumfang, bestandene,
fehlgeschlagene und übersprungene Fälle. Stichproben ohne unabhängige fachliche
Prüfung oder Tests auf künstlichen Daten belegen keine Lernwirksamkeit. Die
technische Bereitschaft ersetzt weder fachliche noch datenschutzrechtliche
Entscheidungen.
