# SchuleSchlau: Roadmap zur Produktionsreife

**Stand der Bestandsaufnahme: 31.10.2026.** Diese Datei ist der lokale Arbeitsplan für die Weiterentwicklung von SchuleSchlau im bestehenden Repository `schulpilot`. Sie beschreibt offene Arbeiten und erforderliche Nachweise; sie ist keine Zusicherung, dass Software oder Lernwirkung fehlerfrei sein können.

## Ziel und Umgang mit dieser Roadmap

SchuleSchlau soll Kinder vor und nach der Schule altersgerecht beim Verstehen, Üben und Vorbereiten begleiten. Fotografierte Hefte, Arbeitsblätter, Arbeitshefte, Bücher und Klassenarbeiten sollen sicher verfügbar sein und zu nachvollziehbaren, fachlich passenden Lernangeboten führen. Eltern behalten Übersicht und Kontrolle, ohne jeden Lernschritt übernehmen zu müssen. Die App muss auch auf kleinen Smartphones ruhig, verständlich und zuverlässig bedienbar sein.

Die technische Grundlage besteht bereits. Diese Roadmap fordert vor allem gezielte Korrekturen, fehlende Abnahmen und einen belegbaren Übergang vom betreuten Test zu einem definierten öffentlichen Angebot. Bestehende Fähigkeiten werden nicht allein deshalb als vollständig abgenommen betrachtet, weil Code oder einzelne Tests existieren.

**Prioritäten:**

- **P0 – zuerst:** bekannte Betriebs- und Sicherheitsrisiken, Datenintegrität und Aufgaben, die andere verlässliche Tests ermöglichen.
- **P1 – Freigabe des definierten Nutzerkreises:** Qualität, Kinderschutz, Datenschutz, Bedienbarkeit und verlässlicher Betrieb im tatsächlich angebotenen Umfang.
- **P2 – vor dem jeweiligen Angebot:** breitere Lehrplanabdeckung, Offline-Funktionen, Play-Veröffentlichung oder Verkauf. Sie sind keine Voraussetzung für einen begrenzten Test, solange sie nicht versprochen oder aktiviert werden.
- **Laufend:** Regression, Aktualisierung und Überwachung nach der Freigabe.

Die Reihenfolge innerhalb der Prioritäten richtet sich nach Abhängigkeiten. Ein Punkt wird erst abgehakt, wenn Umsetzung **und** genanntes Abnahmekriterium erfüllt sind. Zu jedem abgeschlossenen Punkt gehören Datum, verantwortliche Person bzw. ausführende Instanz, betroffener Commit und ein Link auf Tests oder einen bereinigten Prüfbericht. Teilweise erledigte Punkte bleiben offen; echte Grenzen und Fehlschläge werden dokumentiert. Abhängigkeiten, erforderliche Betreiberentscheidungen und nicht zugängliche Geräte werden sichtbar gehalten.

**Arbeitsregeln:** `AGENTS.md` und die bestehende Architektur gelten weiterhin. Zuerst vorhandenen Code und den aktuellen Stand prüfen, vorhandene Nutzeränderungen erhalten und Tests mit künstlichen Daten durchführen. Echte Kinderdaten nur im Rahmen bereits ausdrücklich beauftragter konkreter Prüfungen verwenden. Keine privaten Bilder, Inhalte, Antworten, Zugangsdaten oder Schlüssel in Git, Berichte oder Logs übernehmen. Ein Test, eine Anbieterannahme oder ein Build darf nicht als sichtbare Geräteausgabe oder fachliche Wirksamkeit ausgegeben werden. Kosten, Datenschutzvorgaben und Sicherheitsgrenzen nicht stillschweigend lockern. Für die zunächst lokale Bearbeitung dieser Roadmap keine GitHub-Issues, Pushes oder Serveränderungen allein aufgrund dieser Datei ausführen.

## Arbeitsfortschritt

