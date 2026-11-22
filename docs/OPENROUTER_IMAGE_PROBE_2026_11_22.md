# Isolierte OpenRouter-Bildprobe und Grafikvorbereitung vom 22.11.2026

Die Probe verwendete ausschließlich einen festen, allgemeinen englischen Prompt
für eine gezeichnete Biene auf einer Blume. Keine Heftseiten, Konten oder
Kinderinformationen wurden übertragen. Sie lief außerhalb der App in einer
isolierten Operatorprobe; die Kosten sind deshalb keine Buchung in einem
Produktions-Kinderkonto.

* Der dokumentierte Image-API-Endpunkt akzeptiert `provider.only`,
  `allow_fallbacks`, `zdr` und `data_collection`. Abfrage der veröffentlichten
  Metadaten ergab `microsoft/mai-image-2.7-flash` auf `azure` als Bildmodell und
  den Endpunkt zusätzlich in der ZDR-Liste. Der feste Aufruf mit `n=1`,
  `zdr=true`, `data_collection=deny` und ausgeschaltetem Fallback lieferte
  HTTP 200 und ein dekodierbares PNG mit 1024 × 1024 Pixeln, 1.419.484 Bytes.
  Die Anbieterantwort meldete 0,01030825 USD; es wurden 39 Eingabe- und 1024
  Ausgabe-Bildtokens angegeben. Die Abbildung ist ein ungeprüftes Beispiel,
  keine fachlich freigegebene Vorlage.
* `openai/gpt-image-2.6-flare` über `openai` wurde bei gleicher ZDR-Vorgabe
  mit HTTP 404 abgewiesen. Die Vorgabe wurde nicht geändert und kein
  automatischer Modellwechsel ausgelöst; der anschließende Azure-Test war
  ein separater ausdrücklicher künstlicher Operatoraufruf.
* Die reguläre App kann diesen Endpunkt noch nicht nutzen: atomare Reservierung,
  belastbare Preisobergrenze, datensparsame Vorgaben, binäre Antwortgrenzen,
  Speicherung und Löschkonzept, Fachprüfung und App-Anzeige fehlen. Eine
  einzelne technische Probe beweist nicht die Qualität für beliebige Themen.

Daneben wurden zwei künstliche Luna-Paketproben über den regulären Adapter mit
globalem Azure-Routing ausgeführt: Geschichte wurde validiert (0,0023939 USD),
Biologie wurde wegen einer nicht zur Frage passenden vorbereiteten Grafik
verworfen (0,0023246 USD). Ein künstlicher Sol-Grafikauftrag mit einer Quelle
ohne Originalpfeil konnte die einzige angebotene Szenenvorlage nicht erfüllen
und wurde verworfen (0,02085 USD). Dies begründet keine allgemeine Freigabe
für Luna und keinen erfolgreichen Grafikabschluss. Zusätzlich verwendete eine
weitere Sol-Probe versehentlich eine nur für Paketvorlagen gedachte Referenz;
sie ist kein aussagekräftiger Test des regulären Seitenpfads.
Ein weiterer künstlicher Sol-Grafikauftrag mit ausdrücklichem Quellenpfeil
wurde wegen einer ungültigen Grafikreferenz verworfen (0,025924 USD). Die
versuchsweise geänderte Routenauswahl wurde deshalb wieder zurückgenommen;
keiner der Tests rechtfertigt eine pauschale Modellumstellung.

Die betroffene produktive Bienenrunde wurde ausschließlich lesend geprüft:
Sie bot nur das allgemeine Szenenrezept und die Quelle hatte keinen Pfeil.
Die neue Vorprüfung soll dafür vor einem bezahlten Auftrag abbrechen; eine
geeignete alternative Darstellung ist damit noch nicht geschaffen.

Quellen: [OpenRouter Image Generation](https://openrouter.ai/docs/guides/overview/multimodal/image-generation)
und die abgefragten Modell-/Endpunktdaten am 22.11.2026.
