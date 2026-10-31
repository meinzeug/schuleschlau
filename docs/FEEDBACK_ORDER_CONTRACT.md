# Offener Vertrag: Reihenfolge gespeicherter Rückmeldungen

Stand 31.10.2026. Der globale Reihenfolgenfehler bleibt offen; der unten
genannte eng begrenzte Teilfall ist lokal korrigiert und wird separat geprüft.

## Nachgewiesene Probleme

Ein synthetischer API-Fall mit zwei Fragen und gleichem Zeitstempel ergibt
gleichzeitig eine sichtbare Rückmeldung in der Einheit, keine Wiederaufnahme in
der Übersicht und HTTP 409 bei der Quittierung. Die Detailansicht vergleicht
fragebezogene Versuchsnummern über verschiedene Fragen hinweg; Übersicht und
Quittierung verwenden stattdessen zufällige IDs als Gleichstandsauflösung.
`backend/tests/test_feedback_legacy_order.py` hält den gewünschten
Ende-zu-Ende-Vertrag als strikten erwarteten Fehlschlag fest. Er behauptet
keine historische Reihenfolge.

Weitere lokale Gegenbeispiele in derselben Testdatei zeigen die Grenzen:
Bei zwei zeitgleichen Versuchen *derselben* Frage, deren gespeicherte Nummern
1 und 2 die Reihenfolge belegen, wurde die im Detail angezeigte Rückmeldung
in der Übersicht nicht gefunden. Für diesen Teilfall verwendet der gemeinsame
Resolver jetzt nur dann die belegten Versuchsnummern, wenn alle Versuche am
neuesten Zeitstempel zur selben Frage gehören, alle Nummern dieser Frage
unterschiedliche positive Ganzzahlen sind und frühere Zeitstempel niedrigere
Nummern tragen. Die Übersicht prüft dafür höchstens 16 reguläre und 16
zusätzliche Gleichstandkandidaten; die Quittierung verwendet denselben
Resolver. Innerhalb des geprüften Suchfensters hat eine zeitlich neuere
Rückmeldung einer anderen Einheit Vorrang; ein ungültiger neuerer Kandidat
verdeckt dort nicht den nächsten geprüften Treffer.
Wenn das normale Suchfenster nur ungültige Kandidaten enthält, sucht die
Übersicht zusätzlich begrenzt nach bis zu 16 ungelesenen Antworten ohne
Zeitgleichstand. So verdecken beispielsweise 33 ungültige neuere Kandidaten
eine solche ältere Rückmeldung nicht mehr. Für diesen Zusatzschritt werden
keine gesamten Versuchs- oder Ereignisverläufe geladen. Ein synthetischer
Sättigungstest begrenzt die Anzahl der SQL-Abfragen auf höchstens 67; dies ist
keine Laufzeitmessung oder ein Beweis für allgemein begrenzte Datenbanklast.
Die zusätzliche Abfrage läuft nur, wenn das reguläre Suchfenster ausgeschöpft
wurde, ohne einen Treffer zu finden. Gültige zeitgleiche Rückmeldungen außerhalb
des bisherigen Kandidatenfensters kann sie weiterhin nicht garantieren; ein
älterer eindeutiger Treffer kann dann vor einem solchen Treffer erscheinen.
Ohne diesen Nachweis gilt
der bisherige Altbestand-Fallback; daraus wird keine Reihenfolge abgeleitet.
Die Kandidatengrenze kann bei vielen gleichzeitig offenen Altmarkern weitere
Rückmeldungen verbergen und ist keine Gesamtlösung. Außerdem kann bei zwei gleichzeitig markierten
Versuchen nach dem Quittieren eines Markers der andere weiterhin ungelesen in
der Datenbank liegen, ohne dass ihn der aktuelle Rückmeldevertrag anbietet.
Ein reiner UUID-Gleichstandsvergleich oder ein stilles Ausblenden ist daher
keine sichere Behebung. Ein Modelltest zeigt zudem, dass bei zwei verschiedenen
Fragen beide möglichen historischen Reihenfolgen identische gespeicherte Daten
ergeben können. Diese synthetischen Gegenbeispiele belegen keine Häufigkeit im
Produktionsbestand.

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

## Ausdrückliche Wiederherstellung für neue Clients

Neue Clients können bei mehreren oder widersprüchlich angezeigten ungelesenen
Markern die Schaltfläche „Rückmeldungen ansehen“ verwenden. Der Kinderzugang
liest dabei ausschließlich Marker seiner eigenen Einheit und zeigt je Seite
höchstens zehn eigene Antworten mit Aufgabenstellung und gespeichertem Ergebnis.
Die stabile Paginierung verwendet IDs nur zur Darstellung; ihre Reihenfolge ist
keine Aussage über den zeitlichen Ablauf. Lösungen, Erklärungen und interne
Bewertungsgründe werden in dieser Ansicht nicht zusätzlich offengelegt. Das
Öffnen und Blättern ist lesend und markiert nichts als gelesen.

