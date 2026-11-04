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

## Dritter Lauf auf Release 1.38.79

Nach Ausrollen von Commit `384e8b2` wurden genau die fest gebundenen künstlichen
Referenzbilder 01 (Bruch und Einheiten) und 03 (Wasserkreislauf) in eine neue
künstliche reguläre Testfamilie hochgeladen. Das befristete Konto wurde über
den auditierten lokalen Befehl freigeschaltet. Ein bewusst gestarteter
Vorbereitungslauf dauerte bis `ready` 155,8 Sekunden. Vier OCR-/Gegenprüfungs-
und zwei Paketaufrufe waren erfolgreich: 6 Aufrufe, 0,113681 USD bekannte
Kosten, keine unbekannten Kosten. Für zwei Fächer entstanden zwei gespeicherte
Paketteile und Einheiten mit je zwei Aufgaben. Jede Einheit enthält eine Quellenkennung; deren eindeutige Zuordnung zur jeweiligen
Seite wurde vor der Löschung des Testkontos nicht gesondert geprüft. Keine Antwort
wurde abgegeben. Die Aufgaben
wurden anhand ihrer Fragestellungen auf Themenbezug gesichtet; damit sind ihre
vollständige fachliche Qualität oder pädagogische Wirkung nicht bewiesen.

Die OCR erfasste die sichtbaren Textregeln, `2/3 Minute = 40 Sekunden`, die
Einheitentabelle und die Wasserkreislauf-Aussagen passend zum Referenztext;
`Sonne → Wolke` wurde als beschriftete Zeichnung erfasst. Die erste Seite hat
zusätzlich einen Balken mit drei Feldern, von denen zwei blau markiert sind.
Dieser Balken fehlt sowohl in der Abschrift als auch in den `source_blocks`;
die OCR gilt deshalb für diese Referenz nicht als vollständig. Die Datenbank
kennzeichnete dennoch beide Seiten als lesbar und ohne Unsicherheit.

Die Codeanalyse zeigt: Der OCR-Systemauftrag verlangt einen Block für eine
**beschriftete** Zeichnung und deren Beschriftungen, untersagt aber gleichzeitig
Bildbeschreibungen als Ersatz für Wortlaut. Ein unbeschriftetes, farbiges
Flächenmodell hat keinen ausdrücklich verlangten eigenen Bildbefundkanal. Das
OpenRouter-Bild wird als JPEG mit `detail=high` übertragen. Diese Erkenntnis
belegt keinen technischen Bildübertragungsfehler und keinen Grund, die
bestehenden Quellenprüfungen abzuschwächen. Ein getrennter, quellgebundener
Bildbefund mit Unsicherheiten und entsprechenden Prüfungen bleibt erforderlich.
Die reguläre Testfamilie wurde nach Prüfung gelöscht; die lokale private
Diagnosekopie wurde entfernt.
