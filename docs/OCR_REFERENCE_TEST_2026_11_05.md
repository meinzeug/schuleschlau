# Vier künstliche Referenzseiten: regulärer OpenRouter-Ablauf

Am 05.11.2026 wurden die vier in `testdata/ocr_synthetic/manifest.json`
mit SHA-256 gebundenen künstlichen Bilder über die reguläre Material-API in
eine eigens angelegte künstliche Familie hochgeladen. Der befristete Zugang
wurde über `private_qa_access` nach Prüfung der Familie und aller vier
Bildsummen eingerichtet. Produktionsstand war `74acbae`. Die Prüfung verwendete
keine echten Kinderdaten und gab keine Aufgabenantworten ab.

Ein einmaliges ausdrückliches Abgeben startete die persistente Vorbereitung.
Vier Erkennungen und vier Gegenprüfungen wurden erfolgreich durchgeführt. Der
auf dem Server eingestellte automatische Seitenprüfmodus bestätigte die Seiten
anschließend selbst und der *gleiche* Vorbereitungsauftrag erstellte zwei
Paketpartitionen; ein separater Paketstart oder ein Wiederholungsauftrag wurde
nicht ausgelöst. Nach 219 Sekunden meldete der Server `ready`. Zehn tatsächlich
verbuchte erfolgreiche Aufrufe kosteten zusammen **0,169264 USD**; unbekannte
Kosten: null. Die Erkennungen liefen mit `openai/gpt-6-luna`, ihre Gegenchecks
und die zwei Paketpartitionen mit `openai/gpt-6.1-sol`. Die Sichtprüfung dieser
Aufzeichnungen und der Bildreferenzen erfolgte durch die Coding-AI; eine
unabhängige menschliche Prüfung bleibt offen.

| Referenz | Einzelvergleich der erkannten Abschrift und Zeichnungen |
| --- | --- |
| 01 Brüche und Einheiten | Überschrift, beide Regelsätze, `2/3 Minute = 40 Sekunden`, Tabellenüberschriften und -zeile sowie der Merksatz wurden in Reihenfolge erfasst. Zwei vorläufige Bildbefunde beschreiben drei gleich breite Abschnitte, links zwei blau und rechts einen weiß. |
| 02 Satzglieder, Abdeckung | Überschrift, beide Beispielsätze, Randfrage, Merksatz und `Unklar:` wurden in Reihenfolge erfasst. Zwei Hinweise kennzeichnen den verdeckten Wortlaut als nicht lesbar; ein Text hinter der Abdeckung wurde nicht ergänzt. Die Seite blieb trotz automatischer Bestätigung als teilweise lesbar markiert. |
| 03 Wasserkreislauf | Überschrift und alle drei erklärenden Sätze stimmen in Reihenfolge. Die Beschriftungen `Sonne` und `Wolke` sind als `Sonne→Wolke` zusammengefasst; vorläufige Bildbefunde beschreiben die gelbe und graue Form sowie den blauen Pfeil. |
| 04 Bruchheft | Überschriften und alle sechs sichtbaren Rechenzeilen einschließlich der unvollständigen letzten Aufgabe wurden in Reihenfolge erfasst. Vier rote Häkchen und die durchgestrichene sowie daneben rot wiederholte `11/15` sind als Markierungen aufgenommen. Ein Grund für die widersprüchlich wirkende Wiederholung wurde nicht behauptet. Die unabhängig erkannten Bildbereiche der roten Durchstreichung und der roten Wiederholung unterscheiden sich allerdings deutlich und überlappen jeweils nicht; die automatische Prüfung meldete hierzu bislang keine eigene Unsicherheit. |

Der letzte Befund betrifft die Lage der Markierung, nicht die rein rechnerische
Gleichheit der beiden Aufschriften. Eine plausible Textabschrift beweist keine
richtigen Bildkoordinaten. Die neue Prüfung kennzeichnet eindeutig zuordenbare,
nicht überlappende Korrektur-, Einfügungs- und Durchstreichungsbereiche als
unsicher, erhält beide Befunde und den unveränderten Text und macht die Seite
teilweise lesbar. Für mehrfach vorkommende Markierungen mit unterschiedlichen Bildbereichen
bleibt die Zuordnung unsicher; es wird keine Zuordnung geraten. Die rohen Anbieterantworten verbleiben im regulären
Quellenverlauf; markierte Bereiche bleiben nach dem vorhandenen Quellenvertrag
von bewerteten Aufgaben ausgeschlossen. Die Korrektur wurde an künstlichen
Regressionstests geprüft; sie wurde während des beschriebenen produktiven Laufs
noch nicht eingesetzt.

