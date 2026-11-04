# Getrennter Bildbefund für die Seitenerkennung

Der künstliche Livefall vom 4. November enthält einen vollständig sichtbaren
Balken mit drei Feldern, von denen zwei blau sind. Die Textabschrift ist
korrekt, der Balken wurde aber weder als Block noch als Unsicherheit erfasst;
das Ergebnis behauptete `readable`. Das Foto wird hochauflösend übergeben.
Der OCR-Auftrag fordert nur Beschriftungen und Pfeile zwischen beschrifteten
Elementen. Damit ist die aktuelle Aussage „vollständig gelesen“ für die
Bildinhalte nicht belegt.

`ExtractionOutput.content` muss exakt aus `source_blocks.text` entstehen.
Der aktuelle Blocktyp `diagram_text` ist wörtlich; eine modellgenerierte
Beschreibung an dieser Stelle würde eine Bildinterpretation als Originaltext
und potenziell als bestätigte Lernquelle ausgeben. Ein zusätzlicher Prompt
allein kann eine Vollständigkeit nicht garantieren. Der bestehende Bildcheck
ist ausdrücklich nur eine grobe Text-/Bild-Plausibilitätsprüfung.

Für einen sicheren vollständigen Weg sind mindestens erforderlich:

1. Versionsgebundenes begrenztes Feld `visual_observations` außerhalb der
   wörtlichen Blöcke mit Originalbildausschnitt, ausdrücklich vorläufiger
   Bildbeschreibung und Unsicherheit. Keine automatische mathematische
   Deutung oder Behauptung einer Bildvollständigkeit. Schema, Anbietervertrag,
   Prüfgrenzen und beide getrennten OCR-Durchgänge müssen dieselbe Struktur
   unterstützen. Unlesbare Bildbereiche ausdrücklich unsicher halten.
2. Speicherung und Revision zusammen mit dem Quellfoto, einschließlich
   unabhängiger Gegenprüfung, Quellvergleich, Versionshistorie, Wiederaufnahme
   und serverseitiger Rechteprüfung. Beim Vergleich mehrerer Lesungen keine
   Befunde still löschen oder unvereinbare Beobachtungen als sicher markieren.
3. Im mobilen Prüfablauf Foto und vorläufigen Bildbefund kenntlich getrennt
   anzeigen; Bestätigung/Korrektur muss möglich sein und Quelle sowie Revision
   erfassen. Bei alten Clients einen sicheren, sichtbaren Prüfstatus erhalten.
4. Nach Bestätigung dürfen geeignete Befunde nur über einen eigens belegten,
   getrennt gekennzeichneten Quellenvertrag in die KI-Erstellung gelangen;
   unbelegte Bilddeutungen sind keine Originalzitate oder Kompetenznachweise.
   Änderungen an der Quelle markieren abgeleitete Inhalte zur Prüfung.
5. Migration und Altversionen, Export, Löschung, authentifiziertes
   Löschjournal/Restore und Aufbewahrung für die zusätzliche private Information
   mitführen. Tests müssen fremde Familien, Operatorzugriff, Nebenläufigkeit,
   alte Clients und das Fehlen versehentlicher neuer KI-Aufrufe abdecken.
6. Realistische synthetische Bilder mit und ohne Beschriftung, verdeckte und
   widersprüchliche Bereiche sowie mehrere Fächer auf Originaltreue,
   Unsicherheit und tatsächlich angezeigte Ergebnisse prüfen. Ein einzelner
   erfolgreicher Modelllauf beweist keine OCR-Vollständigkeit.

Diese Architektur ist als Arbeitsplan dokumentiert, nicht implementiert. Die
bestehende Erkennung und ihre Grenzen bleiben unverändert.
