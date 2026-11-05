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
Scrollcontainer; die separate lokale Teilkorrektur ist unten beschrieben.

Ein unabhängiger Test fand eine Bewegung unmittelbar nach Abschluss der
Anfrage und vor dem Nachlayout-Callback. Positionsänderungen außerhalb der
Layoutphase sowie zwischenzeitliche Such-, Filter- und Reiteraktionen
verhindern nun eine veraltete Korrektur; reine Layoutbegrenzungen bleiben
korrigierbar. Künstliche Tests prüfen Scrollsprung, Reiterwechsel und Änderung
mit anschließendem Zurücksetzen der Suche im kritischen Zeitfenster.

Auch beim Ersetzen der neuesten Seite durch eine Aktualisierung werden die
Positionsschlüssel entfernter Karten verworfen; unveränderte Karten behalten
ihren Schlüssel. So wächst diese Hilfsstruktur nicht über den begrenzten
Nachrichtencache hinaus. Ein Test prüft Wegfall und spätere Rückkehr derselben
künstlichen Meldung sowie die Stabilität unveränderter Karten.

Der synthetische Widgettest prüft unterschiedlich hohe Karten, die begrenzte
Seitenrotation, den sichtbaren Anker und eine absichtlich während einer
verzögerten Anfrage veränderte Scrollposition. Eine nach dem Laden weiterhin
nicht sichtbare Benachrichtigung erhält keine Lesemarkierung. Der Positionsfall
wurde zusätzlich im Chrome-Webrunner bei 390 × 760 Pixeln ausgeführt. Die
vollständige Geräte- und Barrierefreiheitsabnahme sowie die Positionserhaltung
im Glockenmenü waren damals noch offen.

## Glockenmenü: lokale Teilkorrektur

Beim Nachladen veränderte sich im synthetischen 390-Pixel-Widgettest die
Position einer weiterhin sichtbaren Meldung um 170 logische Pixel. Der
separate Scrollcontainer erhält nun für geladene Karten stabile Positionsanker
und versucht, eine weiterhin vorhandene sichtbare Karte nach dem Austausch der
Cache-Seite an derselben Bildschirmposition zu halten. Dabei bleiben die
serverseitige Paginierung, der begrenzte Cache und die virtuelle Liste erhalten.
Kontowechsel, Familien-/Sitzungswechsel, Routenwechsel, Schließen des Menüs und
eigene Scrollaktionen verwerfen überholte Korrekturen.

Künstliche Widgettests prüfen die Rotation mit sechs und mit 25 hohen entfernten
Karten und bis zu 20 neuen Karten. Ein nicht sichtbarer neuer Eintrag bleibt
ungelesen. Eine Scrollaktion vor dem Korrekturcallback sowie ein Familienwechsel
bei verzögerter Antwort wurden ebenfalls geprüft. Die vorhandenen Tests zur
Inbox und Sichtbarkeitsmarkierung bestanden vor diesen letzten Ergänzungen mit
82 Fällen. Die beiden Rotationsfälle sowie Familienwechsel und eigene
Scrollaktion bestanden anschließend im Chrome-Webrunner. Ein unabhängiger
Review fand keinen konkreten Datenschutzfehler, verwies aber auf die Grenzen
der virtuellen Liste.
Ist nach dem Layout keine zuvor sichtbare Karte mehr als Renderobjekt vorhanden,
erlauben die Scrollgrenzen die Zielposition nicht oder wird beim Callback aktiv
gescrollt, garantiert der Algorithmus keine vollständige Positionserhaltung.
Insbesondere ein schneller Abschluss während eines aktiven Drags oder Flings
ist gesondert zu untersuchen. Die übergreifende Benachrichtigungs- und
Geräteabnahme bleibt offen.

## Glocke: Aktualisierung während einer aktiven Geste

Der isolierte Stand hält sowohl das Nachladen älterer Meldungen als auch die
Übernahme erfolgreich aktualisierter Listen während einer Geste bis zu drei
Sekunden zurück. Nach einer Verzögerung werden die betroffenen Seiten einmal
erneut abgerufen und Konto, Familie, Sitzung, Vordergrundrevision und
Lesemarkierungen erneut geprüft. Menüschluss, Hintergrund und Kontextwechsel
brechen das Warten ab. Das sind begrenzte GETs, keine KI-Aufträge.

HTTP-401/403-Antworten des aktuellen Kontokontexts leeren den privaten Cache
auch während der Geste; UI-Gatefehler werden nicht als Rechtefehler behandelt.
Ein 429 löst keinen automatischen Wiederholungsversuch über die
Vordergrundwiederaufnahme aus. Ein unbekannter serverseitiger Rechteentzug ist
ohne Widerrufssignal erst nach einem entsprechenden Serverfehler erkennbar.
Nach Timeout bleibt der alte Stand erhalten und die nächste bewusste oder
periodische Aktualisierung kann erneut versuchen. Zwei aufeinanderfolgende
Verzögerungen beim Nachladen können als Ladefehler erscheinen.

125 künstliche Flutter-VM-Tests bestanden, darunter UI-Drag und Fling bei
periodischem Refresh, Kontext- und Vordergrundwechsel, Leserevision, Timeout,
401/403 und 429. Die API-Mocktests belegen die Inbox-Grenze, nicht den
vollständigen globalen 401-Sitzungswiderruf. Die Tests sind keine umfassende
Geräte-, Produktions- oder Barrierefreiheitsabnahme. Ein unabhängiger Code-Review fand keinen weiteren konkreten Blocker. Zwei
gezielte Webrunner-Tests für Drag und Fling bei periodischem Refresh bestanden
in Chrome bei 390 Pixeln. Die vollständige Flutter-Analyse wurde wegen einer
langanhaltenden I/O-Blockade ohne Ergebnis abgebrochen. Die anschließende
gezielte Dart-Analyse aller geänderten Dart-Dateien ergab keine Befunde.