- 31.10.2026, Entwicklung: Neue PDF-Bestätigungen halten die explizit bestätigte Zuordnung zwischen Note und Importposition fest; gelöschte manuelle Noten mit Anfrageschlüssel erhalten eine kindgebundene, mit dem Installationsschlüssel authentifizierte Wiederholungssperre. Diese Grundlagen schließen die Noten-Restorelücke noch nicht: Altimporte sind nicht rückwirkend zugeordnet, Importkopien und Journalbelege bleiben zu bearbeiten. Die Sperren hängen vom gleichbleibenden Installationsschlüssel ab; Schlüsselrotation benötigt einen gesonderten Migrationsvertrag.
- 31.10.2026, Betrieb: Release `6e48cfe` und der zugehörige Offsite-Client sind aktiv. Sicherungen liegen auf dem 50-GB-Volume; eine neue Sicherung mit Journal, eine isolierte authentifizierte Wiederherstellung und der unabhängige Offsite-Abgleich waren erfolgreich. Nach erfolgreichem Abgleich von 2.256 Dateien wurde nur die verifizierte alte Systemplattenkopie entfernt (12.275.552.735 Bytes). Danach waren auf `/` rund 15 GiB frei; der Monitoring-Trockenlauf meldete keine Fehler. Die bekannte Notenlöschungs-/Restorelücke bleibt ungeachtet dieser erfolgreichen allgemeinen Restoreprobe offen.
- 31.10.2026, lokal: Backup- und Restore-Einstiege, Journalexport und ein neuer eingeschränkter Offsite-Leseweg nutzen die vorbereitete stabile Betriebssperre und bei konfiguriertem Volume die UUID-Prüfung. Die Systemd-Dienste erhalten Schreibzugriff auf den Sperrpfad. Dies ist noch kein produktiver Wechsel: Alter Offsite-Client und alter Server müssen koordiniert aktualisiert, Parallelität/Abbrüche und die bestehende Installation vollständig geprüft und erst danach Sicherung, Offsite und Restore auf dem Volume nachgewiesen werden.
- 31.10.2026, lokal: Für die geplante Verlagerung der Sicherungen existieren isoliert getestete Bausteine für eine vom Backup-Verzeichnis unabhängige Sperre und eine exakte Volume-Prüfung. Ein Regressionstest belegt, dass die bisherige Verzeichnissperre nach einem Pfadwechsel nicht mehr schützt. Die Bausteine sind noch nicht an Backup, Offsite und Restore angeschlossen; es gab keinen Mountwechsel und keinen produktiven Funktionstest.
- 31.10.2026, lokal: Die isolierte Wiederherstellungsprobe hält die gemeinsame Backup-Sperre jetzt über die vollständige Prüfung; lesende Zugriffe erzeugen eine fehlende Sperrdatei nicht selbst. 21 Tests und 28 Untertests bestanden. Diese Sperre liegt weiterhin im Backup-Verzeichnis und koordiniert deshalb keinen Mountwechsel oder alle manuellen Aufrufe. Die Produktivinstallation und der Backup-Pfad sind noch nicht umgestellt.
- 31.10.2026, Betrieb: Release `0870f3c` / 1.38.52+207 ist ausgeliefert; API und Worker laufen aus dem aktiven Release, das vorherige bleibt erhalten. Die tatsächlich heruntergeladene APK entspricht dem Manifest; Web-/Download-Dateien sind root-eigen und nicht fremdschreibbar. Eine getrennte Restoreprobe mit aktuellem Journal und temporärer Testdatenbank bestand; sie beweist keine Behebung des offenen Noten-Restore-Fehlers. Der Offsite-Abgleich gelang. Der vollständige CI-Lauf 41235837108 ist erfolgreich abgeschlossen. Drei überprüfte doppelte Arbeitsdateien wurden entfernt (842 MiB); der freie Platz stieg von 2,9 auf 3,7 GiB. Der lesende Abgleich fand 274 ältere Serverarchive (6,69 GiB) mit bytegleichen Offsite-Kopien, aber keine identischen Archive innerhalb des Serverbestands. Die Archive sind unterschiedliche Wiederherstellungspunkte und bleiben erhalten: Eine sichere Bereinigung braucht insbesondere abgestimmte Sperren für Sicherung, Offsite-Abgleich, Deployment und Wiederherstellung sowie eine ausdrücklich definierte Aufbewahrungsstrategie. Die Offsite-Rotation nach 14 Tagen bleibt dabei zu berücksichtigen.
- 31.10.2026, lokal: Unfertige Releaseuploads liegen nun in einem root-geschützten Staging außerhalb des von alten Bereinigungsskripten durchsuchten Releasebaums. Nach Prüfung werden sie ohne Überschreiben atomar veröffentlicht und erneut geprüft. 24 isolierte Tests einschließlich pausiertem Upload und paralleler Bereinigung bestanden. Die Zeit zwischen Veröffentlichung und Aktivierung sowie konkurrierende Deployments bleiben ohne globale Sperre offen.
- 31.10.2026, lokal: Beim ausdrücklichen Öffnen der Wiederherstellung schützt ein idempotentes Startsignal ungelesene Rückmeldungen bereits vor dem ersten bestätigten Eintrag gegen vorzeitigen Rundenabschluss. PostgreSQL: 53 Feedbacktests bestanden, zwei historische Fälle weiterhin erwartete Fehlschläge; zusätzliche Berechtigungs- und Benachrichtigungstests sowie zehn Fluttertests bestanden. Alte Clients, ACKs vor Annahme des Startsignals und späte Netzwerk-Commits bleiben offen; siehe `docs/FEEDBACK_ORDER_CONTRACT.md`.
- 31.10.2026, lokal: Die Tagesübersicht zeigt Kindern die direkt bedienbaren Tageskarten ohne ständig doppelte Schnellauswahl; diese lässt sich bei Bedarf öffnen. Der Hinweis zum Bearbeitungsstand wird einmal angezeigt, die Elternansicht bleibt erhalten. Mobile Widgettests für 320/390 Pixel und 200 % Schrift sowie Navigation und Filter bestanden; ein eigener Browser-Screenshot für diesen Teilfall fehlt noch.
- 31.10.2026, lokal: Für bereits begonnene Rückmeldungswiederherstellungen verhindert ein verspäteter regulärer ACK den vorzeitigen Abschluss mit weiteren ungelesenen Antworten. Eine möglicherweise auf einem anderen Gerät gezeigte Lösung wird als ungewiss statt als tatsächlich gesehen behandelt; belegbar unabhängige Beispiele bleiben davon ausgenommen. Der Dialog ist bei 320 × 568 und 200 % Schrift einschließlich langer Inhalte scrollbar. Je 48 synthetische Feedbacktests bestanden auf SQLite und PostgreSQL 16, dazu neun Fluttertests und die Analyse. Der Altclient-Fall vor dem ersten Recovery-ACK sowie ein erst nach Netzwerk-Timeout eintreffender Commit bleiben offene Grenzen; Details und bewusster erneuter Abgleich stehen in `docs/FEEDBACK_ORDER_CONTRACT.md`.
- 31.10.2026, lokal: Das Reparaturquellarchiv wird gegen den zur signierten APK gehörenden Commit sowie die tatsächlich hochgeladenen Bytes geprüft; eine manipulierte oder fehlende Datei und Symlinks werden abgewiesen. Die Prüfungen erfolgen vor der Aktivierung. Zusammen mit den Aktivierungsfällen bestanden 37 isolierte Tests; ein echtes Deployment ist nicht erfolgt.
- 31.10.2026, lokal: Der Webbuild von Commit `3ca1eae` gelang in einem temporären Worktree. Der nachfolgende Android-Releasebuild wurde wegen hoher Rechnerbelastung abgebrochen; ein vollständiger signierter Build und seine Prüfung stehen für den späteren, endgültigen Commit weiterhin aus. Beim Webbuild meldete das TTS-Plugin Warnungen zur künftigen WebAssembly-Kompatibilität.
- 31.10.2026, lokal: Die Aktivierung stoppt API und Worker vor dem Releasewechsel und prüft auch das Ergebnis der zweiten Sicherung nach dem Auslaufen des Workers. Bei frühen Fehlern stellt sie geänderte Dienstdateien und den optionalen TURN-Helfer wieder her; schlägt dies fehl, bleiben die Dienste gestoppt. 24 isolierte Tests mit simuliertem systemd bestanden. Eine echte systemd-/Deploymentabnahme und die unten beschriebene übergreifende Koordination stehen noch aus.
- 31.10.2026, lokal: Für aktuelle Clients ist ein ausdrücklicher Wiederherstellungsweg für mehrdeutige ungelesene Rückmeldungen ergänzt. Das Kind sieht eigene gespeicherte Antworten seitenweise ohne behauptete zeitliche Reihenfolge und quittiert nur den gewählten Marker. Mehrere Marker, parallele Bestätigungen, beschädigte Details, Trennung verschiedener Kinder, erhaltene Entwürfe und Abschluss erst nach dem letzten Marker werden synthetisch geprüft. Der Weg startet keinen KI-Auftrag; ein Rückblick bleibt bewusst anforderbar. Die historische Reihenfolge und der alte Clientvertrag bleiben offen; siehe `docs/FEEDBACK_ORDER_CONTRACT.md`.
- 31.10.2026, lokal: Der Kinder-Lernstand zeigt die Zahl geübter Aufgaben und bündelt Einzelzahlen im aufklappbaren Überblick. Fachkarten und Filter bleiben erreichbar. Im künstlichen Konto wurden im 390-×-844-Browser der Überblick geöffnet und geschlossen sowie der Wechsel vom Fach zu dessen Themen bedient; Widgettests decken auch große Schrift ab. Eine allgemeine Abnahme aller Kinderansichten steht noch aus.
- 31.10.2026, lokal: Verständnisrunden prüfen vor und nach dem Anbieteraufruf den Kinderkontostatus erneut; Hausaufgabenänderungen prüfen Sitzung und Konto nach dem Warten auf die Kind-Sperre. Künstliche Tests bestanden auf SQLite und isoliertem PostgreSQL. Die Hausaufgabentests simulieren Zustandsänderungen und beweisen keine vollständige Konkurrenzabnahme.
- 31.10.2026, lokal: Die Aufbewahrungsbereinigung protokolliert tatsächlich gelöschte abgelaufene Lernrunden im Löschjournal. Ein synthetischer Wiederherstellungstest zeigt, dass eine vorher gesicherte abgelaufene Runde durch Journalabgleich entfernt und eine aktuelle Runde erhalten wird; Wiederholung erzeugt keinen doppelten Eintrag. Je 24 Tests bestanden auf SQLite und isoliertem PostgreSQL. Die vollständige Aufbewahrungs- und Löschprüfung aller Datenarten bleibt offen.
- 31.10.2026, lokal: Schulbuddy zeigt zunächst zwei Frageideen und weitere auf Wunsch; nach Chatbeginn stehen die Vorschläge auf Abruf. Bei der künstlichen Browserprüfung mit 390 × 844 Pixeln wird eine technische Nichtverfügbarkeit für Kinder verständlich angezeigt. Der Chat war dort nicht für Modellaufrufe freigeschaltet; Vorschläge und tatsächliches Absenden wurden durch Widgettests geprüft. Wortimport- und Sprachprojektaufträge prüfen zusätzlich, dass Auftrag und Sitzung denselben Benutzer haben. Die synthetischen Fälle bestanden auf SQLite und isoliertem PostgreSQL; ein öffentlich herstellbarer Angriff wurde dabei nicht nachgewiesen.
- 31.10.2026, lokal: Die Rückmeldungsübersicht findet nach einem von ungeeigneten Gleichstandkandidaten belegten Suchfenster zusätzlich begrenzt zeitlich eindeutige ältere Rückmeldungen. Tests prüfen 33 ungeeignete neuere Einheiten, erhaltene Marker und die begrenzte Zahl von Datenbankabfragen. Zeitgleiche alte Rückmeldungen verschiedener Fragen und weitere Kandidaten außerhalb der begrenzten Fenster bleiben offen.
- 31.10.2026, lokal: Die isolierte Wiederherstellungsprobe behandelt ein fehlendes aktuelles Löschjournal nicht mehr als leeres Journal. Der Monitor lehnt ältere Erfolgsberichte ohne Nachweis der vorhandenen Journaldatei ab. Künstliche Tests prüfen fehlende und vorhandene Dateien sowie ungültige Berichte. Vorhandensein und gültige Einzelsignaturen belegen keine Vollständigkeit. Es wurde keine Serverprüfung oder produktive Wiederherstellung durchgeführt.
- 31.10.2026, lokal: Backup, Offsite-Export und Restore lesen das Löschjournal unter der stabilen Schreibersperre. Fehlende oder nicht lesbare Journale erzeugen einen gesonderten Backupstatus und Monitoralarm; eine Datenbanksicherung bleibt möglich. Die Offsite-Quittung wird an Name und Hash des übertragenen neuesten Archivs gebunden. Künstliche Tests prüfen Rotation, verschlüsselte Archive, gleichzeitige Veröffentlichung sowie ACK-Fehler; bei unklarem ACK bleibt eine Markierung für den Betreiberabgleich. Vor einem späteren Einsatz sind Serverrelease und unabhängiger Pull koordiniert zu aktualisieren. Dieser lokale Test beweist weder eine lückenlose Journalhistorie noch eine produktive Wiederherstellung.
- 31.10.2026, lokal: Für Eltern-Lernkompass-Aufträge wird die Verifikation des Kontos erneut vor und nach dem Anbieteraufruf kontrolliert; manuelle Aufträge prüfen auch das Inaktivitätslimit der Sitzung. Je 40 künstliche Fälle bestanden auf SQLite und isoliertem PostgreSQL. Dauerhafte Freigaben bleiben nach Logout wirksam, aber nicht bei Verlust der Kontoverifikation. Die allgemeine Berechtigungsabnahme bleibt offen.
- 31.10.2026, lokal: Ein eindeutig belegter Gleichstand von Versuchen derselben Frage wird bei Rückmeldungsanzeige, Wiederaufnahme und Quittierung gleich behandelt. Neue Tests berücksichtigen auch ältere und neuere Rückmeldungen anderer Einheiten; je 25 Tests bestanden auf SQLite und isoliertem PostgreSQL. Die Übersicht prüft jeweils höchstens 16 reguläre und 16 zusätzliche Gleichstandkandidaten; globale Altgleichstände verschiedener Fragen und mehrere ungelesene Altmarker bleiben offen.
- 31.10.2026, lokal: Die leere Hausaufgabenansicht verzichtet auf eine zweite Fotoaktion und nutzlose Filter; die Aktualisierung bleibt im Menü. Im echten Browser bei 390 × 844 Pixeln mit künstlichem Konto wurden Vorher/Nachher und die Aktualisierung bedient. Die Klassenarbeitsvorbereitung zeigt für Kinder die nächste Runde vor optionalen Plandetails; Widgettests decken auch schmale Ansichten mit großer Schrift ab. Die mobile Browserabnahme der Klassenarbeitsansicht steht noch aus.
- 31.10.2026, lokal: Bei der Seitenprüfung erscheinen globale und abschnittsbezogene Lesunsicherheiten vor der bewussten Bestätigung zusammen und ohne doppelte Hinweise; auch das Lesefenster erhält sie. Künstliche Tests bewahren ungewöhnliche ältere Werte und prüfen, dass die angezeigte Quelle und Bestätigung unverändert bleiben. Eine mobile Browserabnahme dieses Teilfalls steht noch aus.
- 31.10.2026, lokal: Die Kinderseite „Heute“ zeigt die nächste Lernaktion mit Fach und gegebenenfalls Elternauftrag. Herkunft, geschätzte Dauer, Lernweg und Begründung sind unter „Mehr zur Runde“ erreichbar; Plan und Hefte sind gebündelt. Im echten Webbrowser bei 390 × 844 Pixeln mit künstlichem Konto wurden Ausgangs- und Änderungsstand angesehen sowie die Rundendetails geöffnet und geschlossen. Widgettests prüfen weitere Größen und große Schrift. Die Gesamtabnahme aller Kinderseiten bleibt offen.
- 31.10.2026, lokal: Die Fach-/Themenauswahl verwendet kürzere Aufforderungen; die gewünschte Zufallsauswahl bleibt oben. Der Wörterrunden-Dialog zeigt die aktuelle Auswahl und bündelt weitere Optionen; bei 320 × 600 Pixeln und 200 % Schrift wurde ein verdeckter Startknopf behoben. Der Fotoeinstieg zeigt Zähler situationsabhängig und nennt das tatsächliche Seitenlimit. Künstliche Fluttertests prüfen Auswahl, Rückwege, Fotoabgabe und große Schrift. Diese Teile sind noch keine browsergestützte Abnahme sämtlicher Kinderansichten.
- 31.10.2026, lokal: In der Vorbereitung führt ein fehlender Auftrag direkt zu gespeicherten Runden; andere Fehler bieten zusätzlich bewusstes Nachladen. Die Rückmeldungsanzeige verwendet den zugehörigen Versuch statt des letzten Versuchs derselben Frage. Für neue Clients prüft eine fähigkeitsgebundene Neubewertung die angezeigte Versuch-ID unter Einheitensperre; Tests decken auch gleichzeitige neuere Antworten und ältere Clients ab. Die globale Reihenfolge zeitgleicher alter Antworten verschiedener Fragen bleibt offen; siehe `docs/FEEDBACK_ORDER_CONTRACT.md`.
- 31.10.2026, lokal: Die Zuordnungsaufgabe erklärt den Tippweg zuerst; ein Aufgabenraumtest bestätigt die Auswahl ohne vorzeitige Bewertung. Ein leeres Kinder-Postfach zeigt keine nutzlosen Filter, bei vorhandenen Einträgen oder aktivem Filter bleiben diese zugänglich. Weitere Tests zeigten damals drei Fälle mit zeitgleichen Rückmeldungen. Der Fall eindeutig nummerierter Versuche derselben Frage wurde inzwischen begrenzt korrigiert; die beiden globalen Altfälle bleiben als erwartete Fehlschläge offen.
- 31.10.2026, lokal: Der Wiederherstellungsmonitor erkennt fehlende, ungültige und veraltete Berichte. Ein einmaliger Initialzeitanker begrenzt die Frist für neue Installationen; die Berichtablage erfolgt atomar. Die isolierten Regressionstests einschließlich simuliertem Alarm sind in `scripts/tests/test_restore_monitor.py` dokumentiert. Kein Serverupdate und kein echter Alarmversand wurden durchgeführt.
- 31.10.2026, lokal: Die Speicherwarnung berücksichtigt nun den tatsächlich nutzbaren Platz einschließlich reservierter Dateisystemblöcke. Ein künstlicher Fall deckt ab, dass eine nach `df` über 90 % belegte Partition zuvor nicht wegen des prozentualen Grenzwerts gewarnt hätte. Speicherbereinigung, Kapazitätsplanung und echte Alarmabnahme bleiben offen.
- 31.10.2026, lokal: Die Quellenbindung der Releaseartefakte wurde im getrennten Worktree auf Commit `614f7d3` mit echtem Web-, signiertem Direct-APK- und Play-AAB-Build geprüft. Der signierte Nachweis ließ sich erfolgreich verifizieren; eine veränderte Webdatei, eine ältere signierte APK mit gleicher Versionsnummer sowie ein veränderter oder ungetrackter Quellstand wurden abgewiesen. Der Abgleich eines übertragenen Baums wurde nur synthetisch getestet; es gab kein Deployment und keinen physischen Androidtest. Spätere Änderungen erfordern einen neuen Build ihres eigenen Commits.
- 31.10.2026, lokal: Bei gleichen Zeitstempeln werden Versuche derselben Frage im Lernrückblick und weiteren fragebezogenen Auswertungen zusätzlich nach der gespeicherten Versuchsnummer sortiert. Künstliche Regressionen prüfen einen zunächst falschen und danach unterstützten richtigen Versuch. Bei identischen Zeitstempeln verschiedener Fragen wurde eine Inkonsistenz zwischen Detailansicht, Heute-Wiederaufnahme und Quittierung reproduziert. `backend/tests/test_feedback_legacy_order.py` hält den gewünschten Vertrag als strikten erwarteten Fehlschlag fest. Die Versuchsnummer gilt nur innerhalb einer Frage und belegt keine globale Reihenfolge; eine Lösung muss neue Reihenfolgen zuverlässig speichern und alte uneindeutige Fälle behandeln, ohne Rückmeldungen zu verlieren. Die allgemeine fachliche Abnahme des Lernstands bleibt offen.
- 31.10.2026, lokal: Für direkte Anbieter prüft die Kinderkostenkontrolle bei gesetztem EUR-Tages- oder Monatslimit die Aktualität des Wechselkurses vor einer neuen Reservierung. Tests decken veraltete und zukünftige Kurse, unbegrenzte Kinderlimits sowie die unveränderten globalen Grenzen und Reservierungen unbekannter Kosten ab. Eine Auswahl von 88 Lernstands-, Rückmeldungs- und Kostenfällen bestand auf einer isolierten PostgreSQL-16-Instanz; eine vollständige Betriebs- und Parallelitätsabnahme aller Kostenpfade bleibt offen.
- 31.10.2026, lokal: Seitenweite Erkennungsunsicherheiten werden bei der Lernquellenauswahl auch dann berücksichtigt, wenn zugleich lokale Abschnittshinweise vorliegen. Leere Unsicherheitshinweise bei teilweise lesbaren oder unlesbaren Seiten werden zurückgewiesen. Künstliche Tests prüfen unter anderem getrennte und lokale Hinweise, ungültige Altwerte und ausdrückliche Bestätigung; eine umfassende OCR-Qualitätsabnahme bleibt offen.
- 31.10.2026, lokal: Für neue allgemeine Lernrunden und Pakete mit gespeicherter Absenderbindung wird die Sitzung und Familienberechtigung vor und nach dem Anbieteraufruf erneut geprüft. Synthetische Widerrufs- und Mitgliedschaftstests decken auch die Behandlung tatsächlich angefallener beziehungsweise unbekannter Kosten ab. Historische Aufträge ohne Absenderbindung behalten vorerst ihr bisheriges Verhalten; die Berechtigung zum damaligen Auftrag lässt sich daraus nicht nachträglich beweisen. Der Gesamtpunkt zu Rechten und Sitzungsentzug bleibt offen.
- 31.10.2026, lokal: In der Klassenarbeitsnacharbeit werden eindeutig numerische Gleichungen nun auch erkannt, wenn ihre Terme in getrennten TeX-Abschnitten stehen. Originalantworten und Unsicherheit bleiben erhalten; unklare, beschädigte oder symbolische Terme werden nicht rechnerisch beurteilt. Künstliche Fälle bestanden auf SQLite und PostgreSQL. Dies ist keine vollständige fachliche Abnahme der Klassenarbeitsnacharbeit.
- 31.10.2026, lokal: Historische Angaben zur Anbieterroute und zu Lernminuten in `docs/AFTER_SCHOOL.md` und `docs/PROVIDERS.md` wurden von aktuellen Regeln abgegrenzt. Die tatsächliche Live-Konfiguration wurde bei dieser lokalen Bearbeitung nicht erneut geprüft. `docs/RELEASE_READINESS.md` enthält einen prüfbaren Vorschlag für Umfang und Abnahmekriterien, noch keine Freigabeentscheidung.

