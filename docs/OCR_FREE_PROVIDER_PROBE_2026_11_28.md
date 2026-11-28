# Künstlicher OCR-Test: erneute Endpunktprüfung am 28.11.2026

Der öffentliche OpenRouter-Modellkatalog wies für
`nvidia/nemotron-3.5-super-vl:free` Bildannahme und strukturierte Ausgabe aus.
Der zugehörige Endpunkt `nvidia` meldete Status 0 und die ausgewiesenen Preise
für Eingabe und Ausgabe als null. Metadaten allein belegen weder tatsächliche
Verfügbarkeit noch Eignung für Kinderdaten.

Ein einzelner ausdrücklich veranlasster Test verwendete über
`scripts/live_ai_smoke.py` die fest prüfsummengebundene **künstliche** Seite
`fraction`. Die Anfrage blieb an diesen Endpunkt gebunden und verlangte
`data_collection: deny`, `require_parameters: true`, keinen Fallback und eine
Preisgrenze von null. Sie wurde mit **HTTP 404** abgelehnt; die gemeldete
Kurzursache lautete, dass kein Endpunkt die kombinierten Routingvorgaben
erfülle. Es liegt weder eine Bilderkennung noch eine modellseitige
Kostenangabe vor. Eine einzelne 404-Antwort beweist nicht, welche Bedingung
die Ablehnung verursacht hat.

Die [öffentliche Modellseite](https://openrouter.ai/nvidia/nemotron-3.5-super-vl%3Afree)
beschreibt für den kostenlosen NVIDIA-Endpunkt eine Protokollierung und
Verwendung zur Produktverbesserung und schließt vertrauliche und persönliche
Daten aus. Die [Anbieterliste](https://openrouter.ai/providers) führt NVIDIA
mit Speicherung und Training auf Eingaben. Das ist ein sachlicher Grund, den
Endpunkt nicht als datensammelfreie Route für Kinderdaten zu behandeln; es ist
aber kein Nachweis, dass genau diese Eigenschaft die beobachtete 404 auslöste.

Die [ZDR-Endpunktliste](https://openrouter.ai/api/v1/endpoints/zdr) enthielt
zum Prüfzeitpunkt weder die exakte kostenlose NVIDIA-Kennung noch die exakte
kostenlose `particle-ai/particle-1:free`-Kennung. Sie enthielt eine bezahlte
Kennung `particle-ai/particle-1`; deren Eigenschaften dürfen nicht automatisch
auf die freie Kennung übertragen werden. Die reguläre Free-Vorgabe verlangt
`data_collection: deny`, aber keine zusätzliche ZDR-Pflicht. Das Fehlen in der
ZDR-Liste allein beweist daher nicht, dass ein Endpunkt `deny` nicht erfüllen
kann. Andere Bedingungen wie Anbieterbindung, Schema und Kontokonfiguration
bleiben ebenfalls mögliche Ursachen für Routingfehler.

Keine Datenschutzeinstellung, Modellroute oder Kontogrenze wurde geändert.
Die vollständige OCR-Abnahme, der regulär reservierte Anbieterpfad und ein
mobiler Fotoimport mit Modellantwort bleiben offen. Zukünftige Prüfungen
müssen die aktuellen Endpunkt- und Datenschutzangaben erneut abrufen und
dürfen aus diesem Einzelversuch keine fachliche Qualität ableiten.
