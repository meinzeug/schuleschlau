# MediaExplorer – Arbeitsplan (28.11.2026)

## Bestand und Grundlagen
- Bestehenden `catalog_models.py`, `catalog_search.py`, `catalog_ai.py`,
  `catalog_jobs.py`, die bestätigten privaten Lernkontexte und `learning_tip_*`
  wiederverwenden; Fach- und Stufenkennungen nicht aus YouTube-Antworten oder
  Kinderfotos ableiten. Öffentlicher Katalog und private Lernnachweise bleiben
  getrennt. Existierende Sofatutor-Einträge und bestätigte Leerlisten erhalten.
  `catalog_search.current_snapshot()` ist derzeit ausdrücklich auf `sofatutor`
  festgelegt; eine zusätzliche Quelle benötigt einen expliziten eigenen Pfad
  oder einen kompatiblen Adapter und darf den alten Suchpfad nicht umdeuten.
- YouTube `search.list` liefert tatsächliche Kandidaten; `videos.list` prüft
  gültige Metadaten und Erreichbarkeit. Laut aktueller Google-Dokumentation
  gelten standardmäßig getrennte 100 `search.list`-Aufrufe pro Tag und 10.000
  Einheiten für andere Endpunkte; projektspezifische Kontingente können davon
  abweichen. Keine erfundenen IDs, Inhalte oder Kosten; API-Daten spätestens
  nach 30 Tagen erneuern oder löschen, audiovisuelle Inhalte nicht herunterladen.
- YouTube-Richtlinien verlangen die Meldung kindgerichteter Clients und
  verbieten bestimmte abgeleitete API-Daten/Metriken. Ob die geplante
  100-Punkte-Bewertung oder KI-Materialien aus solchen Daten zulässig sind,
  muss für den konkreten Fall geprüft werden; keine automatische
  YouTube-Datenbewertung als bereits erlaubt ausgeben. Eigene pädagogische
  Prüfungen transparent kennzeichnen und nicht aus Aufrufen/Likes ableiten.
- Gemini-Dokumentation beschreibt öffentliche YouTube-URLs als Preview;
  OpenRouter dokumentiert `google/gemini-2.5-flash` mit `input_video` und
  YouTube-URL auf dem Responses-Endpunkt. Dokumentation belegt weder die
  Freischaltung noch Kosten, Datenschutz-, Nutzungsrechte oder erfolgreiche
  Analyse für dieses Konto. Technische Erprobung getrennt belegen. Metadaten
  sind keine Inhaltsanalyse; ohne belegte Analyse keine Videozusammenfassung.

## Priorisierte Aufgaben (offen)

### Technischer Zwischenstand: gemeinsamer Evidenzkern

Eine additive Migration ergänzt öffentliche Medienreferenzen, mehrere
Lehrplanzuordnungen und versionierte redaktionelle Entscheidungen. Eine
interne, rein lesende Auswahlfunktion gibt ausschließlich öffentlich
zugeordnete, verfügbare und frische Medien nach einer menschlichen
Inhaltsprüfung zurück. Sie verlangt ausdrücklich passende Region, Schulform,
Stufenart, Stufe und Altersangabe. Lehrplan- und Medienrevisionen müssen
übereinstimmen; eine spätere Sperre schlägt eine ältere Freigabe. Historische
Quellen brauchen eine Einordnung, Propaganda und sensible Inhalte zusätzlich
eine Gegenperspektive. Ein bloßer Metadatentreffer gilt nie als Inhaltsprüfung.

Die Tabellen enthalten keine Kinder-, Familien-, Aufgaben- oder Lernstands-ID.
Sie dürfen bis zur Implementierung eines kontrollierten Importpfads und der
automatischen Lösch-/Aktualisierungsfrist nicht mit echten YouTube-API-Daten
befüllt werden. Die Auswahlfunktion selbst stellt die Quelle nicht dar und
bildet noch keine Autorisierungsgrenze für einen zukünftigen Endpunkt. Sie ist
nicht mit Sofatutor verbunden und verändert dessen Leerlisten nicht. Es gibt
noch keine Recherche, grafische Admin-Bedienung, Videoanalyse, Bewertung oder
Schüleroberfläche; eine erfolgreiche Inhaltsprüfung oder rechtliche
Freigabe wird damit nicht behauptet. Unbekanntes Alter oder unbekannte
Stufenart liefert weiterhin keine Empfehlung. Die erste Auswahl unterstützt
nur ausdrücklich im öffentlichen Lehrplan belegte Schulklassen; Phasen,
Sprachlernjahre, Vorschule und Hochschule bleiben offen. Eine redaktionelle
Zuordnung darf den belegten Klassenbereich nicht erweitern. Gespeicherte
Prüfungen belegen die Erklärung der Prüferin oder des Prüfers, nicht eine
kryptographische Unveränderlichkeit des externen Videos.