## Ausgangslage und Grenzen

Die Bestandsaufnahme am 31.10.2026 sah den dokumentierten Release 1.38.49+204 und einen erfolgreichen CI-Lauf für den zugehörigen Produktcode. Der synthetische Monatstest umfasste 30 simulierte Schultage und 32 Seiten; jeder Tag hatte eine abgeschlossene quellengebundene Runde. An 29 Tagen waren alle ursprünglichen Einstiegsrunden abgeschlossen, für eine fehlerhafte alte Runde wurde eine Ersatzrunde abgeschlossen. Das belegt weder alle Folgeetappen noch tägliche Mindestlernzeit oder eine langfristige Lernwirkung. Ein zusätzlicher künstlicher Live-Fotoablauf wurde im 390-Pixel-Browser durchgeführt. Aktuelle Nachweise und Einschränkungen stehen in [docs/STATUS.md](docs/STATUS.md) und [docs/EVERYDAY_QA_2026_10_30.md](docs/EVERYDAY_QA_2026_10_30.md).

Physische Android- und aktuelle sichtbare FCM-Abnahmen bleiben offen; ältere Emulatornachweise sind davon getrennt zu bewerten. Der Lehrplanbestand ist nach [docs/CURRICULUM.md](docs/CURRICULUM.md) unvollständig. Eine Prüfung der vollständigen Software durch jedes reale Kind, aller Fächer oder aller möglichen Modellantworten liegt nicht vor. Die frühere 100-Runden-Serie wurde auf Nutzerwunsch beendet und wird durch diese Roadmap nicht wieder eröffnet.

## 1. Rahmen und Freigabeumfang

- [x] **P0 – Verbindlichen Einsatzumfang und Freigabestufen festlegen**

  Festlegen, welche Nutzergruppen, Geräte, Fächer, Alters- und Klassenbereiche, KI- und Medienfunktionen beim betreuten Test, beim begrenzten Pilot und bei einer späteren breiten Freigabe tatsächlich unterstützt werden. Lehrplanabdeckung, Offline-Nutzung, Push, Familienanrufe, Play-Veröffentlichung und Verkauf nur dann als Bestandteil einer Stufe ausweisen, wenn sie dafür ausdrücklich vorgesehen sind. Verantwortlichkeiten für fachliche, technische, Datenschutz- und Betreiberfreigabe benennen.

  **Abnahme:** Eine nachvollziehbare Umfangs- und Freigabematrix nennt pro Stufe Funktionen, ausgeschlossene Fälle, erforderliche Nachweise und Entscheidungsverantwortliche. Fehlende Angaben gelten nicht als automatisch genehmigt.

  **Nachweis 31.10.2026:** `docs/RELEASE_SCOPE.md` grenzt die bestehende
  Übungsumgebung, einen möglichen begrenzten Pilot und eine spätere breite
  Freigabe ab und nennt Zuständigkeitsrollen und erforderliche Nachweise.
  Die Matrix aktiviert keinen Pilot oder Verkauf und ersetzt keine noch
  ausstehenden Entscheidungen oder externen Fachprüfungen.

- [x] **P0 – Messbare Qualitäts- und Betriebsziele definieren**

  Für die gewählte Zielgruppe vor den Tests Grenzen für kritische fachliche Fehler, unbekannte Bewertungen, Wiederherstellbarkeit, Auftragszuverlässigkeit, Wartezeit, Benachrichtigung, gleichzeitige Nutzung und Datenschutzvorfälle festlegen. Keine erfundenen Prozentwerte als bereits gemessene Leistung ausgeben; Grenzwerte müssen zum beabsichtigten Einsatz und den zur Verfügung stehenden Messungen passen.

  **Abnahme:** Jedes Ziel hat Messmethode, Testdaten, Bezugszeitraum, Grenzwert, verantwortliche Rolle und ein Vorgehen bei Nichterfüllung.

  **Nachweis 31.10.2026:** `docs/QUALITY_TARGETS.md` legt überprüfbare
  Arbeitsziele für den betreuten Übungsbetrieb fest. Die Werte sind Vorgaben,
  keine erfundenen Messergebnisse oder allgemeine Produktionsfreigabe; für
  einen größeren Pilot müssen Umfang und Stichprobengröße erneut festgelegt
  werden.

- [x] **P0 – Anforderungen, Entscheidungen und tatsächliche Anbieterroute abgleichen**

  Aktuelle Nutzeraufträge, `AGENTS.md`, dokumentierte Betreiberentscheidungen und tatsächlich eingesetzte Konfiguration zeitlich einordnen. Insbesondere den ausdrücklich beauftragten automatischen Seitenabgleich mit älteren Regeln zur manuellen Bestätigung in Einklang dokumentieren; frühere Anbieter-, Budget- und Lernzeitangaben als historische Stände kennzeichnen. Bestehende Freigaben nicht erneut anfordern und keine Live-Konfiguration allein wegen widersprüchlicher alter Dokumentation ändern.

  **Abnahme:** Eine Übersicht nennt für jeden Widerspruch die geltende spätere Entscheidung, den aktuellen Implementierungsstand und gegebenenfalls eine konkrete offene Anpassung. Mindestlernzeiten bleiben Mindestziele und sperren freiwilliges Weiterlernen nicht.

  **Nachweis 31.10.2026:** Die Übersicht
  `docs/DECISIONS_CURRENT_2026_10_31.md` ordnet die Betreiberentscheidungen zu
  Prüfmodus, Mindestzeit, Anbieter, Modellwechsel, Reservierungen, Push und
  Marke zeitlich ein. Die tatsächlichen Einstellungen wurden ohne Schlüssel
  oder Kinderinhalte lesend auf Release `484a9be` geprüft; spätere Änderungen
  erfordern einen erneuten Abgleich. Terra ist damit nicht freigegeben oder
  aktiviert und eine externe Datenschutzprüfung nicht ersetzt.


## Konkrete P0-Befunde aus der Bestandsaufnahme

- [ ] **P0 – Speicherplatz prüfen und rechtzeitig absichern**

  **31.10.2026, lokal ergänzt:** Die Systemplatte und das neue Backup-Volume
  werden getrennt betrachtet; der unabhängige Wächter prüft zusätzlich sein
  Offsite-Dateisystem. Stichtagsmessung, Reserven und ihre Grenzen stehen in
  `docs/STORAGE_AND_ALERTS.md`. Künstliche Grenzwert- und Alarmtests bestehen.
  Die produktive Übernahme auf beiden Hosts ist mit Release `1.38.56+211`
  erfolgt; tatsächlicher Spitzenbedarf und längerfristiger Wachstumstrend
  bleiben noch nachzuweisen.

  - [x] Serverprüfungen für Speicherplatz und konfigurierte Volume-UUID
    implementieren und mit künstlichen Grenzwerten sowie auf dem Zielhost im
    lesenden Trockenlauf prüfen.
  - [x] Den unabhängigen Wächter um Speicher- und Statusdateiprüfung erweitern
    und die Fehlerfälle isoliert testen.
  - [x] Beide Änderungen abgestimmt ausliefern und die produktiven Timer prüfen.

  Bei der lesenden Prüfung am 31.10.2026 zeigte das Serverdateisystem rund 92 % Belegung und etwa 3,1 GiB frei. Wachstum von Datenbank, privaten Uploads, Backups und eigenen Releases getrennt messen; den Platzbedarf für Backup, Build, Upload und Wiederherstellung berücksichtigen. Nur eindeutig entbehrliche eigene Artefakte unter Einhaltung aller Aufbewahrungsregeln bereinigen oder Speicherkapazität erweitern; keine fremden Dienste oder Daten verändern. Warn- und Eskalationsschwellen auf den tatsächlich verfügbaren Platz und den Wachstumstrend abstimmen.

  **Abnahme:** Freier Platz, erwarteter Spitzenbedarf, Zuständigkeit und Alarmweg sind dokumentiert; ein kontrollierter Test zeigt eine rechtzeitige Warnung. Eine Stichtagsmessung wird nicht als dauerhafte Kapazitätsgarantie ausgegeben.

