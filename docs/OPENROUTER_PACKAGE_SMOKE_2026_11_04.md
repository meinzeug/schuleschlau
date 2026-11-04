# Künstliche OpenRouter-Paketprobe vom 4. November 2026

Der Betreiber hat echte OpenRouter-Aufrufe auf schulpilot.dorfspy.de für die
Tests ausdrücklich beauftragt. Es wurden ausschließlich zwei bereits auf ihre
künstlichen Inhalte geprüfte und über die vorhandenen Bildsummen gebundene
Testfotos eines eigenen regulären Testkontos verwendet. Die einmalige
kontobezogene Testzugangsfreigabe erfolgte mit dem vorhandenen auditierten
Operatorbefehl `schulpilot.private_qa_access`; andere Konten und allgemeine
Anbieter- oder Datenschutzkonfigurationen wurden nicht verändert.

Die aktive Route meldete OpenRouter, Data-Collection-Deny und bezahlte Modelle.
Der bestehende Ablauf erkannte beide Seiten und prüfte sie anschließend erneut;
danach startete er die Paketverarbeitung. Vier Erkennungs-/Prüfaufrufe waren
erfolgreich, der Paketauftrag schlug fehl. Die Anbieterantwort war mit
`finish_reason=stop` abgeschlossen. Die datensparsame Validierungstelemetrie
meldet `prepared_graphics` / `prepared_graphic_question_anchor`: Die
ausgewählte Grafik passte nicht zu den ausdrücklich gebundenen
Aufgabenparametern. Die App veröffentlichte keine erfundenen Ersatzaufgaben.
Die konkrete Modellantwort wurde nicht gespeichert; die Ursache des
Modellverstoßes ist damit nicht weiter bestimmt. Der Test beweist weder einen
Ausgabelängenabbruch noch einen Fehler der Bindungsprüfung.

Fünf Aufrufe wurden verbucht: vier erfolgreich, einer fehlgeschlagen und
berechnet; zusammen 0,102894 USD, keine offenen Kosten. Es wurde keine
Providerwiederholung ausgelöst und keine Kinderantwort gespeichert. Ein echter
erfolgreicher Mehrseiten-Paketlauf und die vollständige Adapterfehlermatrix
bleiben offen. Ein Ergebnis dieses einzelnen Anbieterlaufs belegt keine
allgemeine Verfügbarkeit oder fachliche Qualität der Bilderkennung.

Ergänzend bestanden isoliert `backend/tests/test_openrouter_error*` und
`backend/tests/test_package_parts_worker.py`: 18 Tests und 18 Subtests. Sie
simulieren Fehler und ersetzen den noch fehlenden erfolgreichen Echtlauf nicht.

Die bestehende Anweisung fordert bereits ausdrücklich den exakt zur gewählten
Bruchgrafik passenden `n/d`-Anker. Zusätzlich verknüpft das gebundene
Ausgabeschema jeden Fragenzweig über ein Muster mit genau den IDs dieses
Bruches. `backend/tests/test_package_prepared_graphics.py` prüft diese Bindung,
die Ablehnung abweichender Fragen und die Erhaltung der unveränderten Aufgabe;
105 Fälle bestanden. Weil der konkrete abgelehnte Inhalt aus Datenschutzgründen
nicht vorliegt, ist nicht belegbar, welches Element das Modell verletzt hat
oder ob ein veränderter Prompt dieses Verhalten verhindert hätte. Den Guard zu
lockern wäre keine fachlich sichere Korrektur.

Das künstliche Konto wurde nach der Diagnose über seinen regulären
Löschendpunkt entfernt; temporäre private Diagnosekopien wurden gelöscht. Für
eine weitere Probe ist eine neue eigene künstliche Testfamilie mit dem
vorgesehenen befristeten Zugang und eine bewusste Auftragserstellung nötig.
Ein fehlgeschlagener Auftrag wird nicht automatisch wiederholt.

## Zweiter bewusst gestarteter Durchlauf

Eine neue künstliche reguläre Testfamilie nutzte denselben befristeten,
auditierbaren Zugang und dieselben zwei geprüften Fotos. Vier Erkennungs- und
Gegenprüfungsaufrufe sowie ein Paketaufruf wurden erfolgreich abgeschlossen;
der Server meldete `ready` mit einer Mathematikeinheit und zwei Aufgaben.
Fünf Aufrufe kosteten zusammen 0,099380 USD; alle Kosten waren bekannt.
Es wurden keine Antworten gespeichert und keine Aufträge wiederholt.

Der Lernplan verknüpfte beide Fotos mit der Gruppe, aber nur **eine** Seite
war für die generierte Einheit tatsächlich geeignet. Die zweite Seite wurde
wegen `reading_uncertain` ausgeschlossen und ein Prüfhinweis angezeigt.
Beim Vergleich mit dem künstlichen Original blieb der blasse handschriftliche
Kasten unten rechts auch für die prüfende Person nicht zuverlässig lesbar;
eine künstliche Auflösung der Unsicherheit wäre nicht belegbar. Daher ist
dies ein erfolgreicher Lauf mit einer genutzten Quelle und sicherer
Unsicherheitsbehandlung, kein Beleg für ein Zweiquellenpaket. Ein echter
Pakettest mit zwei gleichermaßen prüfbaren Seiten bleibt offen.

Die zweite Testfamilie wurde nach der Prüfung regulär gelöscht; die lokale
private Diagnosekopie wurde entfernt.
