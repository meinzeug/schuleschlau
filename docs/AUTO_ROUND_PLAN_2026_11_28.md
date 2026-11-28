# Priorität: Lernrunden aus Heftthemen vorbereiten

Betreiberauftrag vom 28.11.2026: Bereits beim Entstehen des Lernwegs nach
Heftverarbeitung sollen passende Lernrunden automatisch vorbereitet werden,
damit das Kind beim Öffnen nicht jedes Mal eine Erzeugung auslösen und warten
muss. Vorbereitung ist nicht gleich Start: kein Lernzeit- oder Antwortbeleg,
keine aktive Runde allein durch Erzeugung. Bereits gespeicherte Runden müssen
erreichbar bleiben. Abrufe/Seitenwechsel bleiben rein lesend.

Die normale Grenze von zwölf Etappenanforderungen pro zehn Minuten und
anfragendem Konto gilt weiterhin. Ist das Zeitfenster ausgeschöpft, wartet
der Hintergrundlauf ohne zusätzlichen Anbieteraufruf auf das nächste Fenster.
Nur ein ausdrücklich angeforderter erfolgreicher Wiederholungsversuch kann
einen zuvor gestoppten Lauf fortsetzen; ein Fehler wird nicht automatisch
erneut an den Anbieter gesendet.

## Beobachteter Iststand
- `learning.plan` bietet bestätigte Einzelmaterialien und nicht materialisierte
  `study_path`-Etappen als Startkandidaten; `library.learning_subjects` gruppiert
  diese mit bereits gespeicherten Einheiten. Das UI zeigt Material/Etappe als
  „Runde vorbereiten“; nur bestehende Einheiten starten sofort.
- `school_preparation` verwaltet Quelle, Session, Eltern-/Familienrechte,
  Providerrevision, Tarife, Folgejobs und atomare Reservierung. Die bestehende
  Paketpartitionierung kann Erstaufgaben bereitstellen; nur ungedeckte
  Lernwegblöcke brauchen weitere Vorbereitung.
- `study_path.prepare_block` erzwingt bislang eine bewusste Einzelanforderung,
  maximal einen laufenden Kinderauftrag und fachliche Reihenfolge. `job_context`
  prüft Quellenfingerprints, Plan und `block_reason` erneut. Diese Prüfungen
  dürfen für Hintergrundarbeit nicht still umgangen werden.

## Umsetzung / Nachweis offen

Zwischenstand: Für neue abgeschlossene Schultag-Vorbereitungen ist ein
quellen- und sitzungsgebundener Hintergrundlauf implementiert. Er reserviert
jeweils genau einen bestehenden Etappenauftrag, hält bei einem Fehlschlag an
und erzeugt weder Antworten noch Lernzeit. Die bisherigen Lernweg- und
Vorbereitungstests liefen mit 64 bestandenen und einem übersprungenen Fall;
gezielte künstliche PostgreSQL-Tests decken zusätzlich die automatische
Verarbeitung ab. Für neu bestätigte einzelne Heftseiten ohne Schultag gibt es
ebenfalls einen revisions- und sitzungsgebundenen Hintergrundauftrag. Dabei
wurden 14 künstliche PostgreSQL-Fälle einschließlich paralleler Worker sowie
Export, Löschung und Aufbewahrung geprüft. Beide Warteschlangen durchlaufen
auch bei mehr als 100 wartenden Einträgen alle Seiten in begrenzten Portionen.
Ein ausgeschöpftes kurzes Anfragelimit verzögert die Reservierung bis zum
nächsten Fenster; Kosten- und Kontingentsperren bleiben davon getrennt und
stoppen den Auftrag. Ein fehlgeschlagener Anbieterauftrag wird nicht dadurch
wiederholt.
Gleiche Fotos mit verschiedenen Uploadkennungen werden noch nicht allgemein
als Duplikate erkannt. Eine erfolgreiche echte KI-Probe für die neuen Abläufe
und ihre vollständige Browserprüfung stehen noch aus. Die bei automatischen
Etappen beobachtete Lernstandsänderung ist noch nicht atomar vollständig
abgesichert; siehe [Evidenzbeobachtung](AUTOMATIC_EVIDENCE_OBSERVATION.md).
Deshalb bleibt der übergeordnete Punkt offen.

Ein künstlicher End-to-End-Test deckt inzwischen Upload, zwei Erkennungen und
eine vorbereitete Runde ab; ein zweiter prüft parallele Uploadwiederholungen
mit demselben Schlüssel. Ein weiterer Test prüft die private In-App-Meldung
mit der passenden Rundenroute, wiederholten Recovery-Läufen, Zugriffstrennung
und Quellenänderung auf SQLite und PostgreSQL. Dabei findet kein Anbieter- oder
Push-Aufruf statt; eine tatsächliche Firebase-Zustellung ist damit nicht
nachgewiesen.
Dieselben Eigenschaften wurden auch für automatisch vorbereitete einzelne
Heftseiten geprüft, einschließlich paralleler Recovery-Läufe und
Quellenänderungen vor und nach dem Bereitstellen der In-App-Meldung.
Ein künstlicher Anbietergrenzfall deckt zudem Quellenrevisionen vor und
während eines Einzelrundenauftrags ab: Die Ausgabe wird verworfen, Kosten
werden entsprechend dem Versandzustand geführt und bestehende Antworten
bleiben erhalten. Ein automatischer Retry findet dabei nicht statt.
1. Trigger ausschließlich an einer gespeicherten bestätigten Heft-/Lernweg-
   Revision, nicht bei GET, und ein dauerhaftes revisionsgebundenes Journal:
   Block- und Quell-IDs, Reihenfolge, Zustand, Ursprungssitzung und -familie,
   Provider-/Elternplanrevision sowie idempotente Auftragskennung.
2. Fehlende Themenrunden mit bestehenden vorbereiteten Einheiten abgleichen;
   Atomik für parallele Uploads, erneute Verarbeitung, mehrere Geräte und
   Überschneidungen. Pro Kind/Quelle/Block kein Duplikat und niemals
   beantwortete oder laufende Einheiten überschreiben.
3. Serverseitiger Worker nimmt zulässige offene Blöcke begrenzt nacheinander
   auf; normale Budgetreservierung, Kostenbuchung, Berechtigung, Consent und
   Providerbindung vor/nach jedem Aufruf. Kein automatischer Providerwechsel,
   kein endloses Retry; Fehler und Kosten nachvollziehbar, Status sichtbar.
4. Vorberechnung darf fachliche Anpassung an spätere Antworten nicht als
   bereits erfolgt ausgeben. Reihenfolge/Elternpflichten wahren; bei geänderter
   Quellen-, Plan- oder Lernstandsbasis veraltete noch nicht begonnene
   Vorbereitungen als solche kennzeichnen und bewusst neu einordnen, bestehende
   Antworten niemals umschreiben. Keine Vorhersage von Beherrschung.
5. Kind sieht einsatzbereite Runde direkt und beim Fehler eine verständliche
   Wiederaufnahme; offene Lernrunde und Zwischenstände bleiben bedienbar.
   Eltern erhalten verständlichen Status. Benachrichtigung nur bestehende
   Berechtigungen/Ruhezeiten, keinerlei privaten Inhalte in Push.
6. Künstliche SQLite-/PostgreSQL-Tests für Revisionen, Sperren, parallele
   Events, Budget/Session-/Freigabeentzug, Workerabbruch, Fehler und bestehende
   Runden; echter autorisierter KI-Test mit künstlichen Daten und Browserprüfung.
   Nicht als erledigt markieren, bevor das tatsächlich nachgewiesen ist.
