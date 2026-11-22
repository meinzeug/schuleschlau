# Geteilte KI-Lernbausteine

## Separat erzeugte öffentliche Illustrationen

Ein Bild für eine offene Lernrunde kann bewusst angefordert werden. Der Server
gleicht die Einheit zunächst lokal gegen einen eindeutigen aktuellen öffentlichen
Kataloginhalt oder einen ausdrücklich kuratierten öffentlichen Schwerpunkt ab.
Nur Fach und öffentlicher Titel gelangen in den Bildprompt; Hefttexte, private
Titel, Identitäten, Fotos, Antworten und Lernstände werden nicht übermittelt.
Bei fehlenden oder mehrdeutigen Zuordnungen bleibt die Funktion bewusst nicht
verfügbar. Alle Fächer und sämtliche denkbaren Themen sind damit nicht als
abgedeckt nachgewiesen. Für allgemeine Bienenrunden gibt es zusätzlich einen
eigenen öffentlichen Schwerpunkt „Honigbiene“ auf Basis der Arizona Extension.

`GET /units/{id}/public-image` ist rein lesend; `POST` benötigt einen eigenen
Idempotency-Key und reserviert genau einen Bildauftrag. Nach einer ausdrücklich
angeforderten, erfolgreich gespeicherten Lernrunde mit fehlender Erklärgrafik
kann der Worker zusätzlich genau einen solchen Bildauftrag automatisch
reservieren, sofern die Bildroute eingerichtet und ein sicherer öffentlicher
Treffer vorhanden ist. Er prüft dabei den ursprünglichen Eltern-/Kinderzugang
erneut und verwendet einen stabilen Idempotency-Key. Fehler erzeugen keinen
automatischen Folgeversuch und keinen kostenpflichtigen Szenen-Fallback; ist
die Bildroute oder die öffentliche Zuordnung grundsätzlich nicht anwendbar,
bleibt der bisherige Szenenweg erreichbar. Andere Familien mit dem
gleichen geprüften öffentlichen Thema und Altersbereich können ein bereits
gespeichertes Bild verwenden, ohne einen erneuten Anbieteraufruf zu bezahlen.
`GET /units/{id}/public-image/file` liefert die PNG-Datei nur nach der normalen
Einheiten- und Familienprüfung. Das Bild ist ein **ungeprüftes KI-Beispiel**,
kein Fachbeleg oder Antwortschlüssel. Unterschiedliche Bildversionen bleiben
anhand Inhaltshash und Modellherkunft nachvollziehbar. Fehlgeschlagene Aufträge
lassen maximal einen erneuten ausdrücklichen Versuch zu; Statusabfragen starten
keine Wiederholungen. Das Ansehen erzeugt keinen Kompetenznachweis.

Die optionale Routingkonfiguration `routes.image` muss ein einzelnes geprüftes
Bildmodell und genau einen Upstream, aktuelles Preisevidenz, Datenfreigaben,
praktische Prüfung und eine `image_output_budget`-Operatorschätzung enthalten.
Die Schätzung bindet Modell, Upstream, Eingabe- und Ausgabe-Token, Zeitpunkt
und Evidenz und muss mit der Reservierung gedeckt sein. Sie ist **keine** vom
Image-Endpunkt garantierte harte Ausgabetokengrenze. Der explizite reguläre
Auftrag verwendet bestehende Familien-, Kind- und globale Buchungsmechanismen,
ZDR und Datensammlungssperre; ohne Route oder gültige Freigabe kein Aufruf.
Die vorhandene regelmäßige Preisaktualisierung prüft die Image-API-Metadaten;
unbekannte Preiskomponenten werden nicht erfunden. Ist ein Kostenbeleg nicht
verfügbar, bleibt die Reservierung bestehen. Einer verspäteten Antwort nach
Abbruch entnommene Generation-ID kann dem Abgleich dienen; das Bild wird nicht
veröffentlicht. Die Providerantwort wird auf Größe, statisches Bildformat,
Pixelmaße und Metadaten geprüft und als PNG neu kodiert.

