# Kopfbereich bei begrenzter Arbeitsfläche

Ein künstlicher Eltern-Notentest im Chrome-Runner zeigte einen um zwei Pixel
überlaufenden Desktop-Kopf: Das Browsermaß wies auf eine breite Arbeitsfläche,
die tatsächlich verfügbare Fläche war jedoch durch die Testumgebung deutlich
schmaler. Der Kopf prüft nun seine eigenen Constraints. Reicht eine Zeile nicht,
ordnet er Titel und unverkleinerte Bedienelemente in mehreren Zeilen an.

Die reguläre Flutter-Testdatei zur Arbeitsflächennavigation bestand mit 33
Fällen. Zwei zusätzliche Fälle schränken eine ansonsten breite Browseransicht
auf 320 beziehungsweise 390 Pixel ein. Sie prüfen unter anderem die
Erreichbarkeit, die Mindestgröße von 48 × 48 Pixeln für Bereichssuche und
Tastaturhilfe sowie deren vollständige Lage im Kopfbereich. Beide Fälle
bestanden auch im Chrome-Runner. Der ursprüngliche Diagnosetest bestand nach
der Korrektur. Ein zwischenzeitlich paralleler Testbuild verursachte
inkompatible Test-Shader; nach Entfernen der ausschließlich in der separaten
Arbeitskopie erzeugten Testdateien bestanden die Wiederholungen seriell.

Dies ist ein synthetischer Constraint-Test, keine Aufnahme eines echten
Smartphones und keine allgemeine Tastatur-, Kontrast- oder WCAG-Abnahme. Die
Kinder-, Eltern- und Adminarbeitsfläche verwenden denselben Kopf; die beiden
neuen Fälle verwenden ein künstliches Elternkonto.
