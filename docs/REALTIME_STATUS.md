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
| Schulbuddy | `app/lib/tutor_sheet.dart` | Bei ausstehender Antwort aktiver Dialog nach 3 s. Konto-, Familien- oder Tokenwechsel verwirft Anzeige und Entwurf. Eine Rückkehr während eines laufenden GETs löst anschließend einen erneuten GET aus; bei HTTP 4xx erst nach bewusstem Aktualisieren erneut lesen. |
| Heftseite erneut einlesen | `app/lib/material_actions.dart` | Beobachtet einen bestehenden Auftrag per GET. Hintergrund und Sitzungswechsel verwerfen überholte Antworten; nach Rückkehr werden Quelle und Auftrag neu geprüft, auch nach vorübergehendem Lesefehler. Ist die Seite beim Zurückkehren überdeckt, erfolgt die Prüfung nach ihrer erneuten Sichtbarkeit. 4xx werden nicht automatisch wiederholt; 403/404 entfernen die private Anzeige. |
| Klassenarbeitsnacharbeit | `app/lib/exam_review_panel.dart` | Bei laufender Analyse oder Erkennung nach 3 s; 4xx stoppen automatische Abfragen, 403/404 verbergen private Ergebnisse. Bewusstes erneutes Laden bleibt verfügbar. |
| Sprachwerkstatt | `app/lib/language_workshop.dart` | Aktive Projektverarbeitung nach 3 s; bei Rückkehr erneut lesen. Sitzung, Familie und Konto begrenzen den Kontext; 4xx stoppen automatische Abfragen und 403/404 verbergen private Ergebnisse. |

## Sitzungswechsel in den Übersichten

Die Kinder-Heute-Seite und der Eltern-Lernüberblick binden nun auch die
bereits geladene Ansicht an den Sitzungstoken, mit dem sie geöffnet wurde.
Bei gemeldetem Tokenwechsel verschwinden Inhalte und Aktionen sofort; ein
noch laufender Statusabruf darf sie nicht zurückbringen und es folgt keine
automatische weitere Abfrage. Die Fälle in `child_home_polling_test.dart`
und `parent_overview_refresh_test.dart` verwenden künstliche Daten und
prüfen ausschließlich GET-Aufrufe. Sie decken Tokenwechsel im Client ab;
ein Cookie-Wechsel ohne entsprechende Aktualisierung des App-Kontostands
und eine echte geräteübergreifende Zustellung sind damit nicht belegt.

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
Mehrkontoszenarien noch einen flächendeckenden Echtzeitkanal. Der Schulbuddy
besitzt künstliche Widgetprüfungen für die Rückkehr während eines laufenden
GETs, HTTP 429 und den Wechsel des Sitzungstokens. Insbesondere
Klassenarbeiten und Sprachwerkstatt benötigen weitere systematische
Offline-, Routenwechsel- und konkurrierende Geräteprüfungen. Ob und wo ein
ereignisbasierter Kanal gegenüber den bestehenden GETs einen belegbaren Nutzen
bringt, ist separat zu entscheiden. Kein Android-Gerätetest wird hier behauptet.

## Ergänzung: Sprachwerkstatt und Nacharbeit

Der Sprachprojektstatus verwirft beim Hintergrund- oder Sitzungswechsel ältere
Antworten; eine Rückkehr liest den aktuellen Stand, sofern kein 4xx-Fehler die
automatische Abfrage angehalten hat. Ein anfänglich im Hintergrund geöffnetes
Projekt wartet bis zum Vordergrund. Nach 403/404 werden alte Projekte und
Quelllisten verborgen; bei 429 bleibt der letzte Stand erhalten. Ein ausdrücklich
ausgelöstes „Erneut laden“ kann nach 4xx wieder lesen. Entwürfe in der
Sprachwerkstatt sind an Konto, Familie und Sitzung gebunden.

Auch die Nacharbeit fragt nach einem 4xx nicht automatisch weiter. Bei 403/404
wird der private Bericht verborgen; der eigene ungesendete Entwurf bleibt im
Speicher und erscheint nach erneut gewährtem Zugriff bei unveränderter Quelle
wieder im Eingabefeld. Hat sich die Quelle geändert, wird er gesondert gezeigt
und nicht ungeprüft übernommen. Künstliche Fälle prüfen diese Unterscheidung,
403, 404, 429 und den ausdrücklichen Abruf, ohne einen KI-Auftrag anzustoßen.

Die Tests verwenden künstliche Transporte und sind keine End-to-End-Abnahme
mehrerer echter Geräte oder ein Nachweis von Pushzustellung. Die vollständige
übergreifende Abnahme des Echtzeit-Roadmappunkts bleibt offen.

## Künstlicher Mehrsitzungstest

`backend/tests/test_realtime_multidevice.py` meldet dasselbe künstliche Kind in
zwei unabhängigen Sitzungen an. Beide fragen denselben gespeicherten
Sprachprojektauftrag vor und nach der Verarbeitung durch den echten Worker ab;
der Providertransport wird dabei künstlich simuliert. Ein anderes Kind derselben
Familie erhält keinen Zugriff. Wiederholte GETs ändern weder die Zahl der
Aufträge und Kostenbelege noch die der Runden, Antworten oder Lernaktivitäten.
Der Worker wird ausdrücklich genau einmal gestartet. Der Fall bestand auf
SQLite und isoliertem PostgreSQL.

`app/test/notification_multidevice_test.dart` verwendet drei getrennte
Clientzustände und einen simulierten Dienst: Nach der Wiederaufnahme erhalten
beide Sitzungen des einen Kontos die eigene neue Meldung; ein Geschwisterkonto
sieht sie nicht. Dieser Test prüft die Client-Wiederaufnahme, nicht den
FCM-Transport oder zwei gleichzeitig installierte Apps. Zusammen mit der
Backendprüfung ist dies ein gezielter Mehrgerätebeleg für Sprachstatus und
Glockencache; eine durchgehende Geräteabnahme sämtlicher Ansichten bleibt offen.

## Mehrsitzungstest für Fotoverarbeitung

`test_two_sessions_follow_photo_preparation_without_creating_jobs` prüft den
realen Foto-Vorbereitungsworker mit einer künstlichen Seite und simuliertem
Provider. Zwei unabhängige Sitzungen desselben Kindes lesen zunächst
`processing`, nach der ausdrücklich gestarteten Verarbeitung `needs_review`
mit einer erkannten Seite. Eine fremde Kindersitzung wird abgewiesen. Wiederholte
GETs verändern weder Auftrags- und Kostenbelege noch Lernrunden, Antworten oder
Aktivitäten. Der Test bestand mit SQLite und isoliertem PostgreSQL; er belegt
weder echte parallele Geräte noch sichtbare Pushzustellung.

## Rückkehr beim erneuten Einlesen einer Heftseite

Künstliche Widgettests prüfen die Rückkehr nach einem Serverfehler, einen
verspäteten GET aus dem Hintergrund, einen Sitzungstokenwechsel, den Entzug
des Quellzugriffs und HTTP 429. Eine zuvor fertige Aktion bleibt während der
erneuten Rechteprüfung verborgen. Auch wenn beim Vordergrundwechsel eine
andere Route darüberliegt, wird nach Sichtbarkeit die Quelle erneut geprüft.
Die Regression umfasst 37 VM-Widgetfälle mit angrenzenden Datenschutzfällen
und 25 Fälle im Chrome-Webrunner; sie verwendet Mocktransporte und keine
echten Kinderdaten oder Anbieteraufrufe. Die übergreifende geräteübergreifende
Abnahme und ein ereignisbasierter Kanal bleiben offen.
