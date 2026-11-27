# Künstlicher Fotoerkennungstest mit kostenfreier Anbieterroutenprüfung

Am 27.11.2026 wurde der separate Operator-Test `scripts/live_ai_smoke.py`
für vier bereits versionierte künstliche OCR-Seiten erweitert. Eine Seite wird
nur bei passender fest im Skript hinterlegter SHA-256-Prüfsumme eingelesen;
eigene Pfade oder reale Fotos lassen sich nicht als Testbild auswählen. Die
bestehende serverseitige künstliche Standardvorlage bleibt ebenfalls verfügbar.
Das Skript verändert keine Anwendungskonfiguration und ist kein Test der
regulären Auftragsreservierung, Abrechnung oder Browser-Verarbeitung.

Vor einem Aufruf prüft das Werkzeug die öffentlichen Modellmetadaten: ein
explizit gewählter `:free`-Endpunkt muss verfügbar sein, Bildannahme und die
für strukturierte Antworten erforderlichen Parameter ausweisen und für alle
ausgewiesenen Kostenfelder außer dem Rabatt null verlangen. Die Anfrage bindet
sich an genau diesen Upstream, erlaubt keinen Fallback, verlangt
`data_collection: deny` und setzt die Preisgrenze auf null. `--strict-privacy`
verlangt zusätzlich ZDR; ohne diese Option bleibt `data_collection: deny`
verbindlich. Fehlende oder widersprüchliche Metadaten verhindern den Aufruf.

## Beobachtung

Für `particle-ai/particle-1:free` und `particle-ai/us` wies der öffentliche
Endpunktkatalog am Testzeitpunkt Bildannahme, verfügbare strukturierte Ausgabe
und Nullpreise für Ein- und Ausgabe aus. Die separat abrufbare ZDR-Endpunktliste
enthielt diesen Endpunkt nicht. Ein echter Aufruf mit der künstlichen Seite
`fraction`, ohne zusätzliche ZDR-Anforderung, wurde am 27.11.2026 vom Router
mit **HTTP 404 / keine zur Routingvorgabe passende Route** abgelehnt. Es wurde
kein Inhalt erkannt und keine OCR-Qualität belegt. Die einzelne Fehlermeldung
belegt nicht, welche der kombinierten Routingbedingungen die Ablehnung verursacht
hat. Ohne erfolgreiche Modellantwort liegt keine modellseitige Kostenangabe vor.
Keine Vorgabe wurde für einen weiteren Versuch abgeschwächt.

Die anderen zum Prüfzeitpunkt veröffentlichten freien Bildmodelle wiesen
entweder nicht alle für das Schema verlangten Parameter aus oder boten in der
öffentlichen Anbieterdarstellung keine mit dem Testziel vereinbare
Datensammlungseinstellung. Verfügbarkeiten und Metadaten können sich ändern;
eine künftige Prüfung muss sie erneut abrufen.

## Automatische Prüfung und Grenzen

Fünf künstliche Tests prüfen die vier Prüfsummen, Ablehnung veränderter Bilder,
verbindliches `deny`, ausgeschalteten Fallback, Nullpreis und die tatsächliche
Anfrage mit einem simulierten HTTP-Transport. Das ist keine echte OCR-Abnahme.
Auch der abgewiesene Anbieteraufruf, die vier bekannten Vorlagen und die
bisherige Sichtprüfung durch eine Coding-KI ersetzen weder eine unabhängige
fachliche Referenzprüfung noch den offenen regulären Fotoimport und den
vollständigen Browser-/Anbieterablauf.

Quellen: [OpenRouter Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection),
[OpenRouter Data Collection und ZDR](https://openrouter.ai/docs/guides/get-started/sovereign-ai),
[OpenRouter Providers](https://openrouter.ai/providers),
[Referenz der künstlichen Seiten](OCR_SYNTHETIC_REFERENCE_2026_11_04.md).