Für vorhandene Kandidaten gibt es einen begrenzten Admin-API-Pfad mit
blätterbarer Übersicht und revisionsgebundenen redaktionellen Entscheidungen.
Nur verifizierte, aktive Administratoren mit gültiger Sitzung können ihn
nutzen; bei Änderungen gelten die bestehenden Origin-/Requestheader-Prüfungen,
Sitzungssperre, ein begrenztes Kontingent und ein Auditereignis. Gleichzeitige
oder veraltete Entscheidungen erhalten einen Konflikt, statt eine neuere
Entscheidung zu überschreiben. Freigabe setzt die ausdrücklich bestätigte
inhaltliche Sichtung und frische, verfügbare Metadaten voraus. Historische
Quellen brauchen Einordnung, sensible Inhalte und Propaganda zusätzlich eine
Gegenperspektive. Eine spätere Sperre verdrängt eine frühere Freigabe sofort
bei der nächsten Auswahl. Freitext darf keine privaten Schülerdaten enthalten.
Die API importiert keine Medien, prüft kein externes Video und stellt keinen
Nachweis dar, dass die erklärende Person es tatsächlich angesehen hat. Eine
Oberfläche, Urheber-/Nutzungsrechte, Kontrollworkflow und Fristenbehandlung
bleiben offen.

Für vorhandene Kandidaten kann die Redaktion über einen zusätzlichen
Admin-API-Pfad ein bestehendes öffentliches Lehrplanthema ansehen und mit
explizitem, belegtem Klassenbereich zuordnen. Vor der Zuordnung werden die
Medienrevision, der Themendigest, Fach und Herkunft des Lehrplans sowie die
passende Medienregion geprüft. Gleiche Zuordnungen sind idempotent, parallele
Schreibaufträge werden serialisiert und eine abweichende alte Zuordnung wird
nicht versehentlich überschrieben. Ein ausdrücklich revisionsgebundener
Korrekturweg erlaubt Änderung, Entfernung und erneute Aktivierung. Entfernte
Zuordnungen bleiben als inaktive Version erhalten und verschwinden sofort aus
der Medienauswahl. Änderungen besitzen eine eigene Metadatenhistorie und Audit;
ein vorhandener Inhaltsprüfentscheid wird weder gelöscht noch erneuert. Bei
vor der Migration bestehenden Zuordnungen dokumentiert der erste spätere
Eingriff den damaligen Zustand als übernommen, ohne eine ursprüngliche
Entscheidungsperson oder ein Ursprungsdatum zu behaupten. Die Historie ist
nicht kryptografisch manipulationssicher und folgt den Löschbeziehungen des
jeweiligen öffentlichen Mediums und Themas. Eine seitenweise Liste zeigt
bestehende und entfernte Zuordnungen. Keine dieser Aktionen startet
einen externen Abruf, erzeugt Lernfortschritt oder ersetzt die separate
menschliche Inhaltsfreigabe. Die Freigabepolitik prüft weiterhin jede
Zuordnung beim Lesen. Es wurden
ausschließlich künstliche Daten getestet; eine Prüfung mit einem echten
Medienanbieter hat dabei nicht stattgefunden.

Die Adminansicht „Medienredaktion“ zeigt vorhandene Kandidaten seitenweise,
öffnet nur explizit angeklickte kanonische YouTube-Links und übermittelt eine
eindeutige redaktionelle Entscheidung mit Medienrevision und bisheriger
Prüfnummer. Freigaben setzen eine selbst bestätigte Inhaltsprüfung und je nach
Inhaltsart eine Einordnung beziehungsweise Gegenperspektive voraus; eine
vorsorgliche Sperre ist auch ohne Inhaltsprüfung möglich. Die eigene
Bestätigung ist keine unabhängige technische Bestätigung der Sichtung.
Sitzungswechsel verwerfen den Entwurf und spätere Antworten der alten Sitzung.
Die Oberfläche startet keine Recherche oder Provideraufträge, importiert
keine Kandidaten und bedient noch nicht die Themenzuordnung; nach einem
Revisionskonflikt muss das Medium bewusst neu geöffnet werden. Geprüft wurde
mit künstlichen Widgetdaten; echte Quellen-, Rechts- und Kinderabnahme bleiben
offen.

Die von der Netzschicht unabhängige YouTube-Metadatenprüfung kann in
synthetischen Tests bereits Suchergebnisse und Videoantworten auf tatsächlich
gelieferte Kennungen begrenzen. Sie verwirft nichtöffentliche, unverarbeitete,
laufende, altersbeschränkte, regional gesperrte und fehlerhafte Einträge;
Statistiken und Freitextbeschreibungen werden nicht übernommen. Sie erzeugt
ausschließlich kanonische Links und markiert alle Ergebnisse als ungeprüft.
Der mögliche Suchtext stammt nur aus einem öffentlichen, digestgeprüften
Lehrplanthema und dessen öffentlichem Stammfach; private Kindertexte sind
keine Eingabe. Die Implementierung führt **keinen** API-Aufruf aus und belegt
damit weder aktuelle Verfügbarkeit noch die Freischaltung oder Kosten eines
YouTube-Kontos. Vor einem produktiven Abruf fehlen insbesondere feste
Schlüsselverwaltung, API-Quota, Fristenlöschung, Rechte- und
Jugendschutzprüfung sowie die ausdrückliche Aktivierung.

