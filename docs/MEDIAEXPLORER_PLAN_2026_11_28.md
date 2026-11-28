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
