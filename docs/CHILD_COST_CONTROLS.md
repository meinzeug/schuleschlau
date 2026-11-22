# Verbindliche KI-Kostenlimits je Kinderzugang

Die Betreiberansicht bietet unter KI/Kosten eine eigene Auswahl der Kinderkonten.
Tages- und Monatslimit werden unabhängig in EUR eingegeben. „Unbegrenzt“ wird als
`null` gespeichert; `0` verhindert neue kostenpflichtige KI-Aufträge. Die
Zeitzone bestimmt den Beginn von Tag und Monat. Gespeicherte Aufgaben und
Erklärungen sowie freiwilliges Weiterlernen sind keine zeitlichen Kontingente.

Erst ausdrücklich gespeicherte, aktivierte Kindereinstellungen ersetzen für
dieses Kind die bisherigen Familien-Aufruf-/USD-Limits und den alten monatlichen
Kinderkostendeckel des Modellmixes. Der Server reserviert genau nach dieser
Policy. Eltern-/Familienrechte, Tarife, Anbieterfreigabe, Notfallstopp und der
getrennt ausgewiesene globale Betriebskosten-/Aufrufschutz bleiben bestehen.
Ohne aktivierte Kindereinstellung zeigt die Übersicht die tatsächlich weiter
wirksamen Altgrenzen, nicht eine erfundene Freigabe.

## Preis und Reservierung

- Anbieterpreise werden in ganzzahligen Mikro-USD geführt; die EUR-Umrechnung
  verwendet belegten Decimal-Wechselkurs und einen gespeicherten Kurssnapshot.
  Auf Mikro-Einheiten notwendige Rundung erfolgt konservativ nach oben.
- Ein bekannter Anbieterpreis ersetzt die vollständige Anbieterreservierung.
  Ein noch fehlender Gebührenbeleg hält nur die Gebührenreserve. Bekannter Preis
  und voller Generierungshold werden nicht doppelt verbucht.
- Unbekannte Preise bleiben als unbekannt mit Reservierung sichtbar. Das gilt
  insbesondere für den Codex-Kontozugang, der keine tatsächlichen USD-Kosten
  ausweist. Er ist weder kostenlos noch ein OpenRouter-Kostenbeleg.
- OpenRouter-Antwortpreise erhalten zusätzlich einen begrenzten Abgleich über
  `GET /api/v1/generation?id=...`. Auch bereits gemeldete Preise werden geprüft.
  Ein korrigierter Generierungsbeleg wird idempotent verbucht. Ohne gültige
  Generierungskennung wird kein exakter Preis erfunden.
- Preisbelege in der Adminansicht unterscheiden „gemeldet“, „mit
  Generierungsbeleg abgeglichen“ und „offen“. Ein bewusst angeforderter erneuter
  Belegabgleich startet ausschließlich Metadatenabruf, keine neue KI-Antwort.
- Guthabenbelege/Gebühren bleiben gesondert. Bei späterer Preisänderung nach
  Gebührenzuordnung wird eine nötige Gebührenkorrektur ausdrücklich markiert;
  frühere Belege werden nicht stillschweigend umgeschrieben.
- Nur ein nachweislicher Fehler VOR dem Aufruf der Anbieterfunktion hebt eine
  ungenutzte Reservierung als `cancelled` auf. Nach Funktionsaufruf ohne Beleg
  bleibt sie konservativ erhalten.

## Automatischer Abgleich

Der bestehende Worker prüft höchstens alle sechs Stunden den aktuellen
EZB-Referenzkurs und die Preismetadaten der ausdrücklich eingestellten
OpenRouter-Modelle und Upstreams. Der EUR/USD-Kurs wird aus der EZB-Angabe
invertiert und auf sechs Nachkommastellen aufgerundet; veraltete oder ungültige
Dokumente werden verworfen. Für Tokenpreise zählt die höchste veröffentlichte
Preisstaffel. Zusätzliche, nicht unterstützte Aufruf- oder Bildgebühren sowie
fehlende oder mehrdeutige Endpunkte verhindern die Übernahme dieses Preises.
Die Quellen werden unabhängig geprüft; ein Ausfall überschreibt keinen alten
gültigen Wert. Bei längerem Ausfall bleiben bestehende Frischeprüfungen aktiv.

Ein Update wartet auf das Ende laufender und vorgemerkter KI-Aufträge und wird
mit neuen Reservierungen über die Providerzeile serialisiert. Es ändert weder
Provider, Modell, Region, Ausgabelimit, Reservierung, Kontolimits noch die
fachliche oder Datenschutzfreigabe. Ein Metadatenabruf verlängert ausdrücklich
nicht die Gültigkeit einer praktischen Modellprüfung. Die Providerrevision und
ein inhaltsfreier Auditbeleg dokumentieren jede Übernahme; alte Aufträge und
Kostenbelege behalten ihren ursprünglichen Kurssnapshot. Die Admin-Routing-API
und die Adminoberfläche zeigen den letzten Versuch sowie die letzte erfolgreiche
Übernahme getrennt für EZB und Modellstufen; ein teilweiser Erfolg ist kein
Beweis, dass jede Quelle aktuell war.

## Server und Daten

`child_cost_controls.py`, `child_cost_models.py`, `providers.reserve`,
`ai_accounting.py`, `job_failures.py` und `model_routing.py` verwenden denselben
Kostenvertrag. Migration 0038 ergänzt Policy, revisionsgebundene Änderungen und
je ursprünglichem Usage eindeutige `usage_cost_balances`.

`GET /admin/child-cost-controls` listet begrenzt und durchsuchbar ausschließlich
Kostenmetadaten. `GET/PUT /admin/children/{id}/cost-controls` benötigt eine aktuelle
Admin-Sitzung; PUT zusätzlich Revision und Idempotenzschlüssel. Der bestehende
Child-Lock schützt gleichzeitige Policyänderung und Reservierung. Neue Zeitzone
oder Kurse setzen vorhandenen Verbrauch nicht zurück. Die Anzeige lädt nie
private Materialien oder Kinderantworten.

`GET /admin/children/{id}/cost-calls` bietet begrenzte Preisbelege;
`POST /admin/usage/{id}/refresh-cost` ist auditierbar und auf drei bewusste
Metadatenauffrischungen je ursprünglichem Beleg begrenzt. Alte Antwortcallbacks
sind an Konto, Sitzung, ausgewähltes Kind, Revision und aktuelle Liste gebunden.

Kinder-/Familienexport und Löschung führen Policy und Balances mit; alte
Policyänderungsbelege verfallen nach 365 Tagen. Die live wirksame Policy wird
nicht durch diese Aufbewahrung entfernt. Finanzielle Diagnoseholds dürfen
nicht durch Löschen einer Bild-/Diagnosefreigabe aus einem Arbeitsbudget
verschwinden.

## Quellen

OpenRouter dokumentiert Generierungsbelege unter
https://openrouter.ai/docs/api/api-reference/generations/get-generation .
Reasoning- und Providerparameter:
https://openrouter.ai/docs/guides/best-practices/reasoning-tokens und
https://openrouter.ai/docs/guides/routing/provider-selection .

EZB-Referenzdaten: https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml .
Am 22.11.2026 war der letzte veröffentlichte Referenzstand der 20.11.2026:
1 EUR = 1,0990 USD; konservativ gerundet 1 USD = 0,909919 EUR. Ein
OpenRouter-EU-Metadatenabruf ist kein Nachweis, dass der Schlüssel zur
EU-Inferenz berechtigt ist. OpenRouter beschreibt regionale Zugriffe und
deren gesonderte Guardrails unter https://openrouter.ai/business/eu .