Ein explizit freigegebener Echtaufruf mit künstlichem Katalogthema über den
regulär reservierten Auftrag und den festen Azure-Endpunkt von
`microsoft/mai-image-2.7-flash` erzeugte im isolierten SQLite-Test ein PNG;
der Anbieter meldete 0,010398 USD. Dies ist kein Qualitäts- oder
Freigabenachweis für beliebige Bildinhalte oder für echte Familien.
Reproduzierbar mit `RUN_PUBLIC_IMAGE_PAID_PROBE=1` und dem in
`backend/tests/test_public_image_jobs.py` beschriebenen isolierten Test;
der Aufruf ist kostenpflichtig. Die Migration 0049 ergänzt nur die öffentliche
Auftragszuordnung und muss zusammen mit 0048 eingespielt werden.

## Unabhängige KI-Einschätzung eines öffentlichen Bildes

Nach einem erfolgreich gespeicherten Bildauftrag kann der Worker einmal einen
separaten `public_image_review`-Auftrag auf der fest konfigurierten,
bildfähigen Luna-Route reservieren. Das Bewertungsmodell muss sich vom
Bildgenerator unterscheiden. Es erhält ausschließlich das bereits bereinigte
öffentliche Bild, den lokal aufgelösten öffentlichen Fach-/Thementitel und,
falls vorhanden, einen kuratierten öffentlichen Sachtext. Der Katalogtitel
allein ist keine Sachquelle. Die Anfrage bindet einen Upstream, verlangt ZDR
und `data_collection=deny`, folgt keinen Weiterleitungen und verwendet keinen
Anbieterfallback. Ein eigener Nutzungsbeleg hält Reservierung und tatsächlich
gemeldete Kosten fest; unbekannte Kosten werden nicht als kostenlos gebucht.

`public_image_reviews` (Migration 0051) bindet die Einschätzung an Bildhash,
öffentlichen Spezifikationsdigest, Prüfvertragsversion, Modell und Upstream.
`approved` bedeutet ausschließlich, dass die prüfende KI keinen sichtbaren
Widerspruch gefunden hat; es ist weder ein menschlicher Fachcheck noch eine
Garantie. Die API weist deshalb zusätzlich aus, ob überhaupt ein kuratierter
Sachtext vorlag. `pending`, `uncertain` und `unavailable` sind keine Freigabe.
Ein `rejected`-Bild wird nicht mehr ausgeliefert oder von anderen Familien
wiederverwendet. Wenn die Begrenzung noch einen Versuch zulässt, kann ein Kind
ausdrücklich ein neues Bild anfordern; es gibt keinen endlosen Automatismus.

Ein begrenzter Worker-Backfill markiert und versucht höchstens ein älteres
Bild pro Wartungsintervall. Er verwendet ausschließlich die ursprüngliche noch
gültige Sitzung, Familienzuordnung und Quellenrevision sowie eine normale
separate Reservierung. Ohne gültige Autorität oder bei einem Fehler bleibt der
Status ehrlich `unavailable`; der Worker wiederholt diesen Fall nicht
automatisch. Berechtigte können ein vorhandenes Bild mit einem stabilen
Idempotenzschlüssel ausdrücklich prüfen lassen. Höchstens zwei Prüfversuche
pro Bild sind zulässig. GETs lesen nur und starten keine KI. Späte oder durch
Sitzungs-/Quellenänderungen überholte Antworten werden nicht veröffentlicht;
eine vorhandene Generationkennung bleibt für die Kostenklärung erhalten.

Ein echter künstlicher Test am 22.11.2026 überprüfte ein einfarbiges
Testbild gegen ein künstliches öffentliches Thema mit dem unabhängigen
`openai/gpt-6-luna`-/Azure-Endpunkt und normaler Reservierung. Ergebnis war
`uncertain`, der Anbieter meldete 0,000089 USD. Das ist ein technischer Test,
kein Nachweis der fachlichen Zuverlässigkeit für andere Bilder oder Themen.

## Ergänzung: fehlende Grafik in einer angeforderten Lernrunde