- [ ] **P0 – Notenlöschung einschließlich Importen und Restore absichern**

  **01.11.2026, Release `1.38.57+212`:** Beim Fristablauf werden auch noch
  nicht eindeutig zugeordnete mögliche Kopien am belegten Tabellenplatz
  vorsorglich redigiert und journalisiert; andere Noten bleiben erhalten.
  Manuelle Löschungen verlangen weiterhin die Elternprüfung. Künstliche
  Restore- und Regressionstests bestehen auf beiden Datenbanken. Der reale
  Worker entfernte eine 366 Tage alte künstliche Note in einer separaten,
  gesperrten Testfamilie; mögliche Kopien wurden redigiert, eine aktuelle
  Vergleichsnote erhalten und der signierte Beleg geprüft. Die Testfamilie
  wurde anschließend regulär und journalisiert entfernt. Beschädigte Quellen,
  ältere Löschungen ohne Journal und aufbewahrte Slots bleiben offen.

  **31.10.2026, lokale Umsetzung:** Neue Löschungen und der Aufbewahrungslauf
  verwenden versionierte Journalbelege; bestätigte PDF-Positionen werden
  gezielt redigiert. Für alte, nicht sicher zuordenbare Positionen verlangt
  die Elternansicht eine ausdrückliche Entscheidung. Wiederherstellungen mit
  älteren Snapshots, Importkopien und offenen Outbox-Einträgen sind synthetisch
  geprüft. Der genaue Vertrag und seine Grenzen stehen in
  `docs/GRADE_ERASURE.md`. Seit Release `1.38.56+211` ist die Änderung aktiv;
  eine authentifizierte isolierte Restoreprobe auf dem Zielserver bestand.
  Historische Löschungen ohne Journalbeleg und ungeklärte Altzuordnungen
  bleiben gesondert nachzuweisen; dieser Punkt ist daher noch nicht abgehakt.

  - [x] Neue Notenlöschungen samt bestätigter Importkopien journalisieren und
    Wiederholung alter Anfrageschlüssel verhindern.
  - [x] Mehrdeutige Altimporte vor dem Löschen durch berechtigte Eltern
    ausdrücklich prüfen lassen.
  - [x] Schema `0044` ausliefern und einen authentifizierten isolierten Restore
    auf dem Zielserver durchführen.
  - [x] Konservative Fristbereinigung mit künstlichen Altimporten und echtem
    Worker in der Produktionsdatenbank sowie getrenntem Restore testen.
  - [ ] Historische Löschungen ohne Journalbeleg und die Aufbewahrungsfolgen
    ungeklärter Altzuordnungen abschließend nachweisen beziehungsweise klären.

  Bei der lokalen Codeprüfung am 31.10.2026 fiel eine konkrete Lücke auf:
  `grades.delete_grade` löscht die einzelne `SchoolGrade` und auditiert den
  Vorgang, erstellt aber keinen Eintrag für das externe Löschjournal. Die
  Aufbewahrungsbereinigung in `worker.maintenance` löscht alte Noten ebenfalls
  ohne solche Einzelbelege. `erasure.reconcile` unterstützt bisher keinen
  Noten-Scope. Eine ältere Sicherung kann daher einen seitdem gelöschten
  Notendatensatz bei der Wiederherstellung wieder enthalten. Auch
  `GradeSourceSlot.last_value` und `GradeImport.entries` können den Wert
  weiterhin speichern; das Löschen nur der Notenzeile ist keine vollständige
  Löschung dieser Daten. Ein kurzer lokaler Lösungsversuch nur für die
  Notenzeile wurde deshalb nicht übernommen.

  Einen vollständigen, revisions- und familiengebundenen Löschvertrag für
  einzeln gelöschte und abgelaufene Noten samt tatsächlicher Kopien in
  Importvorschauen und Quellpositionen entwickeln. Dabei die bestehende
  Kind- vor Notensperre aus dem Import einhalten, Sitzungen und Elternrechte
  nach Wartezeiten erneut prüfen und die Konsequenzen für offene Vorschauen,
  deren Kontextrevisionen, wiederholte Importbestätigungen und die sichere
  Erkennung früherer Quellpositionen festlegen. Angenommene Elternlernziele
  und andere Noten dürfen nicht mitgelöscht werden. Ein Import-Slot kann erst
  **nach** einem älteren Backup ausdrücklich mit einer bereits vorhandenen
  Note verknüpft worden sein; die dafür nötige Herkunft muss über den Restore
  hinweg belegbar bleiben. Übereinstimmende Notenwerte allein sind kein
  zuverlässiger Zuordnungsbeweis. Neue Journalinformationen dürfen keine
  privaten Inhalte enthalten; ältere Restore-Leser müssen unbekannte Formate
  sicher ablehnen und Rollback und Wiederherstellung müssen vorab geprüft sein.

  **Ursprünglicher technischer Entwurf und weiterhin offene Abnahme:**

  1. Künftige Import-Einträge erhalten versionierte, stabile, opake IDs. Für
     ausdrücklich bestätigtes `add`, `link` und `update` werden Kind, Noten-ID,
     Import-/Eintrags-ID, Quellenrevision und Verknüpfungszeitpunkt
     nachvollziehbar gebunden. Der Fuxnoten-Slot bezeichnet nur eine Position
     im Raster: Eine gleiche Position oder ein gleicher Wert in zwei
     Dokumentversionen belegt für sich keine identische Klassenleistung.
     Migration und Backfill dürfen unbelegte historische Beziehungen nicht
     erfinden; veränderte JSON-Formate benötigen einen ausdrücklich
     kompatiblen Leseweg für bestehende Web- und Android-Clients.
  2. Löschen und Aufbewahrungsbereinigung verwenden dieselbe geprüfte
     Sperrreihenfolge Kind → Note → Slot → Import wie die beteiligten
     Import-/Änderungspfade. Elternsitzung und Familienrechte werden nach dem
     Warten erneut geprüft. Eine Transaktion redigiert die nachweislich
     zugehörigen Importkopien, entfernt beziehungsweise ersetzt den Slotwert
     durch einen datensparsamen Löschmarker, löscht die Note und schreibt den
     versionierten Löschauftrag in die bestehende Outbox. Eine Schemaänderung
     für den heute verpflichtenden Slotwert und das Verhalten älterer Leser
     sind vorher zu prüfen. Fremde Noten und angenommene Elternziele bleiben
     erhalten.
  3. Löschung erhöht die betroffene Kontext-/Vorschaurevision. Ein PDF-Import
     merkt sich vor der ausgelagerten Verarbeitung die relevante Revision und
     prüft sie nach dem erneuten Kind-Lock; bei zwischenzeitlicher Löschung
     wird die alte Auswertung verworfen und eine neue ausdrückliche Aktion
     angeboten. Ein wiederholter alter Noten-Anfrageschlüssel darf gelöschte
     Daten nicht erneut anlegen. Bereits bestätigte Importwiederholungen
     bleiben deterministisch, geben keine redigierten Werte zurück und führen
     nicht zu Doppelimporten; hierfür sind datensparsame Tombstones und der
     Umgang mit alten Clients gesondert zu entwerfen.
  4. Das authentifizierte Journal benötigt einen eindeutig versionierten
     Noten-Löschbeleg mit opaker, kindgebundener Herkunft, die auch gegen
     eindeutig identifizierbare Import-Einträge eines älteren Backups geprüft
     werden kann, wenn die Verknüpfung erst nach diesem Backup erfolgte. Das
     derzeitige Outbox-Schema aus Scope und Ziel-ID reicht dafür nicht aus.
     Keine Note, Fachbezeichnung oder Freitext in den Beleg schreiben; falls
     deterministische Kennungen nötig sind, niedrig-entropische Rasterdaten
     nicht durch ungeschützte Hashes offenlegen, sondern einen getrennt
     verwahrten versionierten HMAC-Schlüssel verwenden. Schlüsselrotation und
     Verfügbarkeit während des gesamten Backupfensters sind zu prüfen.
     Unbekannte Recordversionen und fehlende Schlüssel lassen den Restore
     sicher scheitern; ältere Restore-Leser und Code-Rollback müssen vor der
     Einführung ausdrücklich geprüft werden.
  5. Nach dem Datenbankcommit wird die Outbox zuverlässig und dauerhaft ins
     Journal übertragen. Vor einer Freigabe von Backup oder Restore sind eine
     leer abgearbeitete Outbox und das aktuelle authentifizierte Journal
     nachzuweisen. Wenn nach einem Absturz weder die ausstehende Outbox noch
     ihre Übernahme belegbar ist, darf ein Restore nicht als vollständig
     löschkonform gelten. Betroffene unklare historische Daten bleiben bis zu
     einer konkreten Prüfung gesperrt; weder ganze fremde Importe automatisch
     löschen noch einzelne Beziehungen raten. Zeitablauf allein beweist keinen
     lückenlosen Cutover oder eine vollständige Journalhistorie.

  **Abnahme:** Isolierte SQLite- und PostgreSQL-Fälle prüfen berechtigte und
  fremde Familien, veraltete Revisionen, parallelen Import und Löschung,
  Wiederholungen sowie Aufbewahrungsablauf. Separate Wiederherstellungen von
  Sicherungen sowohl vor als auch nach der Slot-Verknüpfung entfernen alle
  eindeutig zugeordneten gelöschten Daten, erhalten fremde und nicht betroffene
  Daten und übernehmen keine erfundene Zuordnung. Ein fehlender oder alter
  Journal-/Restore-Leser scheitert nachweisbar sicher; offene Vorschauen und
  idempotente Wiederholungen bleiben verständlich und ohne Doppelimport.
  Die Restorefälle umfassen Backups vor dem Import, nach einer Vorschau vor
  dem Link, nach Link und Löschung, Korrekturen sowie inzwischen abgelaufene
  sieben Tage alte Vorschauen und 365 Tage alte Importbelege. Teste außerdem
  Widerruf während Sperrwartezeiten, einen zweiten gleichwertigen Noteneintrag,
  einen tatsächlich parallel ablaufenden Import, verspätete Commits,
  Prozessabbruch zwischen Outbox und Journal sowie beschädigte Signaturen und
  fehlende Schlüssel. Keine solche synthetische Probe ersetzt den gesonderten
  Nachweis des tatsächlichen produktiven Restore- und Cutover-Zustands.
  Unklare historische Beziehungen bleiben als solche dokumentiert, solange
  sie nicht ohne Datenverlust oder unzulässiges Raten auflösbar sind.

- [x] **P0 – Fehlende Wiederherstellungsberichte als Überwachungsfehler erkennen**

  `deploy/monitor.py` prüft veraltete vorhandene Berichte und einen fehlgeschlagenen Dienst, behandelt einen vollständig fehlenden Restore-Bericht aber nicht ausdrücklich als Fehler. Nach definierter Einrichtungsfrist fehlende, ungültige, unvollständige und veraltete Berichte sowie fehlgeschlagene Wiederherstellungsdienste zuverlässig erfassen. Die Behandlung einer ersten Installation vom regulären Betrieb unterscheiden und keine privaten Inhalte alarmieren.

  **Abnahme:** Automatisierte Fälle für gültig, fehlend, beschädigt, veraltet, fehlgeschlagener Dienst und Initialfrist bestehen; ein isolierter Alarmtest zeigt den erwarteten Betriebszustand.

- [x] **P0 – Web-, APK- und Backendartefakte verpflichtend an den Quellstand binden**

  `scripts/deploy.sh` und `scripts/android_manifest.py` prüfen unter anderem Version, Signierer und das separate Repair-Quellarchiv, erzwingen aber noch keinen lückenlosen Commitnachweis für die vorhandenen Web- und APK-Builds. Direkt beim Build ein überprüfbares Manifest mit sauberem Commit, Toolchain, Version und SHA-256 der relevanten Artefakte erzeugen. Deployment vor jeder Aktivierung abbrechen, wenn ein Nachweis fehlt oder Inhalt beziehungsweise Quellstand abweicht; auch tatsächliche Backendquellen und Arbeitsbaumänderungen berücksichtigen.

  **Abnahme:** Der gültige zusammengehörige Build wird akzeptiert; ein alter signierter APK-Build mit gleicher Versionsnummer, geänderte Webdateien, manipulierte Manifeste, ein abweichender Commit und ein nicht erlaubter schmutziger Arbeitsbaum werden nachweislich abgewiesen. Das ersetzt nicht die Signatur- und Versionsprüfungen.

## Lernqualität und fachliche Sicherheit

- [ ] **P1 – Fachliche Abnahmematrix aufbauen und ausführen**

  Aus den vorhandenen synthetischen Fachfällen eine versionierte Matrix nach Fach, Klassenband, Aufgabentyp, Hilfestufe und Fehlerklasse erstellen. Eine fachkundige Person bewertet unabhängig Quellenbezug, Lösung, verlangte Darstellung, Erklärung und Verständlichkeit anhand vorab festgelegter Kriterien.

  **01.11.2026, lokale Ergänzung:** Wiederkehrende längere Antwortauswahlen
  mit mehrfach gleichen Lösungen innerhalb einer neuen Sachrunde werden
  nach der Auflösung der Auswahlindizes als ungültige Ausgabe erkannt;
  die Anweisung fordert abwechslungsreiche Fragen. Kurze gemeinsame
  Kategorien bleiben möglich. Bestehende Runden und Antworten werden nicht
  umgeschrieben. Die Prüfung erkennt keine sinngleichen Umformulierungen und
  ersetzt keine fachliche Abnahme.

  **Abnahme:** Jede für den Start angebotene Kombination hat dokumentierte repräsentative Fälle, eindeutige erwartete Ergebnisse und einen Befund; kritische fachliche Fehler sind behoben und mit Regressionstest erneut geprüft. Nicht untersuchte Kombinationen bleiben sichtbar offen; eine gültige Schemaantwort gilt nicht als fachliche Abnahme.

- [x] **P1 – Bewertung und Lernfortschritt über den gesamten Lebenszyklus prüfen**

  Für richtige, falsche, unklare, unterstützte und erneut richtige Antworten sowie mehrere Runden und Geräte nachvollziehen, welche Aufgaben und Versuche gespeichert und wie sie gezählt werden. Brucherweiterung, verlangte Zähler-/Nennerdarstellung, eindeutige Faktoren, Auswahlindex und ausgeschöpfte neue Zahlenbeispiele gezielt prüfen.

  **Abnahme:** Ausgangsantworten und Hilfen bleiben erhalten, jede Aufgabe zählt genau einmal als Aufgabe und jeder Versuch als Versuch; unklare Modellurteile werden nicht als gesicherter Lernerfolg ausgegeben, und ein fehlender Beleg führt nicht zu erfundenen Aufgaben.

  **Nachweis 31.10.2026:** 115 SQLite-Fälle aus `test_practice_progress.py`,
  `test_fraction_form.py`, `test_fraction_component_assessment.py`,
  `test_recheck_attempt_binding.py`, `test_unit_fraction_practice.py` und
  `test_guided_feedback.py` bestanden. Zusammen mit 57 Coachingfällen
  bestanden dieselben 172 Fälle auf isoliertem PostgreSQL. Geprüft wurden
  insbesondere Erst-/Folgeversuche, Unterstützung, unklare Urteile,
  Bruchdarstellung und bestehende Nachweise; Modelltransporte sind simuliert.

- [ ] **P1 – Abruf und Lernplanung nachvollziehbar abnehmen**

  Mit künstlichen Quellen, Revisionen und Elternaufträgen mehrere eigenständige Prüftage über mindestens sieben simulierte Tage sowie freiwillige Zusatzrunden durchspielen.

  **01.11.2026:** Die Fälle für mindestens drei Prüftage, mehr als sieben
  Tage Abstand, neue Quellen, freiwillige Fortsetzung und konkurrierende
  Aktivitätssekunden laufen erneut auf isolierten Testdatenbanken. Diese
  automatisierten Bausteine sind keine durchgehend beobachtete mehrtägige
  Bedienungsprobe; Ergebnisse und noch fehlende Gesamtprüfung gesondert
  dokumentieren.

  **Abnahme:** Mindestens drei unabhängige selbstständige Prüftage pro Lernziel sind unterscheidbar, neue Fragen und Quellenrevisionen bleiben zugeordnet, Elternaufträge und echte Starttermine bleiben erhalten; Pausen und Zeitziele verhindern keine freiwillige Fortsetzung. Gespeicherte Aktivitätssekunden ergeben den Fortschritt ohne Doppelzählung über Geräte hinweg.

- [ ] **P1 – Sprachlernen mit Fachprüfung und echten Geräten abnehmen**

  Versionierten Sprachpfad mit ausdrücklich bestätigter Locale, Wortpaaren und Varianten prüfen; künstliche Fälle für NFC, Akzent, Artikel, unbekannte freie Sätze, Hör-/Sprechaufgaben und unterstützte Versuche aufnehmen. Auf geeigneten Geräten Berechtigungsentzug, fehlende Stimme, Abbruch und Hintergrundwechsel bedienen.

  **Abnahme:** Jede Antwort folgt der dokumentierten Modusregel, unbekannte Eingaben bleiben unklar; STT wird nicht als Aussprachebewertung oder selbstständiger Schreibbeleg gewertet und Sprache startet nur nach ausdrücklicher Aktion. Gerät, Plattform, Ergebnisse und offene Abweichungen dokumentieren.

## Fotoerkennung und Quellenprüfung

- [ ] **P1 – OCR anhand vollständig referenzierter künstlicher Seiten prüfen**

  Reproduzierbare Seiten mit Druck, künstlich erzeugter Handschrift, Formeln, Tabellen, mehreren Absätzen, Randnotizen, Zuschnitt, geringer Qualität, Zeichnungen und kurzen Notizen zusammenstellen; für jede Seite eine menschlich geprüfte Referenz und erwartete Unsicherheitsmarkierungen festhalten. Im normalen Fotoimport auf Web und Android Aufnahme/Dateiwahl, Zuschnitt, Upload, Erkennung und Wiederaufnahme ausführen.

  **Abnahme:** Alle als lesbar bewerteten Absätze und Formeln werden in richtiger Reihenfolge gegen die Referenz manuell geprüft; Abweichungen, Auslassungen und unlesbare Stellen sind einzeln dokumentiert und führen zu einer Korrektur oder offenen Einschränkung. Treffer auf wenige Textanker und eine Umfangsprüfung gelten nicht als Vollständigkeitsnachweis.

