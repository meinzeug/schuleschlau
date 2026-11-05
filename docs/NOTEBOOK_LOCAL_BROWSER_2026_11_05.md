# Hefte: lokaler Browser- und API-Lauf

Am 05.11.2026 wurde Quellstand `bb2bf24` als Flutter-Webrelease gebaut und
mit dem zugehörigen FastAPI-Prozess ausschließlich auf `127.0.0.1` getestet.
Der Server verwendete eine neue isolierte SQLite-Datenbank und ein eigenes
Uploadverzeichnis. Der Lauf umfasste eine künstliche Familie mit Elternzugang,
zwei eigenen Kinderzugängen und einen dritten Zugang einer anderen Familie.
Die Zugangsdaten waren zufällig und nur im privaten temporären Testverzeichnis
abgelegt. Es wurden keine Produktionskonten oder -daten verwendet. Der lokale
Server wurde beendet; beide temporären Testverzeichnisse einschließlich
Datenbanken, Uploads, Sitzungen und Zugangsdaten wurden anschließend gelöscht.

Für jedes der beiden Kinder wurden die fünf Dateien aus
`testdata/notebook_synthetic/` tatsächlich über die reguläre Upload-API
importiert. Die lokal künstlich erzeugten Layoutseiten sind keine realistischen
Handyfotos. Eine OCR wurde nicht ausgeführt: Der Test setzte den Status der
Upload-Datensätze lokal für die Vorbereitung auf „review“, gab ausdrücklich
künstliche Beispieltranskripte vor und bestätigte sie über die reguläre API.
Die Testfamilie verwendete die reguläre Kontoroute und war technisch nicht als
Demo-Familie gekennzeichnet; ausschließlich ihre Daten waren künstlich.

Im echten Chrome-Browser wurden die Elternansicht bei 390 Pixeln sowie die
Kinderansichten bei 390 und 1280 Pixeln geöffnet. Beide Kinder blätterten
durch fünf Seiten; für das zweite Kind sind alle fünf erfolgreichen,
authentifizierten Bildantworten beobachtet. Das fremde Kind und das jeweils
andere Kind erhielten keinen Zugriff auf das fremde Bild. Ein Kind startete
bewusst eine einzelne Seite und das andere zwei ausgewählte Seiten. In beiden
Fällen öffnete sich die tatsächliche Vorbereitungsseite. Eine Prüfung der
isolierten Datenbank fand genau zwei wartende Aufträge: deren Quellen gehören
zum jeweiligen Kind und die gespeicherten Revisionen stimmen mit der
bestätigten Auswahl überein. Es existieren zwei noch nicht abgerechnete
Reservierungen, keine Aufgabenversuche und keine Auftragsergebnisse.

Es lief ausdrücklich kein Worker; externe Modellanbieter wurden nicht
aufgerufen. Die Warteschlangenansicht ist daher kein Nachweis einer erzeugten
oder abgeschlossenen KI-Runde. Aus diesem Lauf folgen keine Aussagen zur
Qualität einer Bilderkennung, zur Fachlichkeit erzeugter Übungen oder zum
getrennten Klassenarbeiten-Workflow. Die Testseite mit der Aufschrift
„Klassenarbeit“ wurde hier bewusst als Heftquelle hochgeladen. Die Tests wurden
mit einem einmaligen lokalen Treiber ausgeführt; sie ersetzen den separat
versionierten, mit Mocks reproduzierbaren UI-Test nicht.

Bildbelege aus ausschließlich künstlichen Daten:

- [Elternansicht bei 390 Pixeln](images/notebook-local-parent-390-20261105.png)
- [Kind: Blättern bei 390 Pixeln](images/notebook-local-child-390-20261105.png)
- [Kind: Auswahl zweier Seiten bei 1280 Pixeln](images/notebook-local-sources-1280-20261105.png)

Der umfassende Hefte-Roadmap-Punkt bleibt offen, insbesondere für realistische
Fotoqualität, die echte Erkennung und KI-Erstellung, weitere Rollen- und
Materialwege sowie die vollständige menschliche Bedienungsabnahme.
