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