- [x] **P1 – Manuelle und automatische Seitenprüfung getrennt abnehmen**

  Pro Modus künstliche Fälle mit korrekter, fehlerhafter und unlesbarer Erstabschrift sowie technischem Gegencheckfehler prüfen; Hausaufgaben, Klassenarbeiten und Vokabelübernahme mit ihren eigenen Bestätigungsregeln einschließen.

  **Abnahme:** „Stimmt, weiter“ bestätigt im manuellen Ablauf die Quelle ohne zusätzliche Checkbox; im konfigurierten Automodus ist der separate Bild-/Abschriftgegencheck belegbar, Unsicherheit bleibt markiert und nicht belegter Stoff wird nicht bewertet. Ein technischer Fehler erscheint nicht als Erfolg, stoppt nicht fremde Seiten und löst keinen automatischen unbegrenzten Wiederholungsauftrag aus.

  **Nachweis 31.10.2026:** 66 SQLite-Fälle zu automatischer Prüfung und
  Mindestzeit (zwei PostgreSQL-only übersprungen), 86 SQLite-Fälle zu
  Prüfungsseiten und Vokabelübernahme sowie 20 mobile Widgetfälle zu Prüfmodus
  und Klassenarbeitsmaterial bestanden. Auf isoliertem PostgreSQL bestanden
  zusätzlich 141 Fälle einschließlich der Seitenprüfung und
  Vorbereitungs-/Quellrevisionstests. Die Anbieterantworten sind künstlich;
  das ist kein Nachweis vollständiger OCR-Erkennung auf echten Geräten.

- [x] **P1 – Quellenänderung und Unterbrechung sicher fortsetzen**

  Im isolierten Test Fotoabgabe, einzelne Seitenreservierungen, Netzverlust, Reload, Mitternachtswechsel, Quellkorrektur, Löschung und widerrufene Sitzung vor und nach Provideraufrufen auslösen.

  **Abnahme:** Reine Status-GETs erzeugen keine Jobs oder Kosten; jede Seite wird einzeln reserviert und dauerhaft gespeichert, eine geänderte Quelle wird revisionsgebunden erneut geprüft und historische Antworten bleiben erhalten. Nicht lesbare oder nicht bestätigte Seiten können bewusst zurückgestellt werden.

  **Nachweis 31.10.2026:** 72 SQLite-Fälle aus `test_school_preparation.py`,
  `test_school_preparation_parts.py`, `test_source_cleanup.py` und
  `test_source_lineage.py` bestanden; ein echter Sperrparallelitätsfall wurde
  unter SQLite ausgelassen und im 141-Fälle-PostgreSQL-Lauf ausgeführt.
  Unter anderem wurden unterbrochene Aufträge, GETs ohne neue Kosten,
  Mitternacht, Quellenwechsel, widerrufene Sitzungen und gespeicherte
  Antworten mit künstlichen Daten geprüft.

- [x] **P1 – Vokabelvorschau und Materialgrenzen kontrollieren**

  Künstliche Paare mit fehlender Bedeutung, mehreren Spalten und nachträglich korrigierter OCR durch Vorschau, Auswahl und erneuten Import führen.

  **Abnahme:** Paare sind anfangs abgewählt und einzeln editierbar; „Nur Heftseite speichern“ importiert keine Wörter, nur markierte Paare werden atomar und idempotent übernommen, und ein zweites Gerät erzeugt keine Duplikate oder stillen Wörterbuchergänzungen.

  **Nachweis 31.10.2026:** `test_material_vocabulary.py`: je 17 Tests auf
  SQLite und isoliertem PostgreSQL, einschließlich fehlender Übersetzung,
  Mehrspaltenzuordnung, Quellrevision, Berechtigungen und paralleler
  Bestätigung. `material_confirm_next_141_test.dart`: 25 Widgettests,
  einschließlich zunächst abgewähltem und einzeln korrigiertem Wortpaar,
  expliziter Auswahl und „Nur Heftseite speichern“. Die Tests verwenden
  künstliche Daten und simulieren mehrere Sitzungen; sie sind keine native
  Geräteabnahme.

## Lehrplan, Hausaufgaben, Tutor und Prüfungen

- [ ] **P1 – Lehrplanabdeckung fachlich kuratieren und offen ausweisen**

  Den Stand von `docs/CURRICULUM.md` und den versionierten Quelldateien gegen aktuelle amtliche Dokumente prüfen, fehlende Schulformen/Klassenbänder und ungeprüfte Fassungen priorisieren, Fachzuordnung und Fundstelle jeweils fachlich freigeben.

  **Abnahme:** Jede veröffentlichte Zuordnung hat Quelle, Fassung, Geltungsbereich und Prüfergebnis; fehlende Abdeckung bleibt als solche sichtbar. Lehrplanüberschriften dienen nur als Orientierung und ersetzen weder bestätigten Heftstoff noch eine Antwortquelle; Schulstufe und Sprachlernjahr werden nicht gleichgesetzt.

- [x] **P1 – Hausaufgabenhilfe gegen Lösungsverrat und falsche Sicherheit prüfen**

  Mit einem fachlich bewerteten künstlichen Korpus Schritte „Verstehen → selbst versuchen → gestuft helfen → eigenen Weg prüfen“ einschließlich Mehrdeutigkeiten, falscher eigener Antworten und Wiederaufnahme durchführen.

  **Abnahme:** Gespeicherte Hinweisstufen werden nachvollziehbar wiederverwendet, unbekannte Aufgaben werden nachgefragt und bekannte Lösungen nicht vorweggenommen; deterministische Rechenprüfungen und beratende KI-Rückmeldungen sind unterscheidbar. Für freie Modellantworten verbleibt eine dokumentierte manuelle Stichprobenprüfung, da lokale Regeln keinen allgemeinen Lösungsverrat ausschließen.

  **Nachweis 31.10.2026:** `test_homework.py`, `test_homework_context.py`,
  `test_homework_feedback.py` und `test_homework_session_recheck.py` prüfen
  künstliche Aufgaben, drei Hinweisstufen, Wiederaufnahme, Mehrdeutigkeit,
  fehlerhafte Schülerantworten, Lösungsverrat bei bekannten Mustern sowie
  Rechte- und Quellenwechsel. Zusammen mit den Tutor-/Quellzitatfällen liefen
  146 Fälle auf SQLite (zwei PostgreSQL-only übersprungen) und 148 auf
  isoliertem PostgreSQL. Modelltransporte sind dabei simuliert; offene freie
  Modellantworten benötigen weiterhin fachliche Stichproben und sind dadurch
  nicht allgemein gegen Lösungsverrat bewiesen.

- [x] **P1 – Hefttutor und Rückblick gegen Quellen- und Kontextwechsel testen**

  Eigene bestätigte Quellen, knappe Zitate, aktive/pausierte/abgeschlossene Einheiten, Entzug der Sitzung, Löschung und konkurrierende Geräte prüfen.

  **Abnahme:** Antworten bleiben an berechtigte Quellen gebunden; nach geändertem Kontext wird keine alte Providerantwort gespeichert. Hilfe zählt nur für passende aktive oder pausierte Einheiten, ältere Antworten bleiben unverändert. Rückblick und gezielte Anschlussübung sind getrennte Aufträge; ein Generatorfehler löscht weder fertigen Bericht noch Antworten.

  **Nachweis 31.10.2026:** Der künstliche Tutor-/Hausaufgaben-/Zitatlauf
  bestand mit 146 SQLite-Fällen (zwei PostgreSQL-only ausgelassen) und 148
  Fällen auf isoliertem PostgreSQL. Weitere 57 SQLite- und zusammen 172
  PostgreSQL-Fälle schließen getrennten Rückblick und Anschlussgenerator,
  Fehlererhalt, Quellenwechsel und Parallelität ein. Providertransporte waren
  simuliert; daraus folgt keine allgemeine Qualitätsaussage über freie
  Modellantworten.

- [ ] **P1 – Klassenarbeitsvorbereitung und Nacharbeit fachlich abnehmen**

  Künstliche Arbeiten mit mehreren Themen, optionalem Termin, individuell vorgegebenen Aufgabenzahlen je Lerntag, geänderten Plänen, unklarer Lehrkraftzuordnung und schriftlichen Altantworten testen.

  **Abnahme:** Jede Runde wird einzeln bewusst vorbereitet, enthält höchstens fünf Aufgaben und vermeidet gespeicherte Wiederholungen; Zeitangaben bleiben Empfehlungen. Aufgabenauszüge belegen die Originalzeile, trennen alte Antwort, gesicherte Lehrkraft-Rückmeldung und KI-Vorschlag und behaupten weder Vollständigkeit noch Benotung. Alte Antworten erzeugen keine Attempts oder Kompetenznachweise.

- [x] **P1 – Schul- und Klassenkontext als Produktentscheidung klären**

  Prüfen, ob neben dem bestehenden familiengebundenen Schulprofil überhaupt eine gemeinsame Klassen-/Lehrkraftfunktion benötigt und rechtlich freigegeben ist. Vor einer Umsetzung Rollen, Datenflüsse, Einwilligungen, Mandantentrennung und Zuständigkeit schriftlich festlegen; kein Zugriff aus Klassenname oder Lehrkraftbehauptung ableiten.

  **Abnahme:** Entweder eine ausdrücklich begründete Nichtaufnahme oder ein freigegebenes Konzept mit Rechte- und Löschmatrix, Pilotgrenzen und Testfällen liegt vor; bis dahin keine bestehende Klassenraumfunktion oder Schulfreigabe behaupten.

  **Entscheidung 31.10.2026:** Gemeinsame Klassen- und Lehrkraftzugänge sind
  nicht Bestandteil des derzeitigen Übungsumfangs. Der Zweck ist die
  familiengebundene Lernbegleitung; Klassenname oder Schulform begründen
  keinen Zugriff Dritter. Voraussetzungen für eine spätere gesonderte Aufnahme
  stehen in `docs/RELEASE_SCOPE.md`. Bestehende Familienrechte bleiben gleich.

## Kindgerechte Bedienung und Alltagstest

- [ ] **P1 – Alle Kinderansichten sprachlich und in ihrer Bedienung entrümpeln**

  Heute, Lernen, Fach- und Themenlisten, Hefte und Fotoimport, Seitenprüfung, Lernvorbereitung, Lernrunde und Rückblick, Wortschatz, Klassenarbeiten, Schulbuddy, Benachrichtigungen und Einstellungen jeweils in typischen Zuständen auf einem schmalen Smartphone durchgehen. Pro Ansicht die nächste Handlung erkennbar machen, wiederholte Erklärungen entfernen, vertraute kurze Begriffe verwenden und selten benötigte Einzelheiten sinnvoll erreichbar bündeln. Pflichtaufträge, Unsicherheiten, Datenschutzinformationen, Fehler und sichere Rückwege müssen weiterhin verständlich auffindbar sein. Große Schrift, Tastatur, Screenreader, leere Zustände, laufende Verarbeitung und Wiederaufnahme mitprüfen.

  **Abnahme:** Für jede genannte Ansicht sind konkrete Vorher-/Nachher-Befunde, mobile Screenshots und passende Interaktions- beziehungsweise Regressionstests dokumentiert. Die wichtigsten Aufgaben werden mit künstlichen Konten tatsächlich bedient; zusammengeklappte Informationen und Nebenaktionen bleiben erreichbar. Eine einzelne verbesserte Seite oder ein Widgettest ersetzt nicht die Abnahme des gesamten Kinderbereichs.

- [ ] **P1 – Alters- und situationsgerechte Bedienung beobachten**

  Für unterschiedliche bestätigte Klassen-/Altersgruppen repräsentative Aufgaben in schmalem Smartphone-Web, großem Web und auf Android mit künstlichem Material durchführen; fachlich und datenschutzrechtlich geeignete begleitete Nutzertests separat planen und freigeben.

  **Abnahme:** Dokumentierte Personen können Fotoabgabe, Unsicherheit prüfen, eine Runde bearbeiten, Hilfe nutzen, Rückmeldung lesen und Ergebnis erreichen; Schwierigkeiten und Abbrüche werden erfasst und behoben oder als offene Einschränkung geführt. Keine Wirksamkeit oder generelle Altersfreigabe aus Screenshots oder einer einzelnen Beobachtung ableiten.

- [ ] **P1 – Barrierearme mobile Führung nachweisen**

  Tastatur, Screenreader-Semantik, Fokus, große Schrift, Kontrast anhand tatsächlich gerenderter Farben und Trefferflächen prüfen; zusätzlich den echten Web-Runner für Zeitformatierung und reale Android-Geräte für Interaktionen verwenden.

  **Abnahme:** Die nächste Hauptaktion bleibt sichtbar und erreichbar, Feedback bleibt bis zur bewussten Fortsetzung stehen, Tastatur und Navigation verdecken keine Aktion; normale Texte erreichen mindestens 4,5:1 und notwendige Kontrollmerkmale 3:1. Geräte, Schriftgröße, Messungen und offene Befunde dokumentieren; Farbtests allein sind keine vollständige WCAG-Abnahme.