1. [ ] Bestehende Katalog- und Providerpfade, explizite Alters-/Stufenangaben,
   Lernstands- und Rollenrechte sowie bisherige Freigaben nachvollziehen;
   konkrete Schnittstellen und Datenmodelle dokumentieren.
2. [ ] Medien und Quellen, Mehrfachzuordnungen, Prüfumfang, Versionen,
   Freigabe/Sperre, Jugendschutz, Verfügbarkeit und zeitgebundene
   API-Metadaten additiv im bestehenden Backend/DB modellieren; sichere
   Migration, Indexe und idempotente Zusammenführung testen.
3. [ ] Ausschließlich serverseitige, separat widerrufbare YouTube-Konfiguration,
   quota-bewusste Recherche und Verfügbarkeitsprüfung implementieren;
   Anfragen ausschließlich aus allgemeinen kuratierten Themen, niemals mit
   privaten Kinderinhalten. Strenge Timeouts, SSRF-Abwehr, Fehler/Backoff,
   revisionsgebundene Stornierung und API-Speicherfristen prüfen.
4. [ ] Redaktionelle Prüfung und sensible Themen absichern: historische Quellen
   nicht pauschal ausschließen, aber Propaganda und belastende Inhalte erst mit
   Altersfreigabe, Kontext, Gegenperspektive und menschlicher Freigabe ausgeben.
   Meldung/Sperre wirkt auf bestehende Karten unmittelbar; Admin erhält keinen
   Zugriff auf private Kinderinhalte. AI-Output bleibt untrusted.
5. [ ] Nachweislich geeignete, freigegebene Medien zu Fach/Thema/Unterthema,
   bekanntem Bildungsweg und altersgerechter Stufe auswählen. Fehlende Angaben
   ausdrücklich offen lassen. Kein Such- oder KI-Auftrag durch GET, kein
   Lernfortschritt nur durch Anzeigen/Öffnen.
6. [ ] Fachliche 100-Punkte-Matrix mit nachvollziehbarem Prüfstand und erlaubter
   unabhängiger Datengrundlage spezifizieren. Sicherheitsfreigabe schlägt Score;
   reine Metadaten niemals als Inhalts-/Qualitätsprüfung darstellen.
7. [ ] Tatsächlich unterstützte Videoanalyse mit festen serverseitig bestätigten
   Providern, getrenntem Kostenauftrag, auf Revisionsstand gebundener Herkunft
   und tatsächlichem Verarbeitungsnachweis anbinden; Rechte/AGB vor Speicherung
   oder Wiederverwendung abklären. Kein Downloader und keine Fallbacks.
8. [ ] Lernkarten, Fragen, Quiz und Zusammenfassungen ausschließlich aus
   belegbar analysierten und freigegebenen Inhalten ableiten; Quellen-/Versions-
   binding, erlaubte Speicherung, Fehler/Unsicherheit und neue ausdrückliche
   Aktion erhalten. Verstehen erst aus bewerteten Antworten dokumentieren.
9. [ ] Adminansichten für Quellen, Prüfung, Freigabe, Meldungen, Verbrauch,
   Aufträge und Fehler ergänzen; Backend-Autorisierung, Audit, Revisionen,
   Idempotenz und Kostenlimits testen; getrennte private Kinderrechte erhalten.
10. [ ] Kinderfreundliche Medienkarten in bestehender Lernansicht, kein Autoplay,
    Touch/Tastatur/Screenreader, knappe Hinweise und kindgerechte Erklärung;
    keine personenbezogenen Daten in externe Links und klarer Rückweg.
11. [ ] Künstliche Adapter-, Freigabe-, Kosten-, Frist-, Rechte-, Konflikt-,
    Prompt-Injection-, Mehrfamilien- und UI-Tests sowie nach separater
    Betreiberfreigabe kontrollierte Liveprüfung mit öffentlichen Medien;
    fehlende Zugänge/unerprobte Inhalte offen dokumentieren.

Quellen (offizielle Dokumentation):
https://developers.google.com/youtube/data/reference/rest/v3/search/list
https://developers.google.com/youtube/data/determine_quota_cost
https://developers.google.com/youtube/terms/developer-policies
https://ai.google.dev/gemini-api/docs/video-understanding
https://openrouter.ai/docs/guides/overview/multimodal/videos
