# Benachrichtigungsübersicht: Position beim Nachladen

Stand 5. November 2026. In der vollständigen Benachrichtigungsübersicht werden
höchstens drei geladene Seiten gehalten. Beim Nachladen kann eine ältere Seite
mit unterschiedlich hohen Karten aus dem Fenster entfallen. Damit verschob
sich die sichtbare Karte um deren gesamte Höhe; im künstlichen 390-Pixel-Test
betrug der Sprung am bisherigen Stand 1373 logische Pixel.

Beim ausdrücklichen Nachladen hält die Übersicht jetzt die Bildschirmposition
einer sichtbaren, nach dem Laden noch vorhandenen Karte fest. Das bleibt auf
das angemeldete Konto, die Familie, den Sitzungstoken und die aktive Route
beschränkt. Eine zwischenzeitliche eigene Scrollbewegung wird nicht durch die
Positionskorrektur rückgängig gemacht. Bleibt keine sichtbare Karte erhalten
oder begrenzen die Scrollgrenzen die mögliche Position, wird keine vollständige
Positionserhaltung behauptet. Das virtuelle Glockenmenü hat einen eigenen
Scrollcontainer und ist von diesem Fix nicht erfasst.

Der synthetische Widgettest prüft unterschiedlich hohe Karten, die begrenzte
Seitenrotation, den sichtbaren Anker und eine absichtlich während einer
verzögerten Anfrage veränderte Scrollposition. Eine nach dem Laden weiterhin
nicht sichtbare Benachrichtigung erhält keine Lesemarkierung. Der Positionsfall
wurde zusätzlich im Chrome-Webrunner bei 390 × 760 Pixeln ausgeführt. Die
vollständige Geräte- und Barrierefreiheitsabnahme sowie die Positionserhaltung
im Glockenmenü bleiben offen.