Der Lauf prüft nur diese vier Seiten. Es fehlen unter anderem unabhängige
fachkundige Referenzprüfung, weitere Fächer, echte Handschrift, viele Aufnahmen
mit unterschiedlichen Licht- und Perspektivverhältnissen sowie die reguläre
Dateiwahl und der Zuschnitt für diesen Vierseitenlauf. Ein Emulatorlauf mit
anderen künstlichen Seiten ist separat dokumentiert. Deshalb bleibt die
umfassende OCR-Abnahme in der Roadmap offen.

## Erneuter Anbieterfall nach Ausrollen der Lageprüfung

Auf dem produktiven Release `a3feaa8` wurde der reguläre Ablauf am 05.11.2026
mit einer neu angelegten künstlichen Familie und denselben vier fest
freigegebenen Fotos erneut **einmal bewusst** gestartet. Der automatische
Prüfmodus führte nach vier Erkennungen und vier Gegenprüfungen auch zwei
Paketpartitionen aus. Alle zehn Aufrufe waren erfolgreich und kosteten
zusammen 0,163519 USD; unbekannte Kosten: null. Nach 250,6 Sekunden meldete
der Server `ready`. Es wurden keine Antworten gespeichert und keine Aufträge
wiederholt.

Bei Referenzfoto 04 überlappten sich diesmal die Lageangaben aus den beiden
Lesungen für die rote Durchstreichung und die rote Wiederholung jeweils. Beide
Markierungen und beide Lageangaben blieben in den Daten erhalten; die neue
Konfliktwarnung erschien nicht. Das entspricht in diesem Fall der Eingabe,
belegt aber **nicht**, dass ein tatsächlicher Konflikt bei diesem Lauf live
angezeigt wurde. Die zuvor beobachtete Abweichung und ihr isolierter
Regressionstest bleiben oben beschrieben. Die letzte sichtbare Aufgabe erhielt
getrennt den Hinweis, dass nach dem Gleichheitszeichen keine Fortsetzung zu
sehen sei. Die künstliche Familie wurde über den regulären Endpunkt gelöscht;
Zugangsdaten und temporäre Diagnosekopien wurden entfernt.

## Nachprüfung des Gegencheck-Übergangs

Ein späterer künstlicher Worker-Regressionstest bildete den ursprünglich
beobachteten Fall nicht nur im Zusammenführen, sondern bis zur anschließenden
Produktionsvalidierung nach: Bei unterschiedlichen Korrekturbereichen wurde
zwar ein lokaler Hinweis hinzugefügt, aber kein Seitenhinweis. Die Validierung
lehnte daraufhin die als teilweise lesbar markierte Gegenprüfung ab. Der
frühere isolierte Mergetest allein hatte diesen Fehler nicht erfasst.

Lokale Hinweise werden nun in die begrenzte Seitenhinweisliste übernommen,
ohne ihren wortgleichen Blockbezug zu verlieren. Sind bereits acht Hinweise
im Block gespeichert, wird ein weiterer Konflikt mit einem eindeutig
seitenweiten Sammelhinweis angezeigt und die ganze Seite vorsorglich
ausgeschlossen; ältere Details bleiben in den Rohsnapshots erhalten. Leere
Seitenhinweise bleiben konservativ seitenweit wirksam. Ein erhaltener lokaler
Erstlesehinweis setzt die Lesbarkeit auch dann auf teilweise, wenn der zweite
Durchgang sie als vollständig einstufte. Der isolierte Gegencheck mit
künstlichen Transportantworten prüft Jobstatus, beide unveränderten
Lesesnapshots, die ausgeschlossene betroffene Stelle und einen weiterhin
nutzbaren unbeteiligten Absatz. Dies ist keine weitere Live-Anbieterprüfung
und kein Nachweis für allgemeine OCR-Vollständigkeit.
