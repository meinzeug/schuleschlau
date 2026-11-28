# Automatische Lernrunden: isolierte echte KI- und Browserprobe

Am 28.11.2026 wurde der Stand `db4076e7` lokal mit einer neu angelegten,
ausschließlich künstlichen Familie, eigener SQLite-Datenbank und regulärem
Worker geprüft. Die abgeschottete Testinstanz verwendete die lesend übernommene
Modell- und Routingkonfiguration von Version 1.38.171 und einen bereits lokal
vorhandenen OpenRouter-Schlüssel. Es wurden weder Produktionskonten noch deren
Inhalte kopiert. Kosten wurden über reguläre lokale Usage-Einträge reserviert
und abgerechnet; diese lokalen Buchungen sind keine Produktivabrechnung.

## Tatsächlicher Browserablauf

In einem lokalen, nicht sichtbar geschalteten Browser-Tab mit **390 × 844**
Pixeln meldete sich ein künstliches Kind an. Über den normalen Dateiwähler
gab es ein künstliches Bild mit den Regeln und Beispielen `1/4 + 2/4 = 3/4`
und `2/7 + 3/7 = 5/7` ab. Nach der Abgabe folgten ohne weitere Nutzer-POSTs
die erste Texterkennung, eine unabhängige Gegenprüfung und die Paketgenerierung.
Danach zeigte die App den Lernweg mit einer Runde und zwei Aufgaben.

| Auftrag | Modell | Dauer laut Job | gemeldete Kosten |
| --- | --- | ---: | ---: |
| Erkennung | `openai/gpt-6-luna` | 9 s | 0,000792 USD |
| Gegenprüfung | `openai/gpt-6.1-sol` | 9 s | 0,012848 USD |
| Paket | `openai/gpt-6-luna` | 48 s | 0,004132 USD |
| Rückblick nach Antworten | `openai/gpt-6-luna` | 13 s | 0,000730 USD |

Die vier abgeschlossenen Belege zusammen betrugen 0,018502 USD; kein Betrag
war unbekannt. Die Zeit ab erstem Auftrag bis zum gespeicherten Paket betrug
66 s, ohne die vorherige Dateiauswahl. Dies sind einzelne Messungen.

Die Vorwissensfrage „8 von 9 Teilen“ wurde mit `8/9` nach einem passenden
Hinweis als richtig und unterstützt bewertet. Die zweite Frage `2/7 + 3/7`
wurde mit `5/7` richtig bewertet; weil zuvor die Erklärung geöffnet wurde,
zählte auch diese Antwort als unterstützt. Die Runde hatte freie Bruchfelder,
keine Auswahlantworten. Der Rückblick zeigte zwei unterstützte Aufgaben.

Die gespeicherte Einführung enthielt die Additionsregel, aber der ausdrücklich
geöffnete Grafikdialog zeigte nur den separat gespeicherten Viertel-Schritt.
Der ergänzte Dialog zeigt den gespeicherten Gesamttext nach dem letzten
Grafikschritt; eine vorherige erfolgreiche Erklärungsöffnung wird weiterhin
als Unterstützung erfasst. Automatische Einführungen bleiben unverändert.
Ein Vorher-/Nachher-Browservergleich nutzte für den Nachherfall eine getrennte
Kopie desselben künstlichen Ergebnisses und keinen weiteren KI-Aufruf.

Die Screenshots liegen während der lokalen Arbeit unter
`/tmp/schuleschlau-auto-browser-20261128/artifacts/auto-round-browser-*-390.jpg`.
Sie enthalten ausschließlich die künstlichen Inhalte. Der Tab war aus dem
Subagenten heraus nicht sichtbar schaltbar; es war ein echter Browserlauf,
kein vom Nutzer beobachteter Live-Browserlauf.

## Ergänzende Einzelheft-Probe und Grenzen

`backend/tests/test_auto_round_real_ai_optin.py` prüfte getrennt in einem
frischen TestClient-/SQLite-Lauf ein anderes fest erzeugtes künstliches Foto:
zwei echte OCR-Aufträge und eine automatisch vorbereitete Runde mit drei
Aufgaben waren erfolgreich. Dabei wurden keine Antworten erzeugt; gemeldet
wurden 0,062788 USD, keine unbekannten Kosten. Ohne ausdrückliches Opt-in
überspringt pytest diese kostenpflichtige Probe.
Anschließend wurde dieselbe gespeicherte Runde ohne neuen Anbieteraufruf im
390px-Browser geöffnet: Bei `2/3 · 2` standen `2/6`, `4/6` und `4/3` zur
Auswahl. Der Hinweis zum Multiplizieren des Zählers passte; `4/3` wurde
richtig und unterstützt bewertet. Auch eine zuvor geöffnete Erklärung war
als Unterstützung vermerkt. Die beiden Browser-Screenshots tragen das Präfix
`auto-round-choice-`.

Ein vorheriger Browserversuch erreichte nach zwei echten OCR-Aufträgen die
bewusst auf fünf Aufrufe gesetzte Grenze des bereits benutzten Testhaushalts.
Er stoppte ohne automatischen Retry; diese zwei Aufträge kosteten zusammen
0,014052 USD. Der oben beschriebene frische Haushalt hatte sein eigenes,
vorher festgelegtes begrenztes Budget und keine frühere Nutzung.

Der Browserfall belegt eine paketgebundene Einstiegsrunde. Weder ein weiterer
automatischer Lernwegblock noch ein vollständiger 30-Tage-Test, Firebase-
Zustellung, Produktionsbetrieb oder allgemeine OCR-/Fachqualität sind damit
abgenommen. Der Test umfasst keine echten Kinderfotos oder Kinderantworten.