Erst „Gelesen“ quittiert unter der Einheitensperre ausdrücklich die gewählte
Attempt-ID, wiederholt denselben Klick idempotent und erhält alle anderen Marker
und Antworten. Solange ein weiterer zu einer existierenden Antwort gehörender
Marker ungelesen ist, löst dieser Wiederherstellungsweg keinen Abschluss aus.
Nach dem letzten Marker prüft er dieselben Abschlussbedingungen wie der
reguläre ACK. Anders als der reguläre ACK startet er dabei ausdrücklich keinen
automatischen Coach-Auftrag; die vorhandene bewusste Aktion für den Rückblick
bleibt erreichbar. Ein synthetischer End-to-End-Test prüft Abschluss, echten
lokalen Demo-Rückblick, erhaltene Antworten sowie unveränderte Jobs und Kosten
bis zur ausdrücklichen Rückblickaktion. Ein offener Eingabeentwurf bleibt beim
Schließen der Wiederherstellung auf dem Gerät erhalten.
Wenn die Wiederherstellung auf einem Gerät bereits einen Marker quittiert hat,
erkennt ein verspäteter regulärer ACK dafür den Wiederherstellungsursprung und
ist ein idempotenter No-op. Außerdem schützt die Abschlussprüfung nach der ersten
Recovery-Bestätigung alle übrigen zu Antworten gehörenden ungelesenen
Marker, auch wenn danach ein anderes Gerät den regulären ACK verwendet. Für
Altbestände, bei denen noch niemand Recovery verwendet hat, bleibt das alte
Clientverhalten bestehen. Ein neuer Client kann mit dem fähigkeitsgebundenen,
ausdrücklichen POST `/feedback/recovery/begin` bereits vor dem Laden der Liste
die Abschlusssperre aktivieren. Der POST ist unter der Einheitensperre
wiederholbar, markiert keine Antwort als gelesen und startet keinen
Anbieterauftrag. Ein danach eintreffender regulärer ACK eines anderen Geräts
darf verbleibende ungelesene Marker nicht durch einen Abschluss verdecken;
automatische Rückblicke aus diesem ACK werden unterdrückt. Das gilt erst nach
Verarbeitung des Startsignals: Gewinnt ein alter ACK das Rennen vor dessen
Serversperre, bleibt der alte Vertrag wirksam. Alte Clients senden das
Startsignal nicht und haben weiterhin keinen vollständig kompatiblen
Wiederherstellungsweg. Der ursprüngliche Altfall ist damit nicht gelöst.

Die Wiederherstellungsliste zeigt keine Lösung. Könnte der normale
Feedbackraum vor dem Quittieren jedoch eine Lösungsgrafik oder eine automatisch
sichtbare Erklärung gezeigt haben, wird dies nur als **mögliche** Offenlegung
festgehalten. Daraus entsteht kein behauptetes tatsächliches Lesen. Bei einer
späteren, möglicherweise betroffenen richtigen Antwort bleibt die
Selbstständigkeit ungeklärt. Bereits ausdrücklich belegte Offenlegungen bleiben
davon getrennt. Für die eng begrenzte, versionierte Bruchvorlage kann eine
vollständig überprüfte numerische Erklärung ohne Lösungsgrafik belegen, dass
ein Folgebeispiel einen anderen Wert verwendet. Erklärung, gespeicherter Beleg
und mögliche Grafik werden bei der späteren Bewertung erneut abgeglichen;
fehlende, veränderte oder unvollständige Angaben gelten nicht als Beweis für
Selbstständigkeit. Der interne Marker wird mit den Aktivitätsdaten exportiert,
nach 365 Tagen und beim Löschen der Einheit entfernt und nicht in der normalen
Aktivitätsliste angezeigt. Ob die Lösung im Einzelfall wirklich gesehen wurde,
bleibt unbekannt.

Schließt das Kind die Liste während einer Bestätigung, wartet die Oberfläche
auf das Ende der Anfrage und gleicht anschließend ab, soweit kein offener
Eingabeentwurf überschrieben würde. Bei einem Timeout kann der Server trotzdem
erst später speichern; ein unmittelbar anschließender GET belegt dann keinen
endgültigen Zustand. Ein vorhandener Entwurf bleibt erhalten und der Zugriff
„Rückmeldungen ansehen“ bleibt in diesem Fall zum bewussten erneuten Abgleich
erreichbar. Ohne weiteren Abgleich kann die ursprüngliche Aufgabenanzeige nach
einem späten Commit vorübergehend veraltet bleiben; ein automatisches sicheres
Ende-zu-Ende-Commit-Signal ist damit noch nicht nachgewiesen.
Alte Marker mit gültigem JSON, aber unbrauchbarem Detailformat oder ohne
zuordenbare Attempt-ID werden beim Lesen und Quittieren ignoriert und nicht
verändert. Sie gelten nicht als Nachweis, dass ein gültiger Marker gelesen
wurde; die fachliche Zuordnung dieser beschädigten Datensätze bleibt offen.

Dieser Weg repariert nicht die historische Reihenfolge und ersetzt keine
Migration für künftige Antworten. Alte Clients kennen die Schaltfläche nicht;
auch für sie bleibt die globale Wiederaufnahme bei mehrdeutigen Altbeständen
offen. Die Aufbewahrung von Markern, deren zugehörige Antwort fehlt, ist damit
nicht geklärt. Die zwei ursprünglichen Gegenbeispiele für den alten Vertrag
bleiben deshalb erwartete Fehlschläge.

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
