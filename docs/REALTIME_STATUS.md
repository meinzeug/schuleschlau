# Statusaktualisierung und Wiederaufnahme

Stand: 04.11.2026. Diese Bestandsaufnahme beschreibt die vorhandenen
Clientpfade, keine allgemeine Echtzeit- oder Zustellgarantie. In `app/lib` und
`backend/schulpilot` ist derzeit kein SSE- oder WebSocket-Endpunkt implementiert.
Die zeitkritischen Ansichten verwenden begrenzte, authentifizierte GETs; eine
Statusabfrage ist kein Auftrag zur KI-Erzeugung.

| Bereich | Implementierung | Aktualisierung |
| --- | --- | --- |
| Heute / Elternüberblick | `app/lib/dashboard.dart` | Übersicht bei aktiver Vorbereitung nach 5 s, im Elternbereich sonst nach 15 s; Wiederaufnahme und Routenwechsel werden geprüft. |
| Fotoabgabe / Schultag | `app/lib/school_day_screen.dart` | Während Vorbereitung nach 3 s; bei Rückkehr neue Abfrage. Bereits laufende Abfragen werden bei Rückkehr revalidiert. Der ausdrücklich geöffnete Fotoeinstieg kann einen noch fehlenden Schultag anlegen; dies ist kein KI-Auftrag. |
| Lernweg | `app/lib/study_path_panel.dart` | Laufende Etappe nach 3 s prüfen; bei Rückkehr Status neu lesen. HTTP-4xx stoppen automatische Wiederholung, 403/404 entfernen die bisherige private Anzeige. |
| Einzelne Lernrunde | `app/lib/learning_preparation_screen.dart` | Bereits reservierter Auftrag alle 3 s, solange er läuft. Nach Rückkehr und vorübergehendem Lesefehler ein GET; keine automatische Auftragserstellung. |
| Glocke und Gesamtansicht | `app/lib/notification_inbox.dart` | Erste Seite und begrenzt gespeicherte Folgeseiten per GET, Vordergrundaktualisierung nach 45 s und bei Rückkehr; Lesebelege nur für sichtbare Meldungen. |
| Schulbuddy | `app/lib/tutor_sheet.dart` | Bei ausstehender Antwort aktiver Dialog nach 3 s. Kontowechsel verwirft Anzeige und Entwurf. |
| Klassenarbeitsnacharbeit | `app/lib/exam_review_panel.dart` | Bei laufender Analyse oder Erkennung nach 3 s; Anzeige und Entwürfe sind an den aktuellen Kontext gebunden. |
| Sprachwerkstatt | `app/lib/language_workshop.dart` | Aktive Projektverarbeitung nach 3 s; beim Zurückkehren erneut lesen. |

Die Intervalle sind Planungswerte im Vordergrund, keine garantierten
Lieferzeiten. Offline, Browser-Drosselung, ein gestörter Server, Schlafmodus
und Hintergrundbeschränkungen können Aktualisierungen verzögern. Firebase ist
ein zusätzlicher optionaler Benachrichtigungskanal; FCM-Annahme allein belegt
keine sichtbare Zustellung.

## Isolierte Regressionen

`learning_preparation_resume_status_test.dart` prüft bei 390 × 844 Pixeln
vorübergehende Ausfälle vor und nach der Rückkehr und verhindert automatische
Wiederholung von HTTP 429. `school_day_background_test.dart` prüft einen alten
GET beim Vordergrundwechsel und einen zwischenzeitlich ersetzten Sitzungstoken;
`study_path_panel_test.dart` prüft eine solche Wiederaufnahme im Lernweg sowie
403/404/429. Die Testtransporte verwenden ausschließlich künstliche Daten;
die geprüften Wiederaufnahmen senden keine POSTs und starten keine KI-Aufträge.
Die zugehörigen mobilen Fälle wurden auch im Chrome-Webrunner ausgeführt.

Diese Fälle beweisen weder eine vollständige Abnahme aller Geräte- und
Mehrkontoszenarien noch einen flächendeckenden Echtzeitkanal. Insbesondere
Schulbuddy, Klassenarbeiten und Sprachwerkstatt benötigen eigene systematische
Offline-, Routenwechsel- und konkurrierende Geräteprüfungen. Ob und wo ein
ereignisbasierter Kanal gegenüber den bestehenden GETs einen belegbaren Nutzen
bringt, ist separat zu entscheiden. Kein Android-Gerätetest wird hier behauptet.
