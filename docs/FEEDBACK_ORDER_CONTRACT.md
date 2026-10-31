# Offener Vertrag: Reihenfolge gespeicherter Rückmeldungen

Stand 31.10.2026. Dies ist ein lokaler Entwicklungs- und Testplan, keine
implementierte oder freigegebene Lösung. Der bestehende Fehler bleibt offen.

## Nachgewiesene Probleme

Ein synthetischer API-Fall mit zwei Fragen und gleichem Zeitstempel ergibt
gleichzeitig eine sichtbare Rückmeldung in der Einheit, keine Wiederaufnahme in
der Übersicht und HTTP 409 bei der Quittierung. Die Detailansicht vergleicht
fragebezogene Versuchsnummern über verschiedene Fragen hinweg; Übersicht und
Quittierung verwenden stattdessen zufällige IDs als Gleichstandsauflösung.
`backend/tests/test_feedback_legacy_order.py` hält den gewünschten
Ende-zu-Ende-Vertrag als strikten erwarteten Fehlschlag fest. Er behauptet
keine historische Reihenfolge.

Der Flutter-Lernraum las Bewertungsdetails aus dem letzten Versuch der Frage,
nicht aus der ID der angezeigten Rückmeldung. Ein lokaler Widgettest mit zwei
künstlichen Versuchen zeigte zur ersten Antwort die Begründung des zweiten
Versuchs. Die Darstellung wurde separat auf die vorhandene Attempt-ID gebunden;
`app/test/feedback_attempt_identity_test.dart` prüft dies und den fehlenden
Versuch. Für alte Backends ohne gespeicherte Rückmeldungs-ID bleibt der bisherige
lokale Ablauf bestehen. Dieser Teilfix löst den offenen Reihenfolgenfehler
nicht; der Test belegt keine Produktionshäufigkeit.

Für die ausdrücklich bedingte Neubewertung meldet das Backend zusätzlich
`supports_recheck_attempt_id`. Neue Clients senden die angezeigte Attempt-ID
nur bei dieser Fähigkeit; unter der Einheitensperre prüft das Backend die ID
gegen den letzten sicher zu bestimmenden Versuch derselben Frage. Ein später
gespeicherter Versuch führt zu HTTP 409, auch bei identischem oder rückläufigem
Uhrwert. Fehlende, ungültige oder doppelte alte Versuchsnummern bei mehreren
Antworten bleiben ungeklärt und werden nicht anhand der ID geraten. Bei alten
Backends oder fehlender Attempt-ID bieten neue Clients stattdessen die
Lernhilfe an. Alte Clients können weiterhin den bisherigen ungebundenen Aufruf
ohne Body verwenden; er erhält dadurch keine neue Rennschutzgarantie. Dieser
gezielte Schutz für Neubewertungen löst die globale Rückmeldungsreihenfolge
zwischen verschiedenen Fragen nicht.

## Zielvertrag und Datenmodell

- Für jede neu gespeicherte Antwort eine positive, innerhalb der Einheit
  eindeutige und monoton steigende Sequenz persistent vergeben. Die Vergabe
  erfolgt nach Idempotenzprüfung, unter der bereits bestehenden Einheitensperre
  und in derselben Transaktion wie Attempt und Rückmeldungsmarker. Ein Replay
  erzeugt keinen neuen Versuch und keine neue Sequenz. Eine eindeutige
  Datenbankbedingung schützt zusätzlich gegen Kollisionen.
- Die Migration ergänzt eine nullable Sequenz und lässt bestehende Zeilen
  unverändert. Die Reihenfolge sequenzierter Zeilen richtet sich nach der
  Sequenz, auch bei rückwärts laufender Uhr. Auch fragebezogene Auswertungen
  müssen diese Reihenfolge verwenden; Versuchsnummern dürfen weiterhin nur
  innerhalb derselben Frage als Nachweis verwendet werden.
- Die Aussage, dass sequenzierte Antworten nach allen NULL-Altantworten liegen,
  erfordert einen verlässlichen Cutover: Vor der Migration alle möglichen alten
  Schreibprozesse stoppen; nach einem Code-Rollback oder einer Wiederherstellung
  dürfen diese nicht wieder unsequenzierte Antworten erzeugen. Der bestehende
  Aktivierer stoppt API und Worker vor Migrationen; der Rollbackpfad muss vor
  Freigabe ausdrücklich mitgeprüft und abgesichert werden. Eine mögliche
  Datenbank-Vergabe für alle Writer braucht eigene PostgreSQL-/SQLite- und
  Migrationsprüfungen; die hier beschriebene App-Vergabe allein beweist keinen
  sicheren Rollback auf ältere schreibende Releases.
