# Historischer Entwurf: Inbox-Refresh während einer Geste

Stand: 5. November 2026. Dieser Text hält den Entwurf vor Umsetzung fest.
Der nachfolgend entworfene Refresh-Schutz wurde inzwischen im isolierten
Arbeitsstand ergänzt; sein tatsächlicher Prüf- und Integrationsstatus steht in
[NOTIFICATION_SCROLL_2026_11_05.md](NOTIFICATION_SCROLL_2026_11_05.md).

## Bestehender Vertrag

Die Inbox ist ein gemeinsamer, konto-, familien- und sitzungsgebundener Cache.
Ein Refresh liest den Kopf und, falls vorhanden, bis zu zwei weitere Seiten.
Der komplette neue Stand wird erst nach erfolgreichem Einlesen übernommen.
Ein Fehler beim Rechte- oder Quellenabgleich entfernt bisherige private
Einträge. Hintergrund, veraltete Konto-Generation und parallele Lesebelege
werden im bestehenden Kontrollfluss gesondert behandelt.

Die Bildschirmposition darf dieses Verhalten nicht aushebeln: Ein erkannter
401-/403-, Quellen-, Transport- oder Parsefehler muss auch während einer Geste
unverzüglich den bisherigen Fehlerpfad erreichen. Das Gate darf nur die
Veröffentlichung **erfolgreich** gelesener Ergebnisse betreffen. Ein vom Server
noch nicht gemeldeter Rechteentzug lässt sich ohne eigenes Widerrufssignal
nicht sofort erkennen.

## Vorgesehener Veröffentlichungsvertrag

1. Die geöffnete Glocke meldet bei ihrer Inbox genau eine kurzlebige,
   eigentümergebundene Gate-Registrierung an. Menüschluss, Routen-, Konto-,
   Familien- oder Tokenwechsel, Hintergrund und Dispose entfernen sie und
   lösen eventuell Wartende auf. Abmeldung einer alten Registrierung darf
   keine später neu registrierte Instanz entfernen. Existiert bereits eine
   andere aktive Glocke, muss der Konflikt ausdrücklich behandelt werden;
   veraltete Referenzen dürfen nicht weiter im Cache verbleiben.
2. Der Refresh liest alle benötigten Seiten und prüft Generation, Kontext,
   Vordergrund und Leserevision nach jedem `await`. Fehlschläge gehen sofort
   in den bisherigen Fehlerpfad, ohne auf ein Scrollende zu warten.
3. Vor dem atomaren Übernehmen wird die **aktuelle** Registrierung geprüft,
   damit eine erst während des Netzwerkaufrufs geöffnete Glocke nicht
   übergangen wird. Ist keine Geste aktiv, werden `_pages`, Cursor,
   Lesestatus und Metadaten ohne weiteres `await` zusammen übernommen.
4. Ist eine Geste aktiv, wartet das Gate höchstens drei Sekunden und verwirft
   den gelesenen Stand anschließend. Nach einem tatsächlichen Scrollende wird
   höchstens einmal die vollständige Kette inklusive Kopf und Historienseiten
   erneut gelesen. Vor und nach jedem erneuten `await` gelten dieselben
   Kontext- und Leserevisionsprüfungen. Erst ein frisch erfolgreicher zweiter
   Durchlauf darf veröffentlicht werden. Dies verursacht höchstens einen
   zusätzlichen Satz gezielter GETs und keinen KI-Auftrag.
5. Timeout, Menüschluss, Hintergrund, Registrierungswechsel oder eine weitere
   Verzögerung verwerfen die unveröffentlichte Antwort. `_loading` wird im
   `finally` freigegeben; es gibt keine unbegrenzte automatische Retry-Schleife.
   Der bestehende periodische Timer beziehungsweise eine bewusste erneute
   Aktualisierung darf später erneut lesen. Beim Zurückkehren aus dem
   Hintergrund bleibt der vorhandene Resume-Vertrag maßgeblich.
6. Ein Gate-Abbruch ist kein HTTP- oder Berechtigungsfehler und darf daher
   nicht fälschlich den Fehlerpfad für fehlende Rechte auslösen. Umgekehrt darf
   das Gate einen tatsächlichen HTTP- oder Parsefehler nicht verschlucken.
   Eine ausdrücklich gemeldete 429 darf nicht durch einen neuen Gate-Retry
   automatisch umgangen werden.

Der bestehende Retry nach einer geänderten Leserevision darf nicht mit dem
einen durch das Gate veranlassten Neuabruf zu einer unbegrenzten Folge
zusammengesetzt werden. Die Implementierung muss ein gemeinsames, explizites
Abrufbudget und dessen Rücksetzpunkte festlegen. Beim Timeout darf keine
unbegrenzte oder unsichtbar verlorene Warteoperation übrig bleiben.

## Erforderliche Prüfungen vor einer Integration

- Während echtem aktivem Drag und Fling treffen Head und mehrseitiger Refresh
  ein: Alte Karten bleiben bis zum sicheren Zeitpunkt bedienbar, eine danach
  noch sichtbare Karte bleibt nach dem frischen Neuabruf an ihrer Position.
- Ein 401 oder 403 auf Kopf **oder** Historienseite leert den privaten Cache
  sofort trotz aktiver Geste; dasselbe gilt für einen Fehler im erneuten
  Abruf nach Scrollende. Keine Lesemarkierung entsteht durch das Warten.
- Konto-, Familien-, Token-, Routenwechsel, Menüschluss, Dispose und
  Hintergrund nach jedem möglichen `await` verhindern die Übernahme alter
  Antworten. Eine neue Registrierung darf durch das Aufräumen einer alten
  Instanz nicht aufgehoben werden.
- Eine Lesebestätigung während des Wartens bleibt nach dem Neuabruf erhalten;
  weder eine späte Seite noch ein doppelter Eintrag darf sie zurücksetzen.
- Drei-Sekunden-Timeout, unterbrochene Gesten, mehrfaches Öffnen/Schließen,
  zwei aufeinanderfolgende Gesten und 429 enden ohne festsitzendes Loading,
  unbegrenzte Neuabrufe oder Überschreiben aktueller Eingaben. Späterer
  Timer/Manuell-Refresh und Wiederaufnahme nach Hintergrund funktionieren.
- Eine gleichzeitig geöffnete Gesamtansicht und mehrere Geräte können weiter
  lesen; nur die berechtigte Sitzung erhält Daten. Ein Gate-Warten darf
  Benutzerinnen und Benutzer anderer Ansichten nicht dauerhaft blockieren.
- Sichtbare Karten, tatsächliche Lesemarkierungen und Positionsänderungen auf
  Flutter-VM und Chrome bei Smartphonebreite prüfen; Gate- und API-Tests
  zusätzlich mit künstlichen Familien und getrennten Sitzungen ausführen.
  Eine Analyse und ein unabhängiger Review gehören zum abschließenden Stand.