Wenn eine ausdrücklich gestartete reguläre Lernrunde ohne geprüfte Grafik
gespeichert wurde, darf der Worker anschließend **einen separaten** öffentlichen
Baustein reservieren. Die fertige Runde bleibt unabhängig vom Ergebnis dieses
Auftrags nutzbar. Übereinstimmung mit einem öffentlichen Katalogthema wird
lokal über Fach und Titel bestimmt; für Körperbau und Blutkreislauf der Honigbiene gibt es
zusätzlich feste öffentliche Schwerpunkte mit kurzer Sachgrundlage.
Andere nicht eindeutig zugeordnete
Themen starten keinen zusätzlichen Auftrag. Es gelangen keine Hefttexte oder
privaten Titel in den Bausteinauftrag oder in seinen gemeinsamen Cache.

Die App bietet einen gespeicherten Treffer in der Runde als **allgemeines,
fachlich ungeprüftes KI-Beispiel** an. Er ist keine Abbildung der eigenen
Heftseite und kein Beleg für eine richtige Aufgabenlösung. GET-Aufrufe lesen
den Status; sie starten keine KI. Rechte und Quellenstand werden beim Abruf
geprüft. Ein fehlgeschlagener Build wird nicht automatisch wiederholt.

Der Generator verwendet ab `public-assets-2` den kompakten, reversiblen
Ausgabetransport. Ab `public-assets-3` sind bei Szenen Pfeile je Phase bereits
im Ausgabeschema vorgeschrieben; der Bienenschwerpunkt bindet drei Körperteile.
Gültige laufende oder fertige `public-assets-1`-, `public-assets-2`- und `public-assets-3`-Bausteine
bleiben verwendbar und werden vor einem neuen Auftrag bevorzugt. Technische
Validierung ersetzt keine unabhängige fachliche Prüfung.

`public-assets-4` bindet beim Bienenschwerpunkt die zwei Pfeilphasen zusätzlich
an eine feste öffentliche Belegfolge. Frühere gültige Versionen bleiben
verfügbar; eine abgelehnte Version wird nicht automatisch erneut angefragt.

`public-assets-5` wählt den Schwerpunkt anhand des tatsächlichen Rundenthemas,
nicht anhand eines allgemeineren Seitentitels. Die Auslieferung verwirft auch
bereits gespeicherte Zuordnungen, wenn der Schwerpunkt nicht zur Runde passt.
Für den offenen Blutkreislauf der Honigbiene beschreibt ein eigener öffentlicher
Schwerpunkt zwei belegte, schematische Flussabschnitte. Bei anderen spezifischen
Bienenthemen ohne solchen Schwerpunkt wird keine generische Grafik automatisch
als passend ausgegeben. Vorhandene öffentliche Builds bleiben separat erhalten.

`public-assets-6` erweitert die lokale Auswahl um bestätigte öffentliche
Kataloginhalte. Deren vollständiger Titel muss nach Unicode-, Groß-/Kleinschreibungs-
und Leerzeichennormalisierung genau dem Rundenthema entsprechen. Fach, bestätigter
Titel, kuratierte Themenzuordnung und aktiver Katalogsnapshot werden geprüft;
mehrere mögliche Zuordnungen führen zu keinem automatischen Auftrag. Der
Kataloginhalt samt ID, öffentlichem Titel und Snapshot ist Teil des Build-Keys;
private Rundentitel und Hefttexte gelangen nicht in den öffentlichen Build.
Beim Abruf wird die Zuordnung erneut überprüft. Ein Katalogtitel bleibt
Metadatum und ist kein fachlicher Beleg; freie Synonymsuche und unscharfe
Zuordnung sind weiterhin nicht freigeschaltet.

Der textbasierte Ausweichpfad für einen gebundenen Einstieg überträgt jede
vorgegebene Einstiegs- und Übungsfrage in einem eigenen festen Schemafeld.
Die Decodierung verlangt dieselbe ID am richtigen Platz; Rollen, Antworten
und Quellen werden nicht umgedeutet. Anschließend greifen alle bestehenden
Lernstart-, Aufgaben- und Quellenprüfungen.

