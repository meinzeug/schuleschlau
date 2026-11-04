# Künstliche OCR-Prüfseiten mit Referenz

Vier ausschließlich künstliche Seiten samt SHA-256 und vollständig sichtbarer
Textreferenz stehen unter `testdata/ocr_synthetic/manifest.json`. Sie wurden am
04.11.2026 visuell gegen die Referenz geprüft; es wurden keine Heftseiten von
Kindern verwendet. Die Referenz wurde anhand der sichtbaren Bildinhalte durch die Coding-AI
erfasst; eine unabhängige menschliche Prüfung steht aus. Sie ist kein
automatisches OCR-Ergebnis. Formeldarstellung als `2/3`
beschreibt die im Bild übereinander stehenden Ziffern mit Bruchstrich; die
Tabellenzeilen geben Zusammengehörigkeit an. Ein maskierter Text darf nicht
erraten werden. Das vierte Bild ist ein eigens generiertes synthetisches Heftfoto mit schräger Lage, Handschrift und roten Korrekturzeichen. Das durchgestrichene Ergebnis ist rechnerisch korrekt und wird daneben rot identisch wiederholt; der Grund ist unbekannt und darf nicht erfunden werden. Der Pfeil auf der dritten Seite ist Bestandteil der Zeichnung,
seine fachliche Interpretation ist kein wörtlicher Seiteninhalt.

Die Fälle kombinieren Drucktext und mehrere Absätze, kalligrafische Druckschrift
als künstliche Annäherung an Handschrift, Formel, Tabelle, Notiz, Markierung,
Balkenmodell, Zeichnung mit Beschriftungen sowie Schräglage, Zuschnitt und
JPEG-Verlust. Sie ersetzen keine echte Handschrift, Perspektiv- und
Schattenvarianten oder die Prüfung des Fotoimports auf Geräten.

`scripts/generate_ocr_regression_pages.py` erzeugt die ersten drei Bilder reproduzierbar
unter Verwendung von DejaVu Sans und URW Z003 (Systemschriften) und Pillow;
die geprüften Dateien wurden mit Pillow 12.3.0 erzeugt. Rendering kann sich
zwischen Font- und Pillow-Versionen unterscheiden. Der Integritätstest
`backend/tests/test_ocr_synthetic_reference.py` prüft die abgelegten Dateien,
nicht die Güte eines Anbieters oder eine erneute Erzeugung.

Für eine OCR-Abnahme müssen die Bilder einzeln über den regulären Import
verarbeitet werden. Anschließend jede Referenzzeile, die Zuordnung in Tabelle
und Grafik sowie die absichtlich verdeckte Stelle mit der jeweiligen Antwort
vergleichen; Auslassungen und unzutreffende Ergänzungen einzeln dokumentieren.
Ein Ankertreffer allein genügt nicht. Ein echter Anbieteraufruf wurde für diese
Seiten noch nicht durchgeführt; der übergeordnete Roadmap-Punkt bleibt offen.