- Detailansicht, kompakte Übersicht, Antwort, Quittierung, Anzeige zusätzlicher
  Erklärung, Lerncontroller, Jobbindung und Schulbuddy verwenden denselben
  Resolver. Er unterscheidet eine belegbar aktuelle Rückmeldung von historischen
  ungelesenen Markern und ungeklärter Reihenfolge. Ein anderer Client oder ein
  Wiederholungsversuch darf die neue Rückmeldung nicht mit einem alten ACK
  quittieren. ACK bezieht sich immer auf eine konkrete eigene Attempt-ID und ist
  unter Einheitensperre idempotent. GET erzeugt und quittiert keine Marker.
- Für Altgleichstände verschiedener Fragen existiert kein verlässlicher
  Reihenfolgenachweis. Keine zufällige ID oder fremde Versuchsnummer darf zum
  Beweis der letzten Antwort umgedeutet werden. Ungelesene Marker bleiben
  erhalten und müssen mit sichtbarer Kennzeichnung erreichbar sein; ihre
  Präsentationsreihenfolge ist keine historische Aussage. Mehrdeutige oder
  unvollständige Altbestände dürfen keine unsichtbare Rückmeldung zur Sperre
  für Weiterlernen, Abschluss oder Navigation machen. Ein nicht auflösbarer
  Marker braucht einen verständlichen, ausdrücklichen Umgang, ohne andere
  Marker pauschal als gelesen zu setzen.
- Neue Clients erhalten Antwort, Ergebnis, Unterstützung, Teilbewertungen und
  Bewertungsverlauf für genau die angezeigte Attempt-ID. Eine neue
  Detailansicht darf weder `attempts.last` einer anderen Antwort übernehmen noch
  eine Neubewertung ohne eindeutige Ziel-ID auslösen. Bei fehlendem Beleg bleiben
  Details offen; fachliche Urteile und alte Antworten werden nicht umgeschrieben.

## Clientkompatibilität als offene Bedingung

Der bestehende Flutter-Client versteht für die Fortsetzung nur eine einzelne
`pending_feedback`-Map und quittiert deren Attempt-ID. Zusätzliche
Mehrdeutigkeits- oder Kandidatenfelder ignoriert er. Ältere Appversionen nehmen
Bewertungsdetails zudem aus `attempts.last`. Nur ein neues Feld zu
ergänzen und im Backend trotzdem zu sperren kann daher ältere Clients
festsetzen; eine beliebige Kandidatenauswahl kann Details vermischen oder eine
historische Reihenfolge nahelegen. Ein serverseitig nicht blockierender Fallback
allein würde für den alten Client noch keinen sichtbaren Zugang zu allen
Markern beweisen.

Vor einer Umsetzung muss deshalb ein konkreter kompatibler Fallback für alte
Web-/Androidversionen nachgewiesen werden, der Zugang zu gespeicherten Markern
und Fortsetzung zugleich erhält. Neue Clients können eine capabilitygebundene,
ausdrücklich als ungeordnet gekennzeichnete Kandidatenansicht unterstützen.
Die reine Forderung nach einem App-Update darf nicht als erfüllter Zugang oder
als Vermeidung einer Blockade ausgegeben werden. Falls sich der Vertrag mit
alten Versionen nicht gleichzeitig erfüllen lässt, darf diese Änderung nicht als
vollständig kompatible Lösung freigegeben werden.

## Noch erforderliche technische Abnahme

1. Echtes Alembic-Upgrade auf isoliertem SQLite und PostgreSQL 16 mit mehreren
   NULL-Altversuchen, existierenden Markern und unveränderten Antworten;
   Nachweis des sicheren Writer-Cutovers und des dokumentierten Rückwegs.
2. Parallele Antworten auf verschiedenen Geräten mit gleichen Uhrwerten und
   umgekehrten IDs: eindeutige Sequenzen, idempotenter Replay, Rollback und
   Uhrensprung. Alte und neue Versionen einschließlich Schreibversuchen nach
   Rollback gezielt prüfen.
3. Detail, Übersicht, Controller, Schulbuddy, Exposure und ACK auf denselben
   Datenbestand prüfen: ein/mehrere ungelesene Marker, gelesene Marker,
   fehlende Aufgaben, mehrdeutige alte Antworten, neuerer unmarkierter Versuch,
   veralteter ACK und parallele ACKs. Kein GET verändert Daten oder startet KI.
4. Flutter und Browser mit 320 px und großer Schrift: zur angezeigten ID passende
   eigene Antwort und Bewertung, gekennzeichnete Mehrdeutigkeit, erreichbare
   nächste Aktion, kein verdecktes Feedback, keine doppelte Antwort. Auch alte
   Clients gegen neues Backend und neue Clients gegen altes Backend prüfen.
5. Export, Löschung und Aufbewahrung der Marker und neuen Sequenz prüfen.
   Nur synthetische Inhalte verwenden; keine externe Anbieteranfrage.