Die öffentliche Bienengrundlage beruht auf [University of Arizona: Honeybee Basic Biology](https://extension.arizona.edu/publication/honeybee-series-honeybee-basic-biology)
und [Arizona State University: Honey Bee Anatomy](https://askabiologist.asu.edu/honey-bee-anatomy).

Dieser erste vertikale Pfad erzeugt **unbewertete KI-Erklärungen und Erkundungsimpulse**, keine geprüften Antwortschlüssel und keine Schulnoten. Die vorhandenen kuratierten VisualReference-Rezepte bleiben getrennt. Technisch validierte KI-Beispiele gelten weiterhin als `factual_status: unassessed`.

## Öffentliche Grundlage und unveränderliche Version

`LearningAssetSpec` akzeptiert ausschließlich Fach aus den vorhandenen 24 Rendererprofilen, vorhandene Rezept-ID/-Version, echte öffentliche Grundlagen-IDs und/oder öffentliche Katalogthemen-ID sowie optional die eindeutig kuratierte öffentliche Inhalts-ID, `de-DE` und ein explizites Niveauband. Es gibt **kein** Feld für freie Themen, Heft-/Unittexte, Antworten, Namen oder private Quellen. Das vorhandene kurze Rendererlabel „Lerntechniken“ wird serverseitig an die tatsächliche Fach-ID „Lern- und Arbeitstechniken“ gebunden; weitere Client-Aliase sind nicht erlaubt.

Der Server löst alle IDs selbst auf. Der Build-Key ist SHA-256 über den vollständigen kanonischen öffentlichen Stand einschließlich Regelinhalt/-version/-digest, Katalogthema/-snapshot/-titel, Rezeptversion/-digest sowie Builder-, Ausgabe- und Renderervertrag. Private Konten, Familien, Kinder, Sitzungen und Aufgaben beeinflussen diesen Schlüssel nicht. Katalogtitel sind Navigation, **kein Fachbeleg**. Tatsächliche kuratierte Regeln bleiben als Herkunft gespeichert; selbst erzeugte Beispielzahlen/-beziehungen sind ausdrücklich unbewertete KI-Beispiele und keine fingierten Quellenzitate.

`learning_asset_builds` beansprucht diesen Schlüssel atomar. `learning_asset_instances` bindet die persönliche Nutzung und Idempotenz getrennt an Autor und Kind. Ein erfolgreicher Build veröffentlicht genau eine unveränderliche `VisualReference`-Version mit `scope: exploration_only`, `subjects: []`, Template und öffentlicher Herkunft. `subjects: []` verhindert auch beim früheren Leser ohne Scopeprüfung, dass ein solches Beispiel als kuratiertes Aufgabenrezept ausgewählt wird. Der neue Leser schließt diese Zeilen bereits in SQL aus.

## Bewusster Ablauf

1. `GET /api/learning-assets/catalogue`: Profile, echte Fach-ID-Zuordnung, vorhandene Rezepte, öffentliche Grundlagen und höchstens 100 Katalogthemen pro Seite; Empfehlungen stammen aus der bestehenden Kandidatensuche über ausschließlich öffentlichen Text. `topic_subject` und `page` grenzen die Themen ein.
2. `GET /api/learning-assets/lookup`: öffentliche Auswahl prüfen, ohne Aufbau, Reservierung oder KI.
3. `POST /api/children/{child_id}/learning-assets/prepare`: geschlossener Selector, `X-Schulpilot-Account` und eigener `Idempotency-Key` (16–80 Zeichen). Die vorhandene `visual-v1`-Clientfähigkeit ist erforderlich. Antwort ist eine **private Instanz**, kein fremder Jobbezug. Ein fertiger Treffer benötigt keinen Anbieteraufruf und keine Reservierung; ein paralleler Treffer übernimmt auch keine fremde Abrechnung.
4. Bei einem Miss: Child→Build sperren, einen normalen begrenzten Job samt vorhandener Unit-Reservierung erzeugen. Nur wenn die **unveränderte bestehende Routenauswahl tatsächlich Sol ergibt**, darf der Aufbau starten; sonst sperrt die Funktion. Keine neue Route oder Budget-/Tokenanhebung.
5. Der Worker gibt alle DB-Verbindungen/Sperren vor dem Anbieteraufruf frei. Er sendet nur den erneut kanonisierten öffentlichen Selectorstand. Actor/Sitzung/Familienrecht/Tarif, öffentliche Versionen und Providerrevision werden vor und nach dem Aufruf geprüft. Nach einem wartenden Childlock müssen Erfolgs- **und** Fehlerpfad den frischen Jobstatus erneut lesen; eine terminale Maintenanceentscheidung wird nicht überschrieben.
6. `GET /api/learning-asset-instances/{id}` und `GET /api/children/{child_id}/learning-assets` lesen ausschließlich eigene Instanzen. Die zweite Route liefert `{items: [...]}` mit maximal 50 Einträgen. Beide prüfen Actor, Familienrecht und `visual-v1`; sie starten keine KI.

Der öffentliche Build-DTO enthält niemals Job-/Actor-/Sitzungs-/Familien-IDs, Fehlerdetails, Verbrauch oder Kosten. Vor `ready` bleiben `asset` und `reference` null. Die Instanz enthält zusätzlich Fach und öffentlichen Titel, sodass auch wartende/fehlgeschlagene Einträge verständlich sind. Persönliche Schlüssel werden bei Wiederholung unverändert aufgelöst; derselbe Schlüssel für eine andere Kind-/Specbindung führt zu 409. Neue Instanzen sind separat auf 60/h je Actor begrenzt, bezahlte Misses auf 10/h, zusätzlich zu allen bestehenden Limits. Demo-Familien dürfen Treffer nutzen, aber keine neue reguläre KI starten.

## Technische Freigabe und Grenzen

Die Antwort enthält einen kurzen Text, genau eine endliche bestehende `Presentation` und 1–3 offene Denkimpulse **ohne** Antworten, Bewertung oder Kompetenzangaben. Bestehende Profil-, Zitat-, Zahlen-, Pfeil-, Offenlegungs- und Geometrieprüfungen bleiben aktiv. Szenen sind zusätzlich auf 2–4 Objekte und 2–3 tatsächlich verschiedene Phasen begrenzt; reine unveränderte Wortkästen werden abgewiesen. Das Wire-Schema verwendet bestehende JSON-Schema-Referenzen und bleibt kompakt. Unvollständige Anbieterantworten, insbesondere `finish_reason: length`, werden verworfen. Es gibt keinen Fallback, automatischen Retry oder zusätzlichen Modellaufruf.

Diese Prüfung beweist Datenform und innere Darstellungskonsistenz, **keine unabhängige Fachwahrheit**. Ein KI-Beispiel darf nicht als Fachquelle einer privaten benotbaren Übung dienen. Eine solche spätere Nutzung bräuchte einen eigenen fachlichen Review und den bestehenden Quellen-/Antwortvertrag; dieser erste Pfad bietet sie ausdrücklich nicht an. Die 24 Profilprüfungen belegen die Vertragsbreite einer deklarativen Szene, nicht 24 Fachinhaltsabnahmen und keinen vollständigen Lehrplan.

Der veröffentlichte Datensatz behält Builder-/Renderer-/Ausgabeschemaversion, die gespeicherte Modellroutenauswahl und – nur wenn tatsächlich vorhanden – einen geschlossenen Transportbeleg mit Modell/Provider sowie Schema-/Prompthashes. Job-, Kosten- oder Kontodaten gelangen nicht in diesen öffentlichen Beleg. Fehlende Transportbelege werden nicht erfunden.

## Fehler, Aufbewahrung und Rückweg

Fehlgeschlagene Builds sind für diesen Schlüssel terminal: auch ein nachgewiesen nicht versandter Auftrag wird derzeit nicht automatisch oder durch bloß erneutes Öffnen neu gestartet. Ein fehlender oder bereits terminaler Creatorjob wird nur lesend als `failed` projiziert, statt Mitnutzer unbegrenzt warten zu lassen; unbekannte Abrechnung wird dabei nicht freigegeben. Eine spätere bewusste Reparatur ist **noch nicht Bestandteil** dieses Vertrags.

Instanzen werden nach 365 Tagen entfernt und bei Child-/Autorlöschung kaskadiert. Persönliche Exportdaten sind nach Autor getrennt; das Kinderexport enthält die kindeigenen Instanzen, Elternexports ergänzen nur die anfordernde Elternperson. Öffentliche Versionen bleiben ohne Privatbindung erhalten. Das Löschen eines Creatorjobs setzt nur den internen FK auf null. Keine Ansicht schreibt Lernzeit, Attempt, Mastery oder Unitantworten.

Unterbrochene Assetaufträge werden vor der allgemeinen Wartung in begrenzten
Einzeltransaktionen mit denselben Child→Build-Sperren beendet. Ein inzwischen
fertig veröffentlichter Auftrag wird nicht rückwirkend abgebrochen. Trifft eine
Modellantwort erst nach dem Abbruch ein, bleibt der Auftrag terminal. Ihre
validierte Generationkennung wird ausschließlich am privaten Verbrauchsbeleg
erhalten, damit der bestehende OpenRouter-Metadatenabgleich den tatsächlichen
Preis nachtragen kann. Dies startet weder eine zweite Erzeugung noch eine neue
Verbuchung der ursprünglichen Reservierung.

Migration `0040_shared_learning_assets` ist additiv nach 0039 und erzeugt genau zwei Tabellen. Ein Code-Rollback vor dieser Migration benötigt eine bewusste Behandlung noch wartender neuer Jobarten und der Migrations-Headkompatibilität; der alte Worker kennt `learning_asset` nicht. Die vorsorgliche leere Rezept-Fächerliste schützt zusätzlich den alten Kandidatenleser, ersetzt aber keine abgestimmte Betriebsrückkehr.

## Nachweise

Die gemeinsame Flutter-Ansicht liegt unter `/discover/:childId` und ist unter
„Lernen“ im Drei-Punkte-Menü „Lernrunden suchen & ordnen“ über
„Themen mit Grafiken entdecken“ erreichbar. Der Einstieg benötigt keine eigene
Zeile oberhalb der gespeicherten Runden. Sie zeigt zunächst
Fach und Thema; Darstellung und Stufe sind aufklappbar. Das gewählte Fach wird
bereits beim ersten Laden serverseitig gefiltert, weitere Themen werden bewusst
seitenweise nachgeladen. Ein unsicher beantworteter Start behält seinen
Idempotenzschlüssel. Gespeicherte Themen und Statusabfragen verwenden nur GETs;
überdeckte Ansichten und der Hintergrund senden keine neuen Erzeugungsaufträge.
Alte Konto-, Familien- und Kindkontexte übernehmen keine späten Antworten.

Die persönliche Themenliste bleibt serverseitig erhalten. Der innere
Animationszustand dieses neuen Erkundungswegs ist zunächst lokal; eine
geräteübergreifende CAS-Speicherung dieses Zustands gehört noch nicht zu diesem
Vertrag. Die vorhandene technische Speicherung normaler Lernrunden bleibt
davon getrennt erhalten.

Schulbuddy erhält über die eigene Instanzkennung die tatsächlich gespeicherte
Erkundung. Der Server prüft Autor, Kind, Familienrecht, aktuellen Build und
Referenzdigest; frei vom Client gelieferte Grafik- oder Erklärungstexte sind
nicht erlaubt. Die Grafik bleibt ausdrücklich ein ungeprüftes KI-Beispiel,
keine fachliche Quelle. Auch die vergrößerte Ansicht bietet einen festen
Tutorzugang außerhalb der verschiebbaren Grafikfläche. Der Tutor sieht das
gesamte gespeicherte Beispiel, zunächst keine zusätzliche lokale Animationsphase.
Dieser Chat erzeugt keinen Hilfebeleg für eine parallel offene Lernaufgabe.

Neue synthetische API-/Worker-/Adaptertests und echte Alembic-Upgradeprüfungen liegen in `backend/tests/test_learning_assets.py` und `test_learning_assets_migration.py`. Sie prüfen den vollständigen Aufbau-/Trefferpfad, Parallelität, Rechte-/Versionswechsel, terminale Sperrraces, Zurückweisung privater Eingaben und Outputkürzung sowie erhaltene künstliche Bestandsdaten. Konkrete finale Laufzahlen stehen im Übergabebericht. Keine echten Kinderinhalte, externen Anbieteraufrufe oder Live-Buildqualitätsbehauptungen sind Teil dieser Tests.