- [ ] **P1 – 30-Schultage-Test als reproduzierbaren Regressionstest fortführen**

  Der in `docs/EVERYDAY_QA_2026_10_30.md` beschriebene isolierte Test dokumentiert bereits 30 Schultage und 32 künstliche Materialseiten; er belegt keine tägliche Mindestzeit, vollständige Lehrplanabdeckung oder langfristige Lernwirkung. Für den nächsten Release einen eigenen Testplan mit festem Code-/Konfigurationsstand, künstlichen Familien und Fotos, isolierter Datenbank und Testuhr erstellen. Pro Tag Quelle, Plan, ausdrücklich gestartete Runde, Antwort-/Hilfestatus, Fehler, Provideraufträge und bekannte/unbekannte Kosten erfassen; Ferien, Fehl- und Nachholtage, Mitternacht, Netzverlust, Quellrevision, Mehrgeräte und freiwillige Fortsetzung einplanen.

  **Abnahme:** 30 einzeln belegte Testtage sind auswertbar, alle kritischen Abweichungen behoben und erneut getestet; ausgefallene Tage und nicht geprüfte Fälle bleiben ausdrücklich offen. Keine echten Kinderantworten oder Produktionszeit manipulieren.

## Betrieb, Sicherheit und Datenschutz

Die folgenden Punkte beschreiben ausstehende, wiederholbare Betriebs- und Freigabearbeiten; bestehende Betreiberentscheidungen werden nicht erneut angefragt. Maßgeblich für den jeweils tatsächlich ausgelieferten Stand ist `docs/STATUS.md`, für Sicherung und Rückweg `docs/OPERATIONS.md`. Der dort zuletzt dokumentierte Release 1.38.49+204 vom 30.10.2026 hatte eine erfolgreiche vollständige CI; ein historischer Befund ist kein Nachweis für spätere Änderungen.

- [x] **P0 – Installation und Zugriffe vor dem Ausbau überprüfen**

  Bestandsaufnahme von Diensten, Caddy, Datenbank, Worker, gespeicherten Anbieter- und Pushfreigaben und deren Revisionen durchführen; nur notwendige projektbezogene Änderungen planen.

  **Abnahme:** Istzustand, Zuständigkeit und Rückweg ohne Zugangsdaten dokumentiert sind und andere Dienste unverändert bleiben. Leere Neuinstallationen müssen einmaligen Setupcode, kurzlebiges HttpOnly-Cookie und genau einen Erstadmin auch bei parallelen Anfragen nachweisen; bestehende Familien dürfen den Assistenten nicht erneut öffnen.

  **Nachweis 01.11.2026:** Je 25 isolierte SQLite-/PostgreSQL-Fälle aus
  `test_installation.py` und `test_public_privacy.py` bestanden, darunter
  paralleler Erstabschluss, abgelaufene Cookies und bestehende Familien.
  Der Zielserver meldet Schema `0044`, abgeschlossene Einrichtung (Revision 6),
  OpenRouter (Konfigurationsrevision 37, Datenschutzfreigabe aktiv), aktivierte
  Google-Anmeldung und erteilte Push-Betreiberfreigabe. API, Worker,
  Sicherungs- und Überwachungstimer sind aktiv. Das isolierte Restore bestand;
  Zuständigkeit und migrationsbewusster Rückweg stehen in `docs/OPERATIONS.md`.
  Keine Zugangsdaten oder Inhalte der verschlüsselten Einstellungen ausgegeben.
- [x] **P1 – Berechtigung und Sitzungsentzug als wiederkehrende Freigabeprüfung ausführen**

  Eltern-, Kinder- und Adminrollen auf eigene und fremde Familien, private Uploads, Noten, Export und Löschung sowie abgelaufene/widerrufene Sitzungen prüfen.

  **Abnahme:** die API Rechte aus der Sitzung ableitet, fremde Inhalte und Adminzugriffe auf private Inhalte abweist und Entzüge auch laufende Vorgänge vor und nach externen Aufrufen erfassen. Adminlogin behält Passwort, Rate Limits, eintägige widerrufbare Sitzung und Audit; keine öffentliche Registrierung.

  **Nachweis 01.11.2026:** Die gezielte Freigabeprüfung aus
  `test_accounts.py`, `test_admin_users.py`, `test_admin_user_races.py`,
  `test_integrity.py`, `test_study_authority.py`,
  `test_schulbuddy_scope_safety.py` und `test_homework_session_recheck.py`
  bestand mit 90 Fällen und vier SQLite-Auslassungen sowie mit allen 94 Fällen
  auf isoliertem PostgreSQL. `test_source_reading.py` bestand zusätzlich mit
  je sieben Fällen, einschließlich privater Originalbilder und Adminsperre.
  Die ebenfalls auf beiden Datenbanken bestandenen Noten- und Providerprüfungen
  decken Elternexport, fremde Familien, Adminlogin und Sperren ab. Diese
  automatisierte Freigabeprüfung ersetzt keinen unabhängigen Sicherheitstest.
- [ ] **P1 – Datenlebenszyklus und Löschung pro Datenart prüfen**

  Aufbewahrung, Export und Löschkaskaden für Quellen samt Tutor-Zitaten, Fotos, Antworten, Wortschatz, Noten/Importbelege, Nachrichten und Zahlungsbelege gegen die jeweiligen Verträge prüfen.

  **Abnahme:** berechtigte Familien vollständig exportieren/löschen können, Aufbewahrungsfristen und gesetzliche Ausnahmen dokumentiert sind, Roh-PDFs nicht gespeichert werden und private Inhalte oder Schlüssel weder in Logs noch Git oder frei zugänglichen Uploads erscheinen.
- [ ] **P0 – Wiederherstellung praktisch üben**

  Verschlüsselte Sicherung in eine separate Datenbank einspielen, aktuelles authentifiziertes Löschjournal und Rechteänderungen abgleichen, alte Sitzungen und Einladungs-/Reset-Tokens widerrufen sowie Verbrauch und Aufbewahrungsfristen prüfen.

  **Abnahme:** Datenintegrität, Löschabgleich, zulässige Backup-Aufbewahrung von höchstens 14 Tagen, getrennte Geheimnisse und eine dokumentierte Entscheidung zur möglichen Journallücke nachgewiesen sind; keine automatische produktive Rücksicherung.
- [ ] **P0 – Überwachung und Störungsablauf prüfen**

  **31.10.2026, lokal ergänzt:** Beschädigte und zukünftige Offsite-Marker
  führen im unabhängigen Wächter zu einem neutralen Fehler statt zu einem
  Programmabbruch. Getrennte Speicheralarme und simulierte Benachrichtigungen
  werden künstlich geprüft; der Ablauf ist in `docs/STORAGE_AND_ALERTS.md`
  dokumentiert. Die Auslieferung ist erfolgt; eine unabhängige Prüfung der
  tatsächlichen Alarmzustellung steht noch aus.

  - [x] Beschädigte oder ungültige Offsite-Erfolgsstände als neutrale Störung
    behandeln und die Erkennung isoliert prüfen.
  - [ ] Installierte Überwachung, unabhängigen Alarmweg und Störungsablauf im
    freigegebenen Betriebsumfang abnehmen.

  Bestehende Checks für API, Worker, festhängende Jobs, Lösch-Outbox, Backups, Speicher, öffentliche Erreichbarkeit und Offsite-Frische sowie zuständige Alarmwege kontrollieren.

  **Abnahme:** ein isolierter, ausdrücklich autorisierter Test die Erkennung und Zuordnung einer Störung belegt, Meldungen keine privaten Inhalte enthalten und Runbook, Eskalation und Wiederanlauf aktuell sind.
- [ ] **P1 – Anbieter- und Kostenkontrollen revisionsgebunden nachweisen**

  Tatsächlich aktive Konfiguration und spätere dokumentierte Betreiberentscheidungen prüfen (`docs/APPROVALS.md`, `docs/STATUS.md`); historische Standards nicht als aktuelle Einstellung behandeln. Mit ausschließlich freigegebenen künstlichen Vorlagen den regulären Ablauf und atomare Reservierung bei Erfolg, Fehler, Parallelität und Widerruf testen.

  **01.11.2026:** Der Zielserver verwendet OpenRouter, Konfigurationsrevision
  37, mit aktiver Datenschutzfreigabe. Je 120 SQLite-/PostgreSQL-Fälle zu
  Grenzen, Reservierungen und Anbietervalidierung sowie je 50 Fälle zu
  Modellrouting, Codex-Adapter und Ausgaberahmen bestanden mit künstlichen
  Transporten. Unbekannte Kosten behalten die Reservierung, parallele
  Ansprüche und fehlende Gebührenbelege werden geprüft. Ein aktueller echter
  künstlicher Providerlauf für die aktive Revision bleibt separat zu belegen;
  simulierte Transporte belegen keine Erreichbarkeit des Anbieters.

  **Abnahme:** feste Adapter/Upstreams, Schema- und Quellenprüfung, Grenzen, Audit, ehrliche unbekannte Kosten und Verzicht auf automatische Providerwechsel oder Wiederholungen belegbar sind; Konfiguration und Freigaben werden nicht still gelockert.
- [ ] **P1 – Google- und Geheimnisbetrieb überprüfen**

  OIDC-State, Nonce, serverseitiges PKCE, Cookie-Webfluss, native Geräte-Proof-/Callback-Ticket-Bindung, ausdrückliche Kontoverknüpfung und zusätzliche Mailbestätigung bei Bedarf prüfen.

  **Abnahme:** keine automatische Verknüpfung nach E-Mail möglich ist, öffentliche Datenschutzerklärung und Inhabernachweis beim Deployment erhalten bleiben und private Clients, Dienstkonten und Signierschlüssel außerhalb von Git und Builds bleiben.

## Release, Android und Benachrichtigungen

- [ ] **P0 – Jeden Release aus einem nachvollziehbaren Quellstand herstellen**

  Passende Backendtests einschließlich isoliertem PostgreSQL, Fluttertests, Analyse und Webbuild sowie `scripts/build_release.sh` mit fixierter Toolchain ausführen; Diff und Geheimnisse prüfen.

  **Abnahme:** Ergebnisse und Fehler mit Commit, Toolchain und Artefakten dokumentiert sind, signierte Direct-APK und Play-AAB dieselbe beabsichtigte Version tragen und Paket, Signierer, Nicht-Debug-Status, 16-KB-Ausrichtung und AAB validiert sind.
- [ ] **P0 – Deployment und Rückkehr belegen**

  Betroffene Konfigurationen und Daten vorher sichern, Migrations- und Rückwärtskompatibilität prüfen, nur SCHULPILOT aktualisieren und vorheriges Release erhalten.

  **Noch offen – parallele Betriebsabläufe:** Zwei gleichzeitige Deployments oder ein manueller Rückweg dürfen sich bei Upload, Aktivierung, Caddy, Dienstdateien, Anbieterworker und Releasezeigern nicht überlagern. Insbesondere darf `prune_releases.py` kein gerade übertragenes, noch nicht aktives Release entfernen. Die Sperre muss auch bei SSH-Abbruch oder beendetem Koordinator erhalten bleiben, solange ein untergeordneter Upload oder ein anderer verändernder Prozess noch läuft. Eine bloß über eine SSH-Verbindung gehaltene Lease genügt dafür nicht. Zeitgesteuerte Backup-, Monitor- und Wiederherstellungsdienste sowie manuelle Aktivierung und Bereinigung in die Koordination einbeziehen. Übergangsweise beachten, dass alte installierte Skripte eine neue Sperre noch nicht kennen.

  **Zusätzliche Tests:** Zwei synthetische Deployments mit künstlich pausiertem Upload und paralleler Bereinigung ausführen; dazu SSH während Upload und Aktivierung unterbrechen, den Kindprozess verzögert beenden und prüfen, dass kein zweiter verändernder Ablauf oder prune das laufende Staging beeinträchtigt. Frühe und späte Fehler, Timerläufe sowie einen manuellen Rückweg unter demselben Vertrag prüfen. Keine Tests gegen Produktion ausführen.

  **Abnahme:** HTTPS/Health den erwarteten Quellstand zeigen, Web-Direktlinks und anonyme Schutzgrenzen geprüft sind, öffentlich ausgelieferte APK und Manifest aus tatsächlicher Datei zu Größe/Hash/Version passen und ein migrationsbewusster Rückweg dokumentiert ist.
- [ ] **P1 – Direct- und Play-Update getrennt abnehmen**

  Für Direct höhere Version auf fester HTTPS-Quelle bei Kaltstart und Wiederaufnahme prüfen; Größen-, Hash-, Paket- und Signaturabweichungen ablehnen und Android-Installationsbestätigung beobachten.

  **Abnahme:** gültiges Update mit erhaltenem Konto und Daten funktioniert, fehlerhafte Downloads nicht installiert werden und das Play-AAB ausschließlich den Play-Updateweg ohne APK-Installerberechtigung enthält. Ein gebautes AAB ist kein Play-Upload oder veröffentlichter Storeeintrag.
