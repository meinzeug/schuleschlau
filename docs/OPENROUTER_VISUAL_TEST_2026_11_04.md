# Echte Prüfung: Bildbefunde und zwei Quellen

Am 4. November 2026 wurde Release `9d26453`, Version 1.38.80, auf
schulpilot.dorfspy.de mit einer eigenen künstlichen, regulären Testfamilie
und den fixierten Referenzbildern `01_bruch_tabelle.png` und
`03_wasser_schief.jpg` geprüft. Die Dateisummen wurden vor dem Upload
verifiziert; der befristete private Testzugang wurde über den bestehenden
Operatorbefehl eingerichtet. Keine echten Kinderinhalte oder Antworten wurden
verwendet. Ein bewusst gestarteter Vorbereitungsvorgang dauerte bis zum
Serverstatus `ready` 137,3 Sekunden. Es wurden keine Anbieterfehler künstlich
provoziert und kein fehlgeschlagener Auftrag wiederholt.

Beide Seiten wurden erkannt und gegengeprüft. Die gespeicherte Abschrift der
Mathematikseite enthielt die Referenzregeln, `2/3 Minute = 40 Sekunden` und
`1 km = 1000 m`; die Sachunterrichtsseite enthielt den Referenztext zum
Wasserkreislauf sowie `Sonne → Wolke`. Der zusätzliche vorläufige Bildbefund
beschrieb den zuvor ausgelassenen Balken korrekt: drei Felder, die beiden
linken blau, das rechte weiß; der Originalbildausschnitt war hinterlegt.
Die zwei Lesungen lieferten zwei nahezu gleichlautende Bildbefunde mit leicht
unterschiedlichen Bildbereichen. Beide wurden als **ungeprüft** angezeigt;
sie sind keine Lernquelle. Die vollständige Qualität der Fotoerkennung für
weitere Bilder ist dadurch nicht belegt.

Der Tagesplan speicherte zwei abgeschlossene Paketteile und zwei Einheiten mit
je zwei Aufgaben. Vor der Löschung wurde für jede Einheit ihre tatsächlich
vom Server ausgegebene `source_material_ids`-Liste mit den IDs der beiden
hochgeladenen Seiten verglichen: Die Mathematikeinheit referenzierte die
Mathematikseite und die Sachunterrichtseinheit die Wasserkreislaufseite.
Der Abgleich fand im eigenen künstlichen Konto statt; IDs werden hier nicht
protokolliert. Themenbezug wurde anhand der Unit-Titel geprüft, eine
umfassende pädagogische Abnahme der Aufgaben nicht durchgeführt.

Zusätzlich wurde **ein** künstlicher Bildbefund über den regulären Endpunkt
explizit bestätigt: HTTP 200, ein eigener Prüfbeleg vorhanden. Abschrift,
Materialrevision, ursprüngliche KI-Bildbefunde und serverseitig berechnete
Lernquelle waren vor und nach dem Prüfschritt identisch. Ein reiner Aufruf
oder die Bestätigung von Seiteninhalt genügt nicht als solche Bildprüfung.

Der Verbrauchsbeleg zeigte sechs erfolgreich abgeschlossene OpenRouter-Aufrufe
(vier Erkennungs-/Gegenprüfungsschritte und zwei Paketaufträge), insgesamt
0,107989 USD und keine unbekannten Kosten. Die eigene Testfamilie wurde
anschließend regulär gelöscht. Keine Produktionsgrenzen oder fremden Konten
wurden verändert.