- [ ] **P1 – Physische Android-Abnahme nachholen**

  Auf Nutzerwunsch derzeit zurückgestellt; sie bleibt für eine belastbare Produktions-/Gerätefreigabe erforderlich und wird durch Emulator, Build oder API-Antwort nicht ersetzt. Mit eigenem Gerät und künstlichem Material Kamera/Fotozuschnitt, Tastatur, Netzverlust, Speicherknappheit, Hintergrund/Rückkehr, Appneustart, Update und Barrierefreiheit einschließlich großer Schrift und TalkBack tatsächlich bedienen.

  **Abnahme:** Gerät/Androidversion, konkrete Abläufe, Beobachtungen, Fehler und Korrekturen dokumentiert und Testdaten regulär bereinigt sind.
- [ ] **P1 – Benachrichtigungen auf echtem Gerät sichtbar prüfen**

  Im bestehenden Firebase-Projekt ausschließlich eigene künstliche Konten mit zeitlich begrenzter Testfreigabe verwenden; Elternfreigabe, ausdrückliches Geräte-Opt-in, Kanal-/Betriebssystemberechtigung, Ruhezeiten und Widerruf kontrollieren. Vordergrundanzeige sowie einen Versand nach nachgewiesenem Android-Hintergrundzustand beobachten, geschützten Zielaufruf prüfen und Registrierungen bereinigen.

  **Abnahme:** sichtbare Anzeige und Ziel tatsächlich dokumentiert sind; FCM-Annahme oder Validierung allein reichen nicht. In-App-Neuigkeiten bleiben ohne Push nutzbar.
- [ ] **P1 – Web und native Freigabe vollständig bedienen**

  Auf kleinen und breiten Ansichten regulären Fotoimport samt Blob-Lesezugriff und Zuschnitt, Anmeldung/Link-Kaltstart, wichtige Lernwege und Logout prüfen; sichtbare Tastatur, Fokus, Kontrast und große Schrift einbeziehen.

  **Abnahme:** reale Browser- und bei Verfügbarkeit Gerätebeobachtungen mit den vorhandenen automatisierten Prüfungen übereinstimmen und offene Lücken ausdrücklich benannt sind.

## Kapazität und öffentlicher Start

- [ ] **P1 – Kapazitätsannahmen vor wachsendem Betrieb messen**

  Auf isolierter, produktionsähnlicher PostgreSQL-Umgebung mit künstlichen Daten gleichzeitig aktive Sitzungen, Uploads, Listen, Jobreservierungen und Worker-Warteschlangen stufenweise prüfen; keine unautorisierten bezahlten Anbieteraufrufe auslösen.

  **Abnahme:** Testprofil, Parallelität, Laufzeit, Fehler, p95-Latenz, Warteschlangentiefe, Ressourcen und Engpass samt Messzeitpunkt dokumentiert sind, realistische Betriebsgrenzen und Alarmwerte daraus abgeleitet und relevante Sperren/Idempotenz unter Konkurrenz bestätigt sind. Ohne Messung keine Nutzerzahl oder Skalierungszusage behaupten.
- [ ] **P2 – Verkauf nur mit echten vollständigen Angaben freischalten**

  Betreiberanschrift, Support, Kontoinhaber, IBAN, Steuerbehandlung, Vertrags-/Widerrufsfassung und E-Mail-Zustellung vom Betreiber klären und konfigurieren; Sperre bis dahin erhalten. Mit künstlichen Bestellungen wiederholte und parallele Anfragen, unveränderliche Preis-/Bank-/Vertrags-Snapshots, manuelle Bankprüfung, Laufzeit, Verlängerung und Erstattung prüfen.

  **Abnahme:** nur tatsächlich dokumentierter Zahlungseingang genau einmal freischaltet und Kinder-, Demo- und Play-Zugänge keine Käufe bewerben. `docs/STORE.md` und `docs/PAYMENTS.md` sind maßgeblich.
- [ ] **P2 – Play-Veröffentlichung gesondert vorbereiten**

  Tatsächliche Play-Console-Berechtigung, Paket-/Signieridentität, Storeangaben, Datenschutz-/Zielgruppenangaben und passenden Testkanal prüfen; erforderliche Betreiberinformationen vervollständigen.

  **Abnahme:** Upload und Freigabestatus in der Konsole und der tatsächliche Installations-/Updateweg dokumentiert sind; bis dahin keine Play-Verfügbarkeit behaupten.
- [ ] **P1 – Begleitete Nutzung und Startentscheidung dokumentieren**

  Nach den einschlägigen Sicherheits-, Betriebs- und Geräteprüfungen eine ausdrücklich vereinbarte kleine Familienrunde durchführen; echte Materialien nur im konkret freigegebenen Umfang verwenden. Kinderführung, Quellenrichtigkeit, Umgang mit Unsicherheit, Elternverständnis und Support beobachten, ohne Erfolg oder Notenverbesserung zu versprechen.

  **Abnahme:** bekannte Blocker, Zuständigkeiten und Ergebnisse samt Grenzen dokumentiert sind und der Betreiber über den jeweiligen Startumfang informiert entscheiden kann; bestehende gesonderte Push- und KI-Freigaben bleiben erhalten.

## KI-Verarbeitung, Referenzen und Darstellung

- [ ] **P1 – Gesamte Verarbeitungskette durchgängig nachvollziehbar machen**

  Upload, einzelne Quellrevision, Erkennung, gegebenenfalls Gegenprüfung, Themen-/Lernzielzuordnung, Referenzsuche, Erstellung, Schema-/Fachprüfung, Speicherung, Darstellung und Bewertung anhand künstlicher Daten verfolgen. Für jede Phase Auftragskennung, Status, Revisions- und Modell-/Vorlagenversion sowie datensparsame Fehlerkategorie verfügbar machen; weder Kindertexte noch Bilder oder Geheimnisse protokollieren. Fehlerhaft gespeicherte oder unpassende Ergebnisse dürfen nicht als bereit angezeigt werden.

  **Abnahme:** Ein künstlicher Erfolgsfall und je ein reproduzierbarer Fehler pro relevanter Phase sind vom berechtigten Betriebs- beziehungsweise Familienkontext nachvollziehbar; GET-Abfragen starten keine KI und ändern keinen Lernstand.

- [ ] **P1 – Ausgabelängen, Schemafehler und Providerstörungen systematisch behandeln**

  Lange Quellen und mehrseitige Pakete mit festgelegten Größen stufenweise und quellgebunden verarbeiten; zulässige Auftrags- und Tokenbudgets sowie Reservierungen vor jedem Schritt prüfen. Abgeschnittene Antworten, fehlerhafte Schemata, 400/429/5xx, Zeitüberschreitungen und Worker-Neustarts in isolierten Tests auslösen. Unvollständige Ergebnisse nicht als vollständig übernehmen; bereits gespeicherte Teilergebnisse und Antworten sichern, verständlichen Status und einen begrenzten, bewusst gestarteten Wiederholungsweg anbieten. Keine automatischen Providerwechsel oder unbegrenzten Wiederholungen einführen.

  **Abnahme:** Mehrseitenfall und Fehlermatrix belegen eindeutige Phasenzuordnung, normale Kosten-/Versuchsgrenzen, keine Doppelaufträge und sichere Fortsetzung; zusätzlich mit künstlichen Inhalten echte freigegebene Anbieteraufrufe durchführen und deren Umfang, Kosten und Restrisiken dokumentieren.

- [ ] **P1 – Referenzdatenbank und Medienauswahl wirksam prüfen**

  Vorhandene Fach-, Themen-, Klassen- und Kompetenzzuordnungen sowie Versionen der Referenzen überprüfen. Für repräsentative Erklärungen nachvollziehen, welche Vorlagen und tatsächlich vorhandenen Medien ausgewählt, an die KI übergeben, parametrisiert und bis ins Frontend transportiert werden. Fehlende Treffer und ungültige Zuordnungen unterscheiden; Medien nur mit gültigen erlaubten Verweisen und tatsächlichen Metadaten anzeigen. Weitere Referenzen versioniert ergänzen, keine Videos erfinden und keinen KI-Aufruf durch bloßes Listen auslösen.

  **Abnahme:** Für mehrere Fächer zeigen Testbelege Auswahl, Referenz-ID/-Version und sichtbare Ausgabe; fehlende, veraltete und fachfremde Treffer führen zu einem erkennbaren sicheren Verhalten. Ein Videoklick erzeugt weder Lernzeit noch Kompetenznachweis.

- [ ] **P1 – Erklärgrafiken und Animationen fachlich und technisch abnehmen**

  Für den vereinbarten Startumfang jeden Erklärungsschritt auf eine fachlich passende Grafik prüfen. Vorhandene Renderer und versionierte deklarative Szenen verwenden; Modelltexte dürfen keinen ausführbaren Code, keine fremden ausführbaren Inhalte und keine ungeprüften Koordinaten einschleusen. Zahlen, Beziehungen, Beschriftungen und sichtbare Zustände gegen dieselben geprüften Daten validieren. Geeignete Interaktionen und Animationen erhalten Start/Pause, Zurücksetzen und gegebenenfalls Schrittsteuerung sowie verständliche Alternativen für Tastatur, Screenreader und reduzierte Bewegung.

  **Abnahme:** Fachkundige Prüfung und tatsächliche Webdarstellung decken ausgewählte Mathematik-, Sprach-, Natur- und Gesellschaftsfachfälle ab; fehlerhafte oder fehlende Grafik wird sicher korrigiert beziehungsweise nicht als vollständig ausgegeben. Erkunden allein erzeugt keinen Leistungsnachweis.

- [ ] **P1 – Schulbuddy als sicheren kontextbezogenen Lernbegleiter prüfen**

  Aktuelle Heftseite, Lernziel, Aufgabe, sichtbaren Grafikzustand und zulässige Hilfen revisionsgebunden übergeben; Schnellaktionen tatsächlich absenden. Antworten auf unklare Quellen, fachliche Fragen, Manipulationsversuche in hochgeladenen Bildern und unangemessene Eingaben mit künstlichen Fällen prüfen. Keine menschliche Identität, emotionale Abhängigkeit, Diagnosen oder zugesicherte Lernerfolge vortäuschen. Bei deutlichem Unterstützungsbedarf eine verständliche, altersgerechte Hilfeoption vorsehen.

  **Abnahme:** Der Tutor bezieht sich auf die tatsächlich berechtigte Quelle, macht Unsicherheit deutlich, verrät nicht ungefragt wesentliche Lösungen und verbucht erfolgreiche aufgabenbezogene Hilfen korrekt. Rechteentzug oder Quellenänderung während des Auftrags verhindert die unberechtigte Speicherung.

## Produktmodule und Familienalltag

- [ ] **P1 – Kinderwege, Navigation und Wiederaufnahme vollständig abnehmen**

  Heute, Lernen, Fach- und Themenübersicht, Lernweg, aktive Runde, Ergebnis und freiwilliges Weiterlernen im 320-/390-Pixel-Web sowie auf breiten Ansichten bedienen. Pro Zustand die nächste Hauptaktion, Rückweg, Warteanzeige, eigene Eingaben und Fehlermeldung prüfen; laufende Runden, Quellen und verpflichtende Elternaufträge dürfen sich nicht gegenseitig verdecken. Gerätewechsel, Reload, parallele Sitzungen, unvollständige Antworten und offene Rückmeldung einbeziehen.

  **Abnahme:** Jede getestete Route erreicht ihr tatsächliches Ziel ohne festhängende Schleife; Feedback bleibt bis zur bewussten Fortsetzung sichtbar, Antworten und Position überleben Wiederaufnahme und angezeigte Zeit beruht auf gespeicherten Aktivitätssekunden.

- [ ] **P1 – Hefte, Materialarten und Suche im digitalen Ranzen abnehmen**

  Fotos von Arbeitsblättern, Heftern, Arbeitsheften, Buchseiten und Tests im künstlichen Konto prüfen: Fachauswahl, unzugeordnete Seiten, Blättern, Zoom, Suche, Filter, Lazy Loading und Berechtigungen. Eine und mehrere gewählte Heftseiten als bewusste Grundlage einer neuen Übung verwenden. Löschvorschau und Neu-Einlesen gegen die aktuellen Regeln für betroffene Runden und Antworten prüfen. Bedarfsgerechte Fotoauslieferung und Cachebereinigung beim Konto- oder Gerätewechsel erhalten.

  **Abnahme:** Berechtigte sehen nur eigene Quellen, auch bei vielen Seiten und Netzunterbrechung; Blättern und Suchen erzeugen keine KI-Kosten oder Lernzeit, und eine bewusst gestartete Übung ist den richtigen Quellenrevisionen zugeordnet.

- [x] **P2 – Offline-Ranzen als gesonderten Produktumfang entscheiden und gegebenenfalls umsetzen**

  Der vorhandene Fotozugriff ist kein nachgewiesener vollständiger Offline-Neustart. Für einen Offline-Ausbau festlegen, welche Inhalte ausdrücklich auf dem Gerät gespeichert werden, wie sie verschlüsselt, begrenzt und aktualisiert werden und wie Entzug, Logout, Geräteverlust, Quellenlöschung und Konflikte behandelt werden. Ohne beschlossenen und getesteten Ausbau die Internetabhängigkeit verständlich nennen.

  **Abnahme:** Bei Aufnahme in den Leistungsumfang funktionieren dokumentierte Lesefälle nach App-Neustart ohne Netz; unberechtigter Zugriff und veraltete beziehungsweise entzogene Inhalte werden verhindert. Synchronisation erzeugt keine doppelten Antworten, Fotos oder KI-Aufträge.

  **Entscheidung 31.10.2026:** Ein vollständiger Offline-Ranzen ist derzeit
  nicht im Leistungsumfang. Die Hefteroptionen nennen die Internetpflicht;
  `docs/NOTEBOOKS.md` beschreibt die Grenzen und Voraussetzungen eines späteren
  Ausbaus. `collection_resume_test.dart` prüft den Hinweis, den GET-only-Zugriff
  und Schutz bei Sitzungs-/Kindwechsel; 15 Widgettests bestanden. Damit wird
  weder Offline-Zugriff noch ein verschlüsselter Gerätespeicher behauptet.

- [ ] **P1 – Elternübersicht, Noten und Planung gegen echte gespeicherte Fakten prüfen**

  Mit einer künstlichen Familie mehrere Kinder, Lerntage, Hilfen, Aufgaben, Versuche, Lernzeit, verbindliche Termine und Freizeiten durchspielen. Berechtigte Elternansichten auf Smartphone und Desktop vergleichen; PDF-Notenimport nur lokal, mit Vorschau, eindeutiger Zuordnung und ohne Roh-PDF-Speicherung testen. Elternlesen darf keine Kinderzeit oder Antworten erzeugen; Noten und private Bemerkungen dürfen nicht automatisch an KI-Anbieter gelangen.

  **Abnahme:** Alle Anzeigen lassen sich auf dieselben gespeicherten Daten zurückführen, Familienmitglieder sehen nur Berechtigtes, Import und Wiederholung sind idempotent und es entstehen keine erfundenen Diagnosen oder Notenprognosen.

- [ ] **P1 – Adminoberfläche und laufende Betriebsentscheidungen abnehmen**

  Familien- und Kontoverwaltung, Kindertages-/Monatsbudgets einschließlich unbegrenzt, Familien-/Systemgrenzen, Providerstatus, Kostenbelege, Notfallstopp und revisionsgebundene Einstellungen mit künstlichen Konten testen. Adminrechte im Backend durchsetzen; Betriebsadministratoren erhalten keinen Zugriff auf private Kinderinhalte. Abschnittswechsel dürfen Entwürfe nicht verwerfen und Lesezugriffe keine Änderungen oder Anbieteraufrufe auslösen.

  **Abnahme:** Fehlerzustände und tatsächlich wirksame Limits sind verständlich; Notfallstopp bleibt bei gestörter Providerabfrage erreichbar, Änderungen sind auditiert, parallele Bearbeitung und widerrufene Sitzungen werden korrekt behandelt.

- [ ] **P1 – Benachrichtigung und direkte Zielnavigation vollständig prüfen**

  Bereitschaft von Seitenverarbeitung und Lernrunden sowie optional fehlende Tages- oder Prüfungsvorbereitung testen. In-App-Glocke mit scrollendem Nachladen, sichtbarkeitsbezogener Lesemarkierung, Wiederaufnahme und berechtigtem Direktlink prüfen; Push folgt denselben neutralen Ziel- und Berechtigungsregeln. Ruhezeiten, Duplikate, Logout, deaktiviertes Push und fehlgeschlagene Zustellung berücksichtigen.

  **Abnahme:** Genau die vorgesehene berechtigte Person kann den passenden gespeicherten Inhalt öffnen; gelesene und ungelesene Meldungen stimmen nach Scrollen und Gerätewechsel. In-App-Erfolg, FCM-Annahme und sichtbare native Zustellung sind getrennt belegt.

- [ ] **P1 – Familienanrufe und optionale Medien nur im freigegebenen Umfang abnehmen**

  Falls für die gewählte Startstufe vorgesehen, Eltern-/Kinderrollen, ausdrückliche Kamera-/Mikrofon-/Bildschirmfreigaben, Verbindungsaufbau, Abbruch, Widerruf und Gerätewechsel mit synthetischen Konten prüfen. Medienlinks auf passende katalogisierte Inhalte und Rückkehr zum Lernkontext testen; kein privater Kontext in URL oder Referrer.

  **Abnahme:** Fremde Familien und Administratoren erhalten keinen privaten Zugriff; fehlende Berechtigungen und ausgefallene Medien blockieren den Lernweg nicht. Nicht geprüfte optionale Funktionen sind nicht Bestandteil der Freigabe.

## Laufende Qualitätssicherung und finale Freigabe

- [ ] **P1 – Abhängigkeiten und kommende Toolchain-Änderungen prüfen**

  Beim lokalen Releasebuild auf Commit `614f7d3` meldete Flutter WebAssembly-Hinweise für `flutter_tts` und Gradle künftig erforderliche Kotlin-Plugin-Anpassungen; bei Backendtests erschien eine Starlette-/HTTPX-DeprecationWarning. Diese Warnungen sind keine aktuellen Buildfehler, können aber spätere Updates behindern. Kompatible Versionen, Lizenz- und Sicherheitsstände sowie Folgen für Web, Android, Sprache und Firebase anhand verlässlicher Quellen untersuchen. Updates getrennt und reproduzierbar mit bestehender Toolchain, Tests und Rückweg durchführen, ohne geschützte Routen oder Firebase-Projekte auszutauschen.

  **Abnahme:** Jede Warnung ist mit tatsächlicher Auswirkung, zuständiger Abhängigkeit und Lösung oder dokumentiertem Beobachtungszeitpunkt erfasst; angepasste Builds und betroffene Funktions-/Gerätetests sind für den jeweils freigegebenen Umfang nachgewiesen. Ein regulär erfolgreicher JavaScript-Webbuild wird nicht als erfolgreicher WebAssembly-Build ausgegeben.

- [ ] **P1 – Datenschutz und Anbieterunterlagen fachkundig prüfen lassen**

  Verzeichnis der Datenarten und Datenflüsse für Kinder, Eltern, Fotos, Lernstände, KI-Anbieter, Hosting, Firebase und Support erstellen. Tatsächliche Auftragsverarbeiter, Unterauftragsverarbeiter, Speicherorte, internationale Übermittlungen, Löschfristen und vertragliche Grundlagen dokumentieren. Eine qualifizierte Stelle prüft Rechtsgrundlagen, altersgerechte Informationen, Elternrechte, Widerruf und ob eine Datenschutz-Folgenabschätzung erforderlich ist; bestehende Betreiberfreigaben nicht mit einer unabhängigen Rechtsprüfung verwechseln. Für KI-Funktionen den konkret anwendbaren Rechtsrahmen und die Risikoeinstufung bewerten lassen.

  **Abnahme:** Dokumentation, Bewertung, gegebenenfalls Folgenabschätzung, vereinbarte Maßnahmen und Zuständigkeiten liegen für den vorgesehenen Freigabeumfang vor; offene Risiken sind vor der jeweiligen Freigabe entschieden.

- [ ] **P1 – Echtzeitstatus gezielt und zuverlässig bereitstellen**

  Für Fotoverarbeitung, Lernrundenvorbereitung, Benachrichtigungen und andere tatsächlich zeitkritische Ansichten die vorhandenen Aktualisierungswege erfassen. Wo sinnvoll, authentifizierte SSE- oder WebSocket-Ereignisse oder gleichwertige gezielte Aktualisierung einsetzen: Familienzuordnung, Wiederverbindung, Ereignisverlust, Gerätewechsel und Hintergrundzustand beachten. Keine komplette Seite in störenden Abständen neu laden; Statusabrufe und Wiederverbindung dürfen keine KI-Aufträge oder Kosten auslösen. Weniger kritische Ansichten nach belegtem Bedarf aktualisieren, ohne einen pauschalen Umbau als Erfolg auszugeben.

  **Abnahme:** Künstliche Geräte zeigen relevante Statusänderungen ohne ungewollten Voll-Refresh, verlieren weder Eingaben noch Navigation und sehen keine Ereignisse anderer Konten; Ausfall und Wiederaufnahme sind reproduzierbar getestet.

- [ ] **P2 – Modellwechsel und Markenauftritt kontrolliert vorbereiten**

  Neue KI-Modelle einschließlich eines möglichen Terra-Einsatzes getrennt für Bilderkennung, Erklärungen, Bewertungen, Kosten und Datenschutz anhand real verfügbarer Anbieterkennungen und künstlicher Prüffälle evaluieren; Katalogdaten allein sind keine Freigabe. Nutzerseitige Bezeichnung SchuleSchlau, vorhandene Logos, Androidartefakte und Texte konsistent halten. Die bisherige Adresse bleibt bestehen, bis eine spätere Domain- oder Migrationsentscheidung tatsächlich getroffen wurde; keine Domainregistrierung aus dieser Roadmap ableiten.

  **Abnahme:** Jeder eingesetzte Modell-/Upstreamwechsel hat nachvollziehbare Qualitäts-, Kosten-, Sicherheits- und Rollbacknachweise. Marken- und Adressänderungen sind kanalübergreifend geprüft und beschädigen keine Logins, Links oder Updates.

- [ ] **P1 – Unabhängigen Sicherheits- und Kinderschutztest durchführen**

  Eine qualifizierte unabhängige Prüfung mit vereinbartem Umfang für Konten, Sessions, Familie/Geschwister/Admin, Uploads, Löschung, URLs, Prompt-Injection, KI-Ausgaben, Release und Infrastruktur durchführen. Kinderfreundliche Fehlermeldungen, Eskalation bei problematischen Inhalten, Datenminimierung und menschliche Ansprechbarkeit gesondert bewerten. Freigaben und Testzugänge begrenzen; Testdaten und -ergebnisse datensparsam behandeln.

  **Abnahme:** Bericht mit nachvollziehbaren Fundstellen, Risikoeinstufung und Nachtests liegt vor; kritische und hohe Befunde sind behoben beziehungsweise vor jeglicher Freigabe durch die verantwortliche Stelle nachvollziehbar entschieden.

- [ ] **P1 – Abnahmen systematisch und wiederholbar automatisieren**

  Passende Backendtests auf SQLite und für Sperren, Rechte und Parallelität auf isoliertem PostgreSQL, Flutter-Tests, Analyse, Webbuild und releasegebundene Prüfungen in einer nachvollziehbaren Pipeline ausführen. Für Fotoimport, Aufgabenbewertung, Lernstand, Tutor, Benachrichtigungen und Rollen repräsentative Browser-E2E-Fälle mit künstlichen Daten ergänzen. Fehlerpfade, Migrations- und Rollbackkompatibilität sowie zeitgesteuerte Abläufe mit isolierter Testuhr abdecken.

  **Abnahme:** Testumfang, Quellrevision, Ergebnisse und übersprungene Tests sind nachvollziehbar. Mocks, Emulatoren, synthetische Inhalte und physische Beobachtungen werden getrennt ausgewiesen; fehlgeschlagene oder abgebrochene Tests gelten nicht als bestanden.

- [ ] **P1 – Nutzer- und Betriebsdokumentation konsolidieren**

  README, Installationsanleitung, Betrieb, Datenschutzhinweise, Eltern-/Kinderanleitungen und KI-Lernmodell mit dem tatsächlichen Stand abgleichen. Historische Aussagen zu kostenlosen Anbietern, Zeitobergrenzen, alter APK-Bezeichnung oder früheren CI-Sperren mit Datums- und Kontextverweis korrigieren, ohne alte Prüfberichte umzuschreiben. Support, Störungsmeldung, Export, Löschung, Umgang mit Fehlbewertungen und Wiederherstellung verständlich erklären.

  **Abnahme:** Eine neue technische Person und eine testende Familie können die jeweils relevanten Abläufe anhand aktueller Dokumentation ausführen; Versionsstand, Grenzen, Verantwortliche und letzte Prüfung sind erkennbar.

- [ ] **P1 – Freigabegespräch und nachvollziehbare Entscheidung durchführen**

  Die Ergebnisse aller für die gewählte Stufe geltenden Punkte zusammenführen: Funktionen und Ausschlüsse, Tests und Fehler, Datenschutz- und Sicherheitsprüfung, Endgeräte, Supportbereitschaft, Datenwiederherstellung, Anbieterabhängigkeit und Kostensteuerung. Für jeden offenen Punkt eine zuständige Person, Risikobewertung und konkrete Folgeaktion nennen. Produktivschaltung, externe Veröffentlichung und gegebenenfalls Verkauf bleiben getrennte Entscheidungen.

  **Abnahme:** Verantwortliche dokumentieren Umfang, Datum, freigegebene Version, offene Risiken und Entscheidung. Fehlt ein zwingender Nachweis, bleibt die entsprechende Freigabestufe offen; ein einzelner grüner Testlauf ersetzt diese Entscheidung nicht.

- [ ] **Laufend – Nach Freigabe messen, reagieren und erneut prüfen**

  Ohne private Inhaltsprotokollierung Fehlerquoten, Auftragsalter, unerwartete Kosten, Sicherungszustand, Speicher und Supportmeldungen überwachen. Anbieter-, Modell-, Lehrplan-, Geräte- und Bibliotheksänderungen an versionierte Regressionen und fachliche Stichproben binden. Störungen priorisiert beheben, Kinder und Eltern verständlich informieren und bei Bedarf betroffene Funktionen begrenzt zurücknehmen.

  **Abnahme:** Verantwortliche, Alarmschwellen, Überprüfungsintervalle und dokumentierte Rückwege existieren; neue Erkenntnisse werden mit Datum und belastbaren Belegen in diese Roadmap und die zuständige Dokumentation übernommen.
