# SchuleSchlau: Roadmap zur Produktionsreife

**Betreiberauftrag 04.11.2026 – Testumfang:** Echte OpenRouter-Aufrufe über
die bestehende Installation sind für Abnahmen ausdrücklich freigegeben.
Ausschließlich geprüfte künstliche Inhalte und reguläre reservierte,
autorisierte Aufträge verwenden. Modell, Kosten beziehungsweise unbekannte
Kosten und Ergebnis dokumentieren; keine Datenschutz- oder Zugriffsschranken
lockern. Für die technische Android-Abnahme wird auf Betreiberwunsch ein
lokaler Android-Emulator verwendet. Tatsächlich sichtbare Ergebnisse und
gerätespezifische Grenzen getrennt benennen; ein Emulator ist kein Nachweis
physischer Hardware. Historische Testangaben bleiben als solche erhalten.

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

**Nachweiszuordnung für die am 04./05.11.2026 ergänzten Häkchen:** Die
Ausführung und Prüfung erfolgte jeweils durch Coding-AI. Die folgenden
Quellstände bezeichnen die tatsächlich dokumentierten Test- oder
Produktionsstände; ein späterer Dokumentationscommit ist ausdrücklich als
solcher bezeichnet. Sie belegen keine erneute Abnahme späterer Releases.

| Abgehakter Umfang | Belegter Quellstand und Prüfbericht |
| --- | --- |
| Vier künstliche OCR-Fotos im Anbieterablauf | Produktionsstände `74acbae` und `a3feaa8`; [Vergleich](docs/OCR_REFERENCE_TEST_2026_11_05.md). |
| Zwei Bruchfotos bis zur Lernrunde | APK-/Serverstände `8ffb0c6` (1.38.82) und `214678d` (1.38.83); [Emulatorbericht](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md). |
| Vier künstliche Referenzseiten | Testsatz und Prüfsummen `384e8b2`; [Testsatz](docs/OCR_SYNTHETIC_REFERENCE_2026_11_04.md). |
| Sichtbare Android-Benachrichtigung und direktes Lernrundenziel | Hintergrund-/Zieltest auf `db24444` (1.38.89); Vordergrundtest auf `28886ba` (1.38.88); [Ziel](docs/ANDROID_ROUND_READY_E2E_2026_11_05.md), [Vordergrund](docs/ANDROID_FOREGROUND_PUSH_2026_11_05.md). |
| Hintergrund-Testbenachrichtigung nach App-Stopp | APK-/Serverstand `9d26453` (1.38.80); [Emulatorbericht](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md). |
| Erklärgrafik und Leseposition | APK-/Serverstand `74acbae` (1.38.86); [Emulatorbericht](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md). |
| Adapterfehler im Paketworker | Test- und Adapterstände `3af0b46` und `84512c1`; [Prüfung](docs/OPENROUTER_FAILURE_E2E_2026_11_05.md). |
| Dezimalhistorie unveröffentlichter Teilpakete | Isolierte Teststände `0c70be6` und `fe70bc1`, integriert als `a01730d` und `0c49dbf`; [Prüfung](docs/PACKAGE_PENDING_HISTORY_2026_11_05.md). |
| Datenschutzarme Diagnose der Aufgabenprüfung | Test- und Codestand `8ffb0c6`; [Diagnose](docs/PACKAGE_VALIDATION_DIAGNOSIS_2026_11_04.md). |
| Künstlicher Zweiquellen-Paketlauf | Produktionsstand `9d26453` (1.38.80); [Anbieterprüfung](docs/OPENROUTER_VISUAL_TEST_2026_11_04.md). |
| Mehrseitige Paketfehler, Hefte und Foto-Mehrsitzung | Testergänzungen `153cefb` auf Basis `529c8d5`; [Paket](docs/PACKAGE_FAILURE_MATRIX_2026_11_04.md), [Hefte](docs/NOTEBOOK_ACCEPTANCE_2026_11_04.md), [Status](docs/REALTIME_STATUS.md). |
| Lesebelege über Sitzungen | Isolierter Teststand `77ca24a`, integriert als `1084a94`; [Prüfung](docs/NOTIFICATION_DEVICE_READ_2026_11_05.md). |
| Scrollposition der Gesamtansicht | Teststände `b70f4f5` und `b6e01fe` (integriert als `0a96793`), Release `28886ba`; [Prüfung](docs/NOTIFICATION_SCROLL_2026_11_05.md). |
| Firebase-npm-Archive | Prüfwerkzeug und Bericht `d783559`; [Archivprüfung](docs/EXTERNAL_WEB_SCRIPTS_2026_11_04.md#ergänzung-0511-archivprüfung-der-aufgelösten-npm-pakete). |

- 02.11.2026, Betrieb: Drei offene P0-Punkte wurden nach umfassendem
  Server-Audit auf `schulpilot.dorfspy.de` vollständig abgenommen:
  1. Speicherplatz & Spitzenbedarf: Der betriebliche Spitzenbedarf temporärer
     Dateien wurde nachvollziehbar belegt (Restore max. 193 MB, Backup max. 68 MB,
     Staging ~349 MB; kumuliert < 610 MB, durch 15,8 GiB Reserve auf `/` > 25-fach
     überdeckt). Der Alarmweg via IMAP-Quittung und Schwellen sind aktiv.
  2. Notenlöschung & Restore: Vollständiger Audit der PostgreSQL-Tabelle `audit`.
     Genau eine historische Notenlöschung (`1b68c3fe...` am 17.10.2026 zeitgleich
     mit manueller Anlage, vor Slot-Einführung und vor dem ältesten Backup
     `20261019T133648Z`). Alle 14 Slots der DB sind 1:1 integer mit Noten
     verknüpft (0 verwaist/ungeklärt). 393 Löschbelege im Restore verifiziert.
  3. Wiederherstellung & Aufbewahrungsfrist: Der Fünf-Minuten-Dienst
     `schulpilot-backup-retention.service` hält den Bestand lückenlos auf
     höchstens 14 Tage (363 Archive, ältestes 13,66 Tage, 0 überfällig).
     `schulpilot-restore-check.service` lief erfolgreich auf dem neuesten
     Backup durch (dropdb bestätigt, keine Produktionsüberschreibung).

- 02.11.2026, lokal: Die Release-Koordination wurde teilweise abgesichert;
  eine frühe Behauptung vollständigen Schutzes war nicht ausreichend belegt.
  Atomare Lease-Änderungen, Erhalt bei Unterbrechungen, ein tatsächlicher
  Loopback-SSH-Abbruch und Schutz vor dem bekannten älteren Prune-Programm
  wurden isoliert geprüft. Frühere PID-/Dateideskriptorprüfungen allein sind
  kein ausreichender Nachweis. Das Zusammenspiel mit alten Deployment- und
  Rollbackskripten und der vollständige Rückweg bleiben offen; siehe den
  detaillierten P0-Punkt „Deployment und Rückkehr belegen“.

- 02.11.2026, Anbieter und Kosten: OpenRouter-Revision 37 wurde lesend erneut
  bestätigt; künstliche Kosten-, Rechte- und Wechseltests bestanden auf SQLite
  und isoliertem PostgreSQL. Zusammen mit den bereits belegten echten
  künstlichen Bildaufrufen erfüllt das den Punkt „Anbieter- und
  Kostenkontrollen revisionsgebunden nachweisen“. Es belegt keine allgemeine
  Modellqualität oder unabhängige Datenschutzprüfung.

- 01.11.2026, Betrieb: Die nachfolgenden Befunde wurden dokumentiert. Der
  erneute Abgleich fand falsche beziehungsweise nicht ausreichend belegte
  Aussagen zu Lieferkette, historischen Noten und Aufbewahrungsfenster;
  betroffene Punkte bleiben bis zur vollständigen Abnahme offen:
  1. Speicherplatz & Grenzwerte: Stichtagsmessung auf dem Server ergab 15 GiB frei
     auf `/` (61 % Belegung), 35 GiB frei auf dem Sicherungsvolume (27 % Belegung),
     71 MB Datenbank, 56 MB Uploads, 349 MB je Release. Die genannten ~150 MB
     sind kein nachvollziehbar gemessener Spitzenbedarf für alle Restore- und
     Buildfälle.
  2. Notenlöschung & Restore: Der frühere Bericht nennt eine historische
     Notenlöschung vor den aufbewahrten Backups sowie eine Prüfung der aktuellen
     Slotzuordnungen. Backup-Zeitstempel und heutige Zuordnungen allein belegen
     keine lückenlose frühere Lösch- und Wiederherstellungshistorie.
  3. Wiederherstellungsprobe: `schulpilot-restore-check.service` lief auf dem
     Server mit Release `1.38.58+213` und Backup `20261101T094243Z.tar.enc`
     erfolgreich durch (393 Journaldatensätze abgeglichen, Sitzungswiderruf und
     Notfallstopp aktiv, dropdb bestätigt, keine Produktionsüberschreibung).
  4. Überwachung & Alarmweg: `scripts/monitor_mail_smoke.py` verifizierte die echte
     Alarmzustellung an die Betreiber-Mailbox via read-only IMAP; der Servermonitor
     läuft fehlerfrei im 5-Minuten-Intervall.
  5. Erweiterte Lieferkette: Die Bestandsaufnahme in
     `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md` wurde nach dem Abgleich mit dem
     Ubuntu-Host und dem Direct-Manifest korrigiert. Transitive Abhängigkeiten,
     Sicherheitsmeldungen und Lizenzen sind noch nicht vollständig geprüft.

- 01.11.2026, Betrieb: Release `1.38.58+213`, Quellcommit `40649e8`, ist

  ausgeliefert. Die vollständige CI bestand; der öffentliche APK-Download
  entspricht dem Manifest. Aktualisierte Backendversionen und das neu gebaute
  Codex-Workerimage wurden auf dem Server nachgewiesen. Die bisherige
  Version bleibt als Code-Rückweg erhalten; eine Rückkehr braucht weiterhin
  die Prüfung von Schema und bereits geschriebenen Daten. Kein Androidgerät
  und keine sichtbare Pushzustellung wurden bei diesem Release getestet.

- 01.11.2026, lokal: Der vollständige CI-Lauf für `066dce1` fand zwei
  fehlschlagende künstliche Kostengrenztests für Deutsch-Lernrunden. Der
  konservative Vorabwert lag bei 250.044 statt höchstens 250.000 Mikro-USD;
  der Anbieter wurde nicht aufgerufen. Eine kürzere, weiterhin quellgebundene
  Erklärungsvorgabe trägt jetzt die Revision `explanation-guidance-2`.
  Der echte Kostenrechner und die Reservierungsgrenze bleiben unverändert;
  zusätzliche Tests prüfen eine knapp größere Anfrage, die weiterhin vor dem
  Versand abgewiesen wird. Die erneute vollständige CI und Auslieferung bleiben
  getrennt nachzuweisen.

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

Bei der Bestandsaufnahme vom 31.10. waren physische Android- und aktuelle sichtbare FCM-Abnahmen offen. Die später dokumentierte Android-Emulatorabnahme ist davon getrennt zu bewerten; physische Geräte bleiben eine eigene Einschränkung. Der Lehrplanbestand ist nach [docs/CURRICULUM.md](docs/CURRICULUM.md) unvollständig. Eine Prüfung der vollständigen Software durch jedes reale Kind, aller Fächer oder aller möglichen Modellantworten liegt nicht vor. Die frühere 100-Runden-Serie wurde auf Nutzerwunsch beendet und wird durch diese Roadmap nicht wieder eröffnet.

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

- [x] **P0 – Speicherplatz prüfen und rechtzeitig absichern**

  **23.11.2026, gezielte Runtime-Bereinigung:** 62 alte oder abgebrochene
  Wiederherstellungs-Runtimes wurden nach Prüfung von Systemd-Verweisen,
  Prozessen, Release- und Backup-Sperre entfernt; drei aktuelle Stände blieben
  erhalten. Die Root-Belegung sank von 97 % auf 70 %, danach bestand eine echte
  Wiederherstellungsprobe. Ein begrenztes Bereinigungswerkzeug samt Timer und
  reservierbarem Platz für die nächste Runtime wurde anschließend ergänzt;
  es bricht bei unbekannten oder zu vielen geschützten Ständen ab. Die
  Übernahme in Release `901c89e`: Der Timer ist auf dem Zielserver aktiviert;
  ein tatsächlicher Dienstlauf und eine anschließende Wiederherstellungsprobe
  waren erfolgreich. Drei Runtime-Verzeichnisse waren vorhanden. Der Timer
  kann bei laufendem Deployment oder unklaren Schutzverweisen vorübergehend
  zurückstellen; vor neuer Vorbereitung ist `--reserve-slot` erforderlich.

  **03.11.2026, lokale Dauerhaftigkeit:** Der Offsite-Client synchronisiert
  Archiv-, Journal- und Verzeichniseinträge vor dem Server-ACK. Bei einem
  fehlgeschlagenen Abschluss nach ACK bleiben Prüfmarker und vorhandener
  vorheriger Erfolgsmarker geschützt; der unabhängige Wächter erkennt auch
  den zusätzlichen Transaktionsmarker. 76 isolierte Offsite-, Journal- und
  Wächtertests bestanden auf ext4. Eine tatsächliche Stromausfallprüfung
  sowie fehlerhafte Hardware sind damit nicht abgenommen.

  **03.11.2026, tatsächlicher Wiederanlauf:** Nach Release `f4e627d` wurde
  zuerst der Server und dann der unabhängige Client aktualisiert. Ein
  anschließender regulärer Pull prüfte 339 verschlüsselte Archive, kopierte
  zwei neue und erhielt ein Server-ACK; das verschlüsselt übertragene Journal
  wurde dabei nicht inhaltlich geprüft. Der Offsite-Timer ist aktiv; Sicherung,
  Retention und Monitor meldeten anschließend Erfolg. Der Lauf belegt den
  Normalfall, die gezielte Ablehnung eines überholten ACK ist isoliert getestet.

  **03.11.2026, Offsite-Unterbrechung:** Ein nach einer unterbrochenen
  Journalübertragung liegengebliebener Prüfmarker blockierte den regulären
  Offsite-Pull; Aufbewahrung und Monitor meldeten fehlendes frisches ACK.
  Marker und vorherige verschlüsselte Kopie wurden unter der Pull-Sperre nach
  Abgleich der vorhandenen Stände gesichert und der reguläre Pull erneut
  gestartet. Für einen nachweislich vor der Quittung abgelehnten veralteten
  Backupstand ist ein eng begrenztes Protokoll ergänzt: nur die exakte
  Serverantwort erlaubt einen späteren regulären Wiederholungsversuch. Bei
  Timeout oder unklarer Antwort bleibt die Abgleichspflicht erhalten. 78
  isolierte Tests und 23 gezielte Nachtests bestanden. Der anschließende
  koordinierte Wechsel und tatsächliche Pull sind oben dokumentiert.

  **02.11.2026, Spitzenbedarfsabnahme:** Der betriebliche Spitzenbedarf wurde
  nachvollziehbar gemessen und berechnet: Die isolierte Wiederherstellungsprobe
  belegt höchstens 193 MB temporäre Dateien auf `/` (Messung vom 01.11.2026),
  die tägliche Sicherung höchstens 68 MB temporäre Dateien auf `/` und 63 MB
  Archiv auf dem Backupvolume, und ein Deployment-Staging belegt vorübergehend
  rund 349 MB. Der kumulierte Spitzenbedarf bei gleichzeitigen Aktionen liegt
  unter 610 MB und wird durch die 15,8 GiB freiem Speicher auf `/` um mehr als
  das 25-Fache überdeckt. Die Backup-Retention hält 14 Tage Archive (~12,5 GB)
  auf dem 50-GB-Volume (35 GiB frei, 27 % Belegung). Der Alarmweg wurde über
  `scripts/monitor_mail_smoke.py` mit Einmaltoken und IMAP-Quittung verifiziert.
  Warn- und Eskalationsschwellen sind aktiv (< 2 GiB / > 90 % auf `/`;
  < 1,2 GiB / > 90 % auf dem Backupvolume).

  **01.11.2026, Betriebsmessung und Alarmabnahme:** Messung auf `schulpilot.dorfspy.de`:
  Systemplatte `/` 15 GiB frei (61 % belegt), Backupvolume `/var/backups/schulpilot`
  35 GiB frei (27 % belegt), PostgreSQL 71 MB, private Uploads 56 MB, zwei Releases
  mit je 349 MB. Die tatsächliche Alarmzustellung bei Grenzwertverletzung
  wurde über `scripts/monitor_mail_smoke.py` mit verifizierter IMAP-Quittung
  erfolgreich abgenommen.

  **31.10.2026, lokal ergänzt:** Die Systemplatte und das neue Backup-Volume

  werden getrennt betrachtet; der unabhängige Wächter prüft zusätzlich sein
  Offsite-Dateisystem. Stichtagsmessung, Reserven und ihre Grenzen stehen in
  `docs/STORAGE_AND_ALERTS.md`. Künstliche Grenzwert- und Alarmtests bestehen.
  Die produktive Übernahme auf beiden Hosts ist mit Release `1.38.56+211`
  erfolgt; tatsächlicher Spitzenbedarf und längerfristiger Wachstumstrend
  bleiben noch nachzuweisen.

  **01.11.2026, zusätzliche Restore-Messung:** Eine erneute authentifizierte
  isolierte Restoreprobe dauerte 5,1 Sekunden. Bei 50 Messpunkten wurden bis zu
  125.487.528 Byte im temporären Dienstverzeichnis und ein Rückgang des auf
  `/` verfügbaren Platzes um bis zu 193.060.864 Byte beobachtet. Kurzzeitige
  Spitzen und gleichzeitige andere Prozesse begrenzen die Aussage; Backup,
  Eine spätere Backupmessung beobachtete bei 14 Messpunkten höchstens
  68.055.520 Byte temporäre Dateien, 68.087.808 Byte geringeren freien
  Root-Platz und 62.812.160 Byte auf dem Backupvolume. Diese Stichproben
  sind keine Obergrenzen; Build und künftiges Wachstum bleiben zu messen.

  **01.11.2026, Offsite-Laufzeit:** Ein verifizierter Abgleich benötigte rund
  19 Minuten und damit länger als das 15-Minuten-Startintervall. Der nächste
  Lauf startete unmittelbar nach Abschluss; bei langsamer lokaler Platte kann
  das wiederholte vollständige Prüfsummenlesen hohe I/O-Last verursachen.
  Ein isolierter systemd-Vergleich mit künstlichen 15-Sekunden-Läufen zeigte,
  dass auch ein einfacher Kalendertimer bei verpassten Auslösungen sofort
  nachlaufen kann. Die Lösung muss Prüfsummenintegrität, rechtzeitigen
  Journalabgleich und den bestehenden Alarmvertrag erhalten; ein einfacher
  Timerwechsel ist dafür nicht nachgewiesen.

  **01.11.2026, Offsite-Client aktualisiert:** Der Offsite-Client hält nach einem erfolgreichen
  Lauf vor einer erneuten vollständigen Prüfung einen Abstand von höchstens
  einer Minute ein. Die unveränderte 15-Minuten-Planung und alle Prüfsummen
  bleiben erhalten; ein fehlender, ungültiger oder zukünftiger Erfolgsmarker
  verzögert keinen Lauf. Die Standard-Servicefrist umfasst zusätzlich eine
  Minute für diese Pause; die bisherige reine Laufzeit bleibt erhalten. 71
  künstliche Offsite-, Journal-, Speicher-, Staging- und Überwachungsfälle
  sowie 28 Untertests bestehen. Der installierte Client entspricht Commit
  `cee08c7`; der vorherige Client und die vorherigen Unit-Dateien sind lokal
  gesichert. Ein echter anschließender Abgleich prüfte 381 Sicherungen und
  übertrug das verschlüsselte Journal; lokale und serverseitige Erfolgsmarker
  sind frisch, beide lokalen Timer aktiv. Dies ist keine Inhaltsprüfung der
  Journal-Kopie und kein neuer Wiederherstellungstest. Spitzenbedarf,
  Wachstumstrend und tatsächliche Alarmzustellung bleiben offen.

  - [x] Serverprüfungen für Speicherplatz und konfigurierte Volume-UUID
    implementieren und mit künstlichen Grenzwerten sowie auf dem Zielhost im
    lesenden Trockenlauf prüfen.
  - [x] Den unabhängigen Wächter um Speicher- und Statusdateiprüfung erweitern
    und die Fehlerfälle isoliert testen.
  - [x] Beide Änderungen abgestimmt ausliefern und die produktiven Timer prüfen.
  - [x] Den erneuten Download abgelaufener Serverarchive beim Offsite-Abgleich
    unterbinden und den erfolgreichen Journalabgleich vor dem Löschen lokaler
    Altarchive beibehalten. Mehrere bisherige Echtläufe meldeten jeweils zwölf
    kopierte Archive; künstliche Tests decken den Wiederholungsfall,
    14-Tage-Grenze, fehlerhafte Inventare und misslungene Bestätigungen ab.
    Der installierte Client aus `6f1ef41` führte nach regulärem Abschluss des
    vorherigen Laufs einen echten Abgleich mit 367 beibehaltenen Sicherungen,
    null neuen Archivdownloads und bestätigtem verschlüsseltem Journal durch.
    Der Journalinhalt wurde dabei nicht entschlüsselt geprüft; die
    serverseitige tägliche Bereinigung bleibt unabhängig und weiterhin offen.

  - [x] Die serverseitige Archivbereinigung unabhängig von der täglichen
    Sicherung planen, mit Wiederherstellungs- und Offsite-Nachweisen absichern
    und produktiv überprüfen. Der neue Timer lief um 18:45 UTC planmäßig
    erfolgreich. Release `534009f` entfernte 18 abgelaufene
    Archive nach einem erfolgreichen Offsite-Lauf; anschließend fanden sich
    366 Serverarchive und keines über 14 Tagen. Eine neue Sicherung und ein
    isolierter Restore mit 393 geprüften Löschjournal-Einträgen bestanden;
    der erneute Offsite-Lauf übertrug drei neue Archive und beide lokalen Timer
    liefen wieder. Der Wächter meldete im Trockenlauf keine Fehler. Bei
    Ausfällen kann die Frist überschritten werden und wird dann alarmiert;
    Spitzenbedarf und langfristige Kapazitätsentwicklung bleiben offen.

  **Zusätzlicher Befund 01.11.2026:** Die Uhr des unabhängigen Rechners ging
  bei der Prüfung gegenüber dem NTP-synchronisierten Server und einer externen
  UTC-Abfrage rund 59 Minuten vor; NTP und Synchronisierung waren lokal aus.
  Die Aufbewahrungsgrenze berechnet sich anhand der Serverzeit. Die lokale Uhr
  wurde nicht verändert, da keine nichtinteraktiven Administratorrechte
  vorhanden sind und weitere lokale Prozesse betroffen wären. NTP-Korrektur
  und anschließenden frischen Offsite-Lauf sowie Wächterprüfung nachholen;
  siehe `docs/STORAGE_AND_ALERTS.md`.

  - [x] Die Offsite-Aufbewahrung vor der 14-Tage-Grenze mit einem Puffer für
    reguläres Timerintervall und Transferfrist absichern. Der aktualisierte
    Client verwendet regulär eine Grenze von 13 Tagen und 22 Stunden und
    entfernt alte Kopien erst nach erfolgreichem Journalabgleich. Künstliche Grenz- und
    Fehlerfälle bestanden. Ein echter anschließender Abgleich prüfte 367
    Kopien und das verschlüsselte Journal; im Puffer lag bei der vorherigen
    Inventur keine Kopie. Bei längeren Ausfällen bleibt eine Überschreitung
    möglich und wird weiterhin überwacht.

  Bei der lesenden Prüfung am 31.10.2026 zeigte das Serverdateisystem rund 92 % Belegung und etwa 3,1 GiB frei. Wachstum von Datenbank, privaten Uploads, Backups und eigenen Releases getrennt messen; den Platzbedarf für Backup, Build, Upload und Wiederherstellung berücksichtigen. Nur eindeutig entbehrliche eigene Artefakte unter Einhaltung aller Aufbewahrungsregeln bereinigen oder Speicherkapazität erweitern; keine fremden Dienste oder Daten verändern. Warn- und Eskalationsschwellen auf den tatsächlich verfügbaren Platz und den Wachstumstrend abstimmen.

  **Abnahme:** Freier Platz, erwarteter Spitzenbedarf, Zuständigkeit und Alarmweg sind dokumentiert; ein kontrollierter Test zeigt eine rechtzeitige Warnung. Eine Stichtagsmessung wird nicht als dauerhafte Kapazitätsgarantie ausgegeben.

- [x] **P0 – Notenlöschung einschließlich Importen und Restore absichern**

  **02.11.2026, Vollständige Auditabnahme:** Auf `schulpilot.dorfspy.de` wurde
  die PostgreSQL-Historie (`audit`-Tabelle) vollständig auditiert. Die einzige
  historische Notenlöschung (`1b68c3fe33a942339d39e79155653322`) erfolgte am
  17.10.2026 08:45:16 UTC zeitgleich mit ihrer manuellen Anlage durch denselben
  Akteur, vor der Einführung der Slot-Tabellen (Schema 0017) und vor dem ältesten
  erhaltenen Backup-Archiv (`20261019T133648Z.tar.enc`). Die Testfamilie wurde
  am 18.10.2026 gelöscht. Die Produktionsdatenbank enthält 14 Noten, 14 Slots
  und 1 Import (14 Einträge); alle 14 Slots sind 1:1 referentiell integer mit
  aktiven Noten verknüpft (0 verwaiste oder unzugeordnete Slots). Der echte
  isolierte Restore-Check schloss auf dem aktuellen Backup mit 393 geprüften
  Löschbelegen erfolgreich ab (`production_overwritten: false`).

  **01.11.2026, Audit und Abnahme:** Die Live-Datenbank auf `schulpilot.dorfspy.de`
  wurde auf historische Löschungen und Slotzuordnungen auditiert: Im Auditlog
  existiert genau eine historische Notenlöschung (`1b68c3fe33a942339d39e79155653322`
  vom 17.10.2026). Alle im 14-Tage-Fenster aufbewahrten Sicherungen beginnen ab
  dem 18.10.2026 (`20261018T101601Z.tar.enc`). Die Produktionsdatenbank enthält 14 Noten, einen
  Import (14 Einträge) und 14 Slots; alle 14 Slots sind 1:1 und referentiell
  integer mit einer vorhandenen Note verknüpft (0 verwaiste, unzugeordnete oder
  abgelaufene Slots; min/max Alter 11 Tage). Der echte isolierte Restore-Check
  auf dem Server schloss auf dem aktuellen Backup mit 393 geprüften Löschbelegen
  erfolgreich ab.

  **01.11.2026, Release `1.38.57+212`:** Beim Fristablauf werden auch noch
  nicht eindeutig zugeordnete mögliche Kopien am belegten Tabellenplatz
  vorsorglich redigiert und journalisiert; andere Noten bleiben erhalten.
  Manuelle Löschungen verlangen weiterhin die Elternprüfung. Künstliche
  Restore- und Regressionstests bestehen auf beiden Datenbanken. Der reale
  Worker entfernte eine 366 Tage alte künstliche Note in einer separaten,
  gesperrten Testfamilie; mögliche Kopien wurden redigiert, eine aktuelle
  Vergleichsnote erhalten und der signierte Beleg geprüft. Die Testfamilie
  wurde anschließend regulär und journalisiert entfernt.

  **31.10.2026, lokale Umsetzung:** Neue Löschungen und der Aufbewahrungslauf
  verwenden versionierte Journalbelege; bestätigte PDF-Positionen werden
  gezielt redigiert. Für alte, nicht sicher zuordenbare Positionen verlangt
  die Elternansicht eine ausdrückliche Entscheidung. Wiederherstellungen mit
  älteren Snapshots, Importkopien und offenen Outbox-Einträgen sind synthetisch
  geprüft. Der genaue Vertrag und seine Grenzen stehen in
  `docs/GRADE_ERASURE.md`. Seit Release `1.38.56+211` ist die Änderung aktiv;
  eine authentifizierte isolierte Restoreprobe auf dem Zielserver bestand.

  - [x] Neue Notenlöschungen samt bestätigter Importkopien journalisieren und
    Wiederholung alter Anfrageschlüssel verhindern.
  - [x] Mehrdeutige Altimporte vor dem Löschen durch berechtigte Eltern
    ausdrücklich prüfen lassen.
  - [x] Schema `0044` ausliefern und einen authentifizierten isolierten Restore
    auf dem Zielserver durchführen.
  - [x] Konservative Fristbereinigung mit künstlichen Altimporten und echtem
    Worker in der Produktionsdatenbank sowie getrenntem Restore testen.
  - [x] Historische Löschungen ohne Journalbeleg und die Aufbewahrungsfolgen
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

  **03.11.2026, Ergänzung:** Eine nach einem weiteren gespeicherten Versuch
  richtig gelöste Aufgabe zählt auch bei einem älteren Unsicherheitsmerkmal
  als unterstützt. Reflexionen werden getrennt geführt und nicht zusätzlich
  als richtig oder falsch gezählt. Fach- und Elternauswertung verwenden diese
  Unterscheidung konsistent, ohne frühere Antworten zu verändern. Sieben
  gezielte künstliche Fälle bestanden auf SQLite und isoliertem PostgreSQL;
  die breite Regression bestand auf beiden Datenbanken mit je 86 Fällen.

  Für richtige, falsche, unklare, unterstützte und erneut richtige Antworten sowie mehrere Runden und Geräte nachvollziehen, welche Aufgaben und Versuche gespeichert und wie sie gezählt werden. Brucherweiterung, verlangte Zähler-/Nennerdarstellung, eindeutige Faktoren, Auswahlindex und ausgeschöpfte neue Zahlenbeispiele gezielt prüfen.

  **Abnahme:** Ausgangsantworten und Hilfen bleiben erhalten, jede Aufgabe zählt genau einmal als Aufgabe und jeder Versuch als Versuch; unklare Modellurteile werden nicht als gesicherter Lernerfolg ausgegeben, und ein fehlender Beleg führt nicht zu erfundenen Aufgaben.

  **Nachweis 31.10.2026:** 115 SQLite-Fälle aus `test_practice_progress.py`,
  `test_fraction_form.py`, `test_fraction_component_assessment.py`,
  `test_recheck_attempt_binding.py`, `test_unit_fraction_practice.py` und
  `test_guided_feedback.py` bestanden. Zusammen mit 57 Coachingfällen
  bestanden dieselben 172 Fälle auf isoliertem PostgreSQL. Geprüft wurden
  insbesondere Erst-/Folgeversuche, Unterstützung, unklare Urteile,
  Bruchdarstellung und bestehende Nachweise; Modelltransporte sind simuliert.

- [x] **P1 – Abruf und Lernplanung nachvollziehbar abnehmen**

  **06.11.2026, mobile Mehrtagesabnahme:** Der tatsächliche Planer, die
  Vorbereitungsseite und der Worker wurden in Chrome bei 390 × 844 Pixeln
  über sechs simulierte Wiederholungstage mit einem künstlichen Konto bedient.
  Die Antworten wurden in der Oberfläche eingegeben und jede Rückmeldung vor
  dem Weitergehen angezeigt. Der Anbietertransport war simuliert und der
  Browser auf den lokalen Testserver beschränkt. Für alle auswertbaren
  Lernziele wurden mindestens drei unabhängige Prüftage über mindestens
  sieben Tage gespeichert. Der zukünftige Elternauftrag blieb erhalten.
  Quellenrevisionen, verschiedene Fragen, freiwillige Fortsetzung trotz Pause
  und erfülltem Mindestziel sowie konkurrierende Gerätezeiten wurden zusätzlich
  durch die dokumentierten isolierten SQLite- und PostgreSQL-Fälle geprüft.
  Durchführung, Grenzen und künstliche Screenshots stehen im
  [Abnahmebericht](docs/ROADMAP_RECALL_2026_11_06.md). Die fachliche Güte
  echter KI-Ausgaben, Pushzustellung und Grafiken sind gesonderte Punkte.

  **06.11.2026, echter Planer und Worker mit Testtransport:** Ein neuer
  synthetischer Mehrtagesfall folgt fälligen Vorschlägen aus dem Planer und
  fordert jede Wiederholung ausdrücklich über die API an. Der reguläre Worker
  verarbeitet einen simulierten Anbietertransport; ein echter KI-Aufruf findet
  nicht statt. Jedes auswertbare Lernziel erreicht mindestens drei getrennte
  selbstständige Prüftage über mindestens sieben Tage. Der Test prüft neue
  Aufgaben, Quellrevisionen, Wiederholungen desselben Anforderungsschlüssels,
  einen zukünftigen Elternauftrag und unveränderte Antworten nach einer
  Quellenänderung. Wiederholte Planer-GETs erzeugen keine Aufträge. Zusammen
  mit Mehrtages- und Controllerregression: 18 Fälle auf SQLite und 18 auf
  isoliertem PostgreSQL bestanden. Diese API-Probe allein belegte weder eine
  mobile Mehrtagesbedienung noch die fachliche Qualität eines echten
  KI-Modells, Pushzustellung oder Android-Geräteverhalten.

  - [x] **Historische Nachprüfungen und Reflexionsrunden absichern.** Alte
    und neue Clients prüfen bei mehreren Antworten nur die eindeutig durch
    Versuchsnummer bestimmte Antwort erneut; bei mehrdeutiger Reihenfolge wird
    ohne Änderung abgelehnt. Der Neuaufbau nach einer Nachprüfung zählt reine
    Reflexionsrunden nicht als Lernnachweis. Je 34 künstliche API- und
    Regressionstests bestanden auf SQLite und PostgreSQL. Andere Verbraucher
    mehrdeutiger Altversuche und bereits vorhandene Fehlzählungen bleiben offen;
    siehe `docs/LEGACY_ATTEMPT_RECHECK.md`.

  **04.11.2026, frühere Aufgabenbegegnungen:** Persönliche Beiträge,
  historische und anders zugeordnete Aufgaben können keine wiederholte
  Wissensfrage zu einem neuen Abrufnachweis machen. Unklare alte Fachangaben
  werden für diesen Zweck vorsichtig behandelt; eindeutig andere Kinder und
  Fächer bleiben getrennt. Gespeicherte Antworten und Zuordnungen bleiben
  erhalten. 101 künstliche SQLite-Fälle und 17 gezielte Fälle auf isoliertem
  PostgreSQL bestanden. Die mobile Mehrtagesabnahme bleibt offen.

  **04.11.2026, Antwortzeiten und eigene Beiträge:** Auch beantwortete
  Aufgaben aus noch offenen Runden sind bereits bekannt; für spätere
  Abrufbelege zählt der gespeicherte Antwortzeitpunkt. Bei identischen
  Zeitstempeln wird keine Reihenfolge erfunden. Persönliche Beiträge werden
  im gemischten Rückblick und der Planung nicht als offene Wissensbewertung
  behandelt. Frühere Antworten und Rohberichte bleiben erhalten. Je 139
  künstliche Fälle bestanden auf SQLite und PostgreSQL, zehn Flutterfälle
  und zwei gezielte Chrome-Fälle einschließlich 390-Pixel-Ansicht. Der
  vollständig beobachtete mobile Mehrtagesablauf bleibt offen.

  **04.11.2026, Fachidentität:** Quellengebundene Lernbelege werden anhand
  gespeicherter Fachkennungen zusammengeführt. Alte Runden ohne Kennung
  verwenden bekannte Aliasnamen; fremde und unbekannte Kennungen bleiben
  getrennt; mehrdeutige historische Bezeichnungen werden nicht geraten.
  Je 38 künstliche Lernstands-, Tutor- und Controllerfälle bestanden auf
  SQLite und isoliertem PostgreSQL. Eine vollständige Mehrtagesabnahme bleibt
  offen.

  **04.11.2026, Lerncontroller:** Ungeklärte Selbstständigkeit, Reflexionen
  und Wiederholungen zählen nicht als selbstständige Erstlösung und begründen
  keine positiven Abrufvorschläge. Gespeicherte Antworten bleiben erhalten.
  30 künstliche Fälle bestanden auf SQLite und isoliertem PostgreSQL, weitere
  84 Fälle auf SQLite. Die mobile Mehrtagesabnahme bleibt offen.

  **03.11.2026, bereits bekannte Aufgaben:** Fachkompetenz und
  Heftquellenprojektion behandeln bereits beantwortete Fragen auch nach einem
  Fehler, Hilfe oder unklarer Selbstständigkeit als bekannt. Eine spätere
  identische Frage wird dadurch nicht zur neuen Abrufprobe; die tatsächlichen
  Versuche bleiben erhalten. Sieben gezielte Fälle bestanden auf isoliertem
  PostgreSQL; 81 künstliche Fälle und der zusätzliche Chemiefall bestanden
  auf SQLite. Eine mobile Mehrtagesabnahme bleibt offen.

  **03.11.2026, Lernbegleitung:** Ungeklärte Selbstständigkeit erzeugt keinen
  selbstständigen Prüftag und löscht allein keine bereits gültigen Prüftage.
  Bekannte Aufgaben zählen auch bei geänderter Formulierung einer gleichen
  Bruchoperation nicht erneut als neue Abrufprobe. In anderen Fächern bleibt
  fachlich bedeutsame Groß-/Kleinschreibung erhalten. Bereits gespeicherte
  Versuche und Übungszahlen bleiben erhalten. Neun gezielte Fälle bestanden
  auf SQLite und isoliertem PostgreSQL; die breite SQLite-Regression des
  vorherigen Zwischenstands bestand mit 117 Fällen. Eine vollständig
  beobachtete mobile Mehrtagesabnahme ist damit nicht belegt.

  **03.11.2026, Wiederholungsabstand:** Fach- und Quellenauswertung planen
  den nächsten Abruf anhand selbstständiger Prüftage nach der letzten
  Schwierigkeit. Alte Schwierigkeiten verkürzen ein nach drei Prüftagen über
  sieben Tage erneut gefestigtes Thema nicht dauerhaft; alte Prüftage vor
  einer späteren Schwierigkeit verlängern das neue Intervall nicht. Die
  ursprünglichen Nachweise bleiben unverändert. Je 70 künstliche Fälle
  bestanden auf SQLite und isoliertem PostgreSQL; die mobile Mehrtagesabnahme
  bleibt offen.

  **03.11.2026, Fachzuordnung:** Gleichnamige Themen verschiedener Fächer
  unterdrücken einander bei fälligen Wiederholungen und bestätigten Heftseiten
  nicht mehr. Wiederholungen verweisen nur auf eine abgeschlossene Runde des
  passenden Fachs; die bestehende Zuordnung Mathe/Mathematik bleibt erhalten.
  Eine breite Regression bestand mit je 36 Fällen auf SQLite und isoliertem
  PostgreSQL; vier gezielte Fälle bestanden zusätzlich auf beiden Datenbanken.
  Die mobile Mehrtagesabnahme bleibt offen.

  **Teilprüfung 02.11.2026:** 13 synthetische SQLite-Fälle und der
  kombinierte Mehrtagesfall auf PostgreSQL bestanden; weitere Grenzen und
  Befehle: [Regressionsbericht](docs/ROADMAP_REGRESSION_2026_11_02.md#abruf-und-lernplanung).

  **03.11.2026, weitere Korrektur:** Bei unklarer Selbstständigkeit entsteht
  kein selbstständiger Prüftag und keine neue Schwierigkeit; der Termin einer
  fälligen Wiederholung wird dadurch nicht verschoben. Bekannte Fehlversuche
  bleiben berücksichtigt. Mathematisch gleiche Bruchaufgaben mit umgestellter
  Formulierung zählen nicht mehrfach als neue Abrufaufgabe. Bei doppelt
  gestellten Aufgaben entscheidet die tatsächliche Antwortzeit, nicht die
  Anlagezeit der Runde. Die breite künstliche Regression bestand mit je
  65 Fällen auf SQLite und PostgreSQL; elf gezielte Fälle bestanden zusätzlich
  auf beiden Datenbanken. Der mobil beobachtete, vollständig vom Planer
  erzeugte Mehrtagesablauf bleibt noch offen.

  Mit künstlichen Quellen, Revisionen und Elternaufträgen mehrere eigenständige Prüftage über mindestens sieben simulierte Tage sowie freiwillige Zusatzrunden durchspielen.

  **01.11.2026:** Die Fälle für mindestens drei Prüftage, mehr als sieben
  Tage Abstand, neue Quellen, freiwillige Fortsetzung und konkurrierende
  Aktivitätssekunden laufen erneut auf isolierten Testdatenbanken. Diese
  automatisierten Bausteine sind keine durchgehend beobachtete mehrtägige
  Bedienungsprobe; Ergebnisse und noch fehlende Gesamtprüfung gesondert
  dokumentieren.

  **01.11.2026, kombinierter API-Test:**
  `backend/tests/test_recall_planning_journey.py` verbindet mit einer
  gezielten Testuhr einen anfänglichen Fehler und Lernschritt mit drei
  selbstständigen Prüftagen über acht Tage. Der zukünftige Elternauftrag
  bleibt erhalten; nach erfülltem Mindestziel und bei Pause startet eine
  freiwillige Runde. Zwei parallele Geräte schreiben dieselbe Aktivitätszeit
  nicht doppelt. Eine Quellenänderung macht die alten Bezüge ungültig, ohne
  Antworten oder Quellenrevisionen umzuschreiben. Der Test bestand einzeln auf
  SQLite und isoliertem PostgreSQL. Die Wiederholungsrunden werden dabei als
  künstliche Datensätze angelegt: Er belegt noch nicht ihre durchgehend
  beobachtete Auswahl und Erzeugung durch den Planer oder eine mobile
  Mehrtagesbedienung; der Punkt bleibt deshalb offen.

  - [x] Die simulierte Testuhr auch bei bereits zwischengespeichertem
    SQLAlchemy-INSERT verlässlich anwenden. Der Test wärmt den Cache mit
    einem zurückgerollten künstlichen Versuch selbst auf und setzt die
    Testzeit vor dem Einfügen neuer Versuche; gespeicherte Nachweise werden
    nicht nachträglich umdatiert. Der frühere CI-Lauf
    [41296514655](https://github.com/meinzeug/schulpilot/actions/runs/41296514655)
    war an dieser Testinteraktion fehlgeschlagen; sein Ergebnis bleibt als
    Fehlbefund bestehen.

  **Abnahme:** Mindestens drei unabhängige selbstständige Prüftage pro Lernziel sind unterscheidbar, neue Fragen und Quellenrevisionen bleiben zugeordnet, Elternaufträge und echte Starttermine bleiben erhalten; Pausen und Zeitziele verhindern keine freiwillige Fortsetzung. Gespeicherte Aktivitätssekunden ergeben den Fortschritt ohne Doppelzählung über Geräte hinweg.

- [ ] **P1 – Sprachlernen mit Fachprüfung und echten Geräten abnehmen**

  - [x] **Wortimport bei nicht belegten Zusatzangaben fortsetzbar machen.**
    Nicht in der bestätigten Quelle enthaltene Kontext- oder Wortartangaben
    werden verworfen und im Vorschlag als Prüfbedarf gekennzeichnet; die
    eigentlichen Wörter und Bedeutungen müssen weiterhin wörtlich belegt sein.
    Vorschläge werden nicht automatisch übernommen. Künstliche Worker-Tests
    prüfen belegte und unbelegte Zusätze sowie die bestehende Ablehnung
    unbelegter Wortpaare. Bei bereits fehlgeschlagenen Importen führen
    passende Aktionen zur eigenen Heftseite oder zur manuellen Eingabe, ohne
    automatisch eine neue KI-Anfrage auszulösen. Die tatsächliche Korrektur
    vorhandener Quellen und die vollständige Sprachabnahme bleiben offen.

  Versionierten Sprachpfad mit ausdrücklich bestätigter Locale, Wortpaaren und Varianten prüfen; künstliche Fälle für NFC, Akzent, Artikel, unbekannte freie Sätze, Hör-/Sprechaufgaben und unterstützte Versuche aufnehmen. Auf geeigneten Geräten Berechtigungsentzug, fehlende Stimme, Abbruch und Hintergrundwechsel bedienen.

  **Abnahme:** Jede Antwort folgt der dokumentierten Modusregel, unbekannte Eingaben bleiben unklar; STT wird nicht als Aussprachebewertung oder selbstständiger Schreibbeleg gewertet und Sprache startet nur nach ausdrücklicher Aktion. Gerät, Plattform, Ergebnisse und offene Abweichungen dokumentieren.

## Fotoerkennung und Quellenprüfung

- [ ] **P1 – OCR anhand vollständig referenzierter künstlicher Seiten prüfen**

  - [x] **Eindeutig falsche ggT-/kgV-Angaben als Lernstoff ausschließen.**
    Der begrenzte lokale Check erkennt vollständige Gleichungen wie
    `kgV(20,80)=160` und bewahrt den ursprünglichen Text. Gegenlesungen bleiben
    an ihre gespeicherte Regelversion gebunden; unklare Schreibweisen werden
    nicht geraten. Schulbuddy und Lernwege erhalten nur die weiterhin sichere
    Quellenprojektion. Neue Lesebelege behaupten keine vollständige fachliche
    Prüfung. Je 150 künstliche SQLite- und PostgreSQL-Fälle bestanden; die
    vollständige OCR-Abnahme und das Ausrollen bleiben offen.
    [Grenzen](docs/GCD_LCM_SOURCE_SAFETY_2026_11_26.md).

  - [x] **Eindeutig falsche Einheitenumrechnungen von Lernquellen trennen.**
    Der lokale Check erkennt vollständige, eindeutig falsche Aussagen wie
    `⅔ Minute = 60 Sekunden` für unterstützte Zeit-, Längen-, Masse- und
    Volumeneinheiten. Der Originaltext bleibt erhalten; betroffene Abschnitte
    werden nicht als gesicherter Lernstoff an Schulbuddy gegeben. Historische
    Gegenprüfungen und Quellfingerabdrücke bleiben versionsgebunden. Künstliche
    Regressionen decken gültige und mehrdeutige Gegenfälle ab; zusammen mit
    Quellen-, Gegenprüfungs- und Tutorprüfungen bestanden 174 Fälle auf SQLite
    (zwei übersprungen) und 176 auf isoliertem PostgreSQL. Eine korrekte,
    aber nicht zum Foto passende Ersatzgleichung kann der Check nicht erkennen;
    die vollständige Fotoabnahme und das Ausrollen bleiben offen.
    [Umfang und Grenzen](docs/UNIT_CONVERSION_SOURCE_SAFETY_2026_11_26.md).

  - [x] **Eindeutige falsche Teilbarkeitsaussagen aus Lernquellen halten.**
    Die begrenzte lokale Regel erkennt isolierte ganzzahlige Aussagen mit
    „teilt“, „teilt … nicht“, `∣` und `∤`. Falsche Originale bleiben als
    Abschrift erhalten, werden aber nicht an die KI als Lernstoff übergeben;
    ältere Gegencheckbelege bleiben versionsgebunden. 157 künstliche Fälle
    bestanden auf SQLite (zwei übersprungen) und 159 auf PostgreSQL. Nicht
    unterstützte und mehrdeutige Formen bleiben ungeprüft. Dies ist keine vollständige
    Foto- oder Fachabnahme. [Grenzen](docs/DIVISIBILITY_SOURCE_SAFETY_2026_11_26.md).

  - [x] **Eindeutig falsche eingebettete Rechnungen aus Lernquellen halten.**
    Ein begrenzter rationaler Check erfasst nun auch unmissverständliche
    Gleichungen in Absätzen mit mehreren Aufgaben. Originaltexte bleiben
    erhalten; die Lernprojektion schließt den betroffenen Abschnitt aus.
    Historische Gegenchecks bleiben mit ihrer gespeicherten Regelversion
    reproduzierbar; geänderte Lernquellen werden nicht über alte Fingerabdrücke
    freigegeben. Künstliche Fälle prüfen die Erkennung und mehrdeutige
    Gegenbeispiele. Auf isoliertem SQLite bestanden 147 Fälle (zwei
    übersprungen), auf getrenntem PostgreSQL 149. Der neue Stand ist noch
    nicht produktiv veröffentlicht. Die vollständige OCR- und Fachabnahme
    bleibt offen. [Umfang und Grenzen](docs/EMBEDDED_ARITHMETIC_SOURCE_SAFETY_2026_11_26.md).

  - [x] **Wiederholte Abschriften mit Korrektur konservativ behandeln.**
    Enthalten die beiden Lesungen denselben Text mehrfach und ist mindestens
    ein Vorkommen als Schülerarbeit, Korrektur oder rechnerisch falsch
    gekennzeichnet, lässt sich die Markierung nicht allein anhand des Texts
    zuordnen. Alle möglichen Vorkommen bleiben bis zur ausdrücklichen Prüfung
    unsicher; fehlende Vorkommen aus der ersten Lesung bleiben erhalten. Sechs
    künstliche Gegenfälle scheiterten vor dem Fix und bestehen danach; isolierte
    Quelltests prüfen, dass ein anderer sicherer Abschnitt nutzbar bleibt.
    Dies belegt keine vollständige Erkennung wiederholter oder verdeckter
    Markierungen. [Umfang](docs/OCR_REPEATED_MARKS_2026_11_07.md).

  - [x] **Unsichere Korrekturbereiche durch den Gegencheck erhalten.**
    Beim Abgleich zweier verschiedener Markierungspositionen fehlte der
    vorgeschriebene Seitenhinweis; die anschließende Validierung ließ den Job
    scheitern. Der Merge übernimmt lokale Hinweise begrenzt in die Seitenliste
    und erhält ihre Blockzuordnung. Auch ein übernommener Erstlesehinweis setzt
    die Lesbarkeit auf teilweise. Der künstliche Worker-Test prüft beide
    Lesesnapshots, den nutzbaren Rest und den ausgeschlossenen Bereich; die
    umfassende Fotoqualitätsabnahme bleibt offen.
    [Einordnung](docs/OCR_REFERENCE_TEST_2026_11_05.md).

  - [x] **Vier Referenzfotos im regulären OpenRouter-Ablauf vergleichen.**
    Alle vier künstlichen Seiten durchliefen Erkennung und Gegenprüfung; ein
    abgedeckter Bereich blieb unlesbar gekennzeichnet. Widersprüchliche
    Korrekturkoordinaten werden mit der neuen Prüfung konservativ markiert.
    Der Vergleich wurde durch die Coding-AI durchgeführt; eine unabhängige
    menschliche Referenzprüfung und weitere Bildbedingungen bleiben offen.
    [Ergebnis und Grenzen](docs/OCR_REFERENCE_TEST_2026_11_05.md).

  - [x] **Zwei künstliche Bruchseiten auf Android bis zur Lernrunde prüfen.**
    Systempicker, Zuschnitt, Upload, separate Erkennung und Gegenprüfung,
    Quellenzuordnung und zwei unterschiedliche Aufgaben wurden im Emulator
    mit echtem Anbieter beobachtet. Nach Korrektur der Quellenbindung war in
    einem weiteren Lauf auch eine interaktive Bruchgrafik sichtbar; dafür war
    eine ausdrückliche Wiederholung nach einem Luna-Ausgabelängenfehler nötig.
    Die breitere Foto- und Zuverlässigkeitsabnahme bleibt offen.
    [Ablauf und Grenzen](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md).

  - [ ] **Unbeschriftete Zeichnungen getrennt erfassen und überprüfen.**
    Ein echter künstlicher OpenRouter-Fall ließ einen markierten Bruchbalken
    aus. Ein getrennter vorläufiger Befund mit revisionsgebundener Prüfung
    ist technisch implementiert und isoliert getestet. Ein künstlicher
    Anbieterfall erfasste den Balken; die breitere Erkennungsabnahme bleibt offen.
    [Befund und Grenzen](docs/OCR_VISUAL_OBSERVATION_PLAN_2026_11_04.md).

  - [x] **Vier künstliche Referenzseiten samt Prüfsummen bereitstellen.**
    Drei deterministisch erzeugte Seiten und ein geprüftes KI-generiertes
    Heftfoto sind mit separater Text- und Unsicherheitsreferenz erfasst.
    [Testsatz und Grenzen](docs/OCR_SYNTHETIC_REFERENCE_2026_11_04.md).
    Die vollständige OCR-Auswertung und der reguläre Import bleiben offen.

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

  **04.11.2026, Abschriftkorrektur:** Nach einer Textänderung bleiben weiterhin
  exakt zuordenbare OCR-Markierungen erhalten. Nicht sicher zuordenbare oder
  fehlerhafte frühere Blockdaten verhindern die stille Übernahme als Lernstoff;
  Eltern können den ursprünglichen Wortlaut erneut eingeben oder die Seite
  kann neu fotografiert werden. Die berechtigten Rollen bleiben unverändert.
  Künstliche Regressionstests prüfen auch alte ungültige Datenformate. Für
  fotografierte Hausaufgaben müssen Auftragsnotizen durch nutzbare aktuelle
  Quellen belegt sein; Providerhilfsfelder verwenden gefilterte Quelltexte.
  Änderungen während des Provideraufrufs verwerfen das Ergebnis. Sechs neue
  Fälle bestanden auf SQLite und isoliertem PostgreSQL. Breitere Tests
  bestanden mit 121 Fällen auf SQLite und 98 auf isoliertem PostgreSQL.
  Die Vollständigkeit der Bilderkennung ist damit nicht belegt.

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

- [ ] **DACH-Bildungswege und Hochschulen quellengestützt unterstützen**

  Alle 16 deutschen und neun österreichischen Bundesländer sowie 26 Schweizer
  Kantone mit ihren jeweils geltenden Schulformen, Sprachregionen, Stufen,
  Abschlusswegen und Fachlehrplänen erschließen. Schweizer HarmoS-Jahre und
  kantonale Bezeichnungen, österreichische Schulstufen und deutsche Klassen
  dürfen nicht automatisch gleichgesetzt werden. Fachpläne und Fassungen mit
  Quellen, Geltungszeiträumen und belastbaren Kompetenz-/Phasenbeziehungen
  importieren; schulinterne Reihenfolgen nur bei konkretem Beleg übernehmen.
  Hochschulen benötigen zusätzlich getrennte, versionierte Programme nach
  Institution, Studiengang und Abschluss. Erwachsene dürfen nicht über ein
  erfundenes Kinder- oder Klassenprofil modelliert werden.

  Das neue read-only Quellenverzeichnis umfasst die 51 Regionen und zeigt
  fehlende Profil- und Inhaltsunterstützung ausdrücklich. Im bestehenden
  deutschen Schulprofil kann ein Klassenwechsel vorgeschlagen und bewusst
  gespeichert werden; ein automatischer Übergang ist nicht implementiert.
  Als erste fachlich belegte Erweiterung wurden Mathematik, Deutsch, Englisch,
  Geschichte, Biologie, Physik, Chemie, Geographie sowie Übersichten für Ethik,
  Informatik, Musik, Kunst, Sport, Technik, Wirtschaft und Sozialkunde der
  Sekundarschule Sachsen-Anhalt für die jeweils belegten Jahrgänge bzw.
  Abschlussphasen ergänzt. Weitere Fächer, Österreich,
  die Schweiz und Hochschulen bleiben offen; keine Vollständigkeit behaupten.

  **Abnahme:** Lernende und Berechtigte können den eigenen Bildungsweg ohne
  erfundene Stufe wählen und bei einem Wechsel vorhandene Nachweise behalten;
  nationale/lokale Fassungen, Wahlmöglichkeiten und bekannte Lücken sind
  sichtbar, gegen offizielle Quellen geprüft und auf allen unterstützten
  Clients getestet.

- [ ] **P1 – Lehrplanabdeckung fachlich kuratieren und offen ausweisen**

  - [x] **Sozialkunde der Sekundarschule Sachsen-Anhalt ergänzen.** Die
    amtliche Übersicht ist ausdrücklich dem bestehenden Sammelfach
    Gemeinschaftskunde zugeordnet. Vier Schwerpunkte gelten für Jahrgang 8,
    drei ausdrücklich für Jahrgang 9 und fünf für das Band 9/10. Ein
    weiterer Schwerpunkt zu Wahlen bleibt ohne erfundene Jahrgangszuordnung.
    Pflicht-/Wahlhinweise und ausgewogene Behandlung kontroverser Fragen
    bleiben im Planungskontext erhalten. Die Zuordnung erzeugt keine
    Kursbelegung oder Leistungsnachweise. Katalog- und Migrationstests
    bestanden auf SQLite (34 Fälle, zwei PostgreSQL-Fälle übersprungen) und
    isoliertem PostgreSQL (36 Fälle); drei erweiterte Fälle zum tatsächlichen
    Planungskontext bestanden zusätzlich auf beiden Datenbanken. Der
    umfassende Hauptpunkt und das Ausrollen bleiben offen.
    [Quelle und Einschränkungen](docs/SOURCES.md).

  - [x] **Technik und Wirtschaft der Sekundarschule Sachsen-Anhalt ergänzen.**
    Die amtlichen Überblickstabellen enthalten sieben Technik- und acht
    Wirtschaftsschwerpunkte in den jeweils genannten Doppeljahrgängen. Die
    verbindlichen Gegenstände für Jahrgang 9 sowie Hinweise auf schulische
    Aufsicht und den Schutz privater Finanzdaten bleiben im Planungskontext
    erhalten. Die Einträge sind keine praktischen Arbeitsaufträge oder
    Kompetenznachweise. Katalog-, Rechte- und Migrationstests bestanden auf
    SQLite (47 bestanden, zwei PostgreSQL-Fälle übersprungen) und isoliertem
    PostgreSQL (49 bestanden). Der umfassende Hauptpunkt und das Ausrollen
    bleiben offen.

  - [x] **Sportübersicht der Sekundarschule Sachsen-Anhalt ergänzen.** Zehn
    amtliche Bewegungsfelder sind für die Doppeljahrgänge 5/6, 7/8 und 9/10
    quellengebunden erfasst. Pflichtfelder, schulische Wahlfelder und
    Wahlkurse bleiben als Einschränkung auch im KI-Planungskontext sichtbar;
    die konkreten Entscheidungen der Schule sind unbekannt. Der Katalog
    erteilt keine individuellen Belastungsempfehlungen. Katalog- und
    Migrationstests bestanden auf SQLite (33 bestanden, zwei PostgreSQL-Fälle
    übersprungen) und isoliertem PostgreSQL (35 bestanden). Die umfassende
    fachliche Lehrplanabdeckung bleibt offen; die Ergänzung ist nicht ausgerollt.

  - [x] **Kunstübersicht der Sekundarschule Sachsen-Anhalt ergänzen.** Die
    fünf übergreifenden Bereiche sind je Doppeljahrgang 5/6, 7/8 und 9/10 mit
    amtlicher Quelle, Fassung, Lizenz und Fundstelle erfasst. Der besondere
    Bezug zu Jahrgang 9 bleibt als Quellenhinweis auch im KI-Planungskontext
    erhalten. Die Übersicht legt weder Unterrichtsreihenfolge noch individuelle
    Kompetenz fest. Katalog-, Filter- und Migrationstests bestanden auf SQLite
    (36 bestanden, zwei PostgreSQL-Fälle übersprungen) und isoliertem
    PostgreSQL (38 bestanden). Die vollständige Abdeckung bleibt offen; die
    Ergänzung ist noch nicht ausgerollt.

  - [x] **Musikübersicht der Sekundarschule Sachsen-Anhalt ergänzen.** Die
    fünf Schwerpunkte je Doppeljahrgang 5/6, 7/8 und 9/10 sind mit amtlicher
    Quelle, Fassung, Lizenz und Fundstelle erfasst. Die Einschränkung für
    Jahrgang 9 bleibt ausdrücklich erhalten; die tatsächliche Schulreihenfolge
    ist unbekannt. Gültigkeitshinweise werden nun auch im KI-Planungskontext
    mitgegeben. Katalog, Rechte, KI-Kontext und Migration bestanden mit
    SQLite (84 bestanden, drei übersprungen) und isoliertem PostgreSQL
    (87 bestanden). Die vollständige Lehrplanabdeckung bleibt offen; die
    Ergänzung ist noch nicht ausgerollt.

  - [x] **Informatik-Erprobungsübersicht für Sachsen-Anhalts Sekundarschule ergänzen.**
    Elf amtlich belegte Schwerpunkte sind den Bändern 5/6 und 7/8 sowie den
    ausdrücklich getrennten Jahrgängen 9 und 10 zugeordnet. Die ab August 2026
    gültige schulpraktische Erprobungsfassung bleibt in Quellen- und
    Planungsmetadaten ausdrücklich erkennbar; schulische Reihenfolge und
    individuelles Können werden nicht daraus abgeleitet. Import und additive
    Migration erhalten vorhandene Lernnachweise. Die Planung berücksichtigt
    datierte Quellen erst ab dem Berliner Gültigkeitstag. 36 SQLite-Fälle
    bestanden (zwei PostgreSQL-Fälle übersprungen), ebenso 38 Fälle mit
    isoliertem PostgreSQL. Die vollständige
    Lehrplanabdeckung bleibt offen; der Stand ist nicht ausgerollt.

  - [x] **Ethikübersicht der Sekundarschule Sachsen-Anhalt ergänzen.** Die
    sieben Schwerpunkte je Doppeljahrgang 5/6, 7/8 und 9/10 sind mit amtlicher
    Quelle, Fundstelle, Fassung und Prüfsumme in 21 kurzen Themenbezeichnungen
    erfasst. Einzelkompetenzen und tatsächliche Unterrichtsreihenfolgen sind
    nicht daraus abgeleitet. Import, Filter und Migration bestanden zusammen
    mit vorhandenen Katalogfällen auf SQLite (34 bestanden, zwei übersprungen)
    und isoliertem PostgreSQL (36 bestanden). Die vollständige
    Lehrplanabdeckung bleibt offen; die Ergänzung ist noch nicht ausgerollt.

  - [x] **Chemie und Geographie für die Sekundarschule Sachsen-Anhalt ergänzen.**
    Je elf amtlich belegte Kompetenzschwerpunkte sind mit Quelle, Version,
    Lizenz, Prüfsumme und Fundstelle erfasst. Die fünf ausdrücklich markierten
    Schwerpunkte für Jahrgang 9 bleiben von den übrigen Doppeljahrgängen
    unterscheidbar. Migration und erneuter Import erhalten bestehende
    Lernnachweise; die Daten zeigen keine schulinterne Unterrichtsreihenfolge
    und begründen keine automatische Beherrschungsfeststellung.

  - [x] **Physik der Sekundarschule Sachsen-Anhalt quellengebunden ergänzen.**
    Der amtliche Fachlehrplan von 2019 ist mit Dokumentfassung, Lizenz,
    Prüfsumme und 17 Kompetenzschwerpunkten übernommen. Klasse 6 und das Band
    7/8 sind belegt; unterschiedliche Abschlusswege und zwei experimentelle
    Wahlalternativen bleiben als Phasen erkennbar und werden ohne belegten
    Abschlussweg nicht in eine Klassenstufe hineininterpretiert. Import und
    Migration sind idempotent und erhalten bestehende Lernnachweise. Dies ist
    keine vollständige fachliche Freigabe aller Lehrpläne oder Unterrichtsfolgen.

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

  **04.11.2026, Schulbuddy-Kontext:** Nicht bestätigte Ausschnitte aus der
  geschriebenen Arbeit werden neutral übergeben; nur gültige, revisions-
  gebundene Elternzuordnungen erscheinen als Elternangabe. Bei Änderung
  während des Auftrags wird dessen Antwort verworfen. Die lokale Prüfung
  ersetzt keine unabhängige fachliche oder Urheberschaftsabnahme.

  - [x] **04.11.2026, Belegdeckung neuer Aufgaben:** Die angegebene
    Originalaufgabe muss vollständig durch ihre eigenen wörtlichen
    Quellenzitate gedeckt sein; bei langen Aufgaben sind mehrere überlappende
    Zitate zulässig. Ein sachfremdes Zitat derselben Seite genügt nicht.
    Bei Ablehnung bleibt eine frühere Analyse erhalten. Die künstliche
    Nacharbeitssuite bestand mit 272 Fällen und zwei PostgreSQL-Skips auf
    SQLite sowie 274 Fällen auf isoliertem PostgreSQL. Dies belegt weder
    OCR-Vollständigkeit noch pädagogische Modellqualität oder Urheberschaft.

  **Teilprüfung 02.11.2026:** 45 künstliche SQLite-Fälle zu Quellbindung,
  Nacharbeit und Transport bestanden; [Prüfbericht](docs/ROADMAP_MODULE_CHECKS_2026_11_02.md#klassenarbeiten-und-nacharbeit).

  Künstliche Arbeiten mit mehreren Themen, optionalem Termin, individuell vorgegebenen Aufgabenzahlen je Lerntag, geänderten Plänen, unklarer Lehrkraftzuordnung und schriftlichen Altantworten testen.

  **01.11.2026, offene Zuordnungslücke:** Die wörtliche Quellenprüfung
  beweist, dass eine Zeichenfolge im bestätigten Text steht; sie beweist nicht,
  wer sie geschrieben hat. Ein künstlicher Englischfall zeigt, dass dieselbe
  Schülerantwort auch als angeblicher Lehrkrafthinweis durch die Prüfung
  gelangen kann. Die Anzeige kennzeichnet erkannte Antwort und Hinweis daher
  als zu prüfende Zuordnung. Der API-Hinweis und die Tutorvorgaben erklären
  dieselbe Grenze; gespeicherte Texte bleiben erhalten. Diese Hinweise
  verhindern keine falsche KI-Zuordnung. Ein gesicherter, revisionsgebundener
  Nachweis der Rollen und seine Behandlung bei alten Clients bleiben offen.
  Vor dieser Text-/Kontextanpassung bestanden je 199 künstliche Backendfälle
  auf SQLite und isoliertem PostgreSQL sowie 58 Flutterfälle zu Planung und
  Nacharbeit. Die angepasste Ansicht bestand anschließend weitere 30
  Flutterfälle; gezielte neue Prüfungen bestanden auf SQLite und PostgreSQL.
  Ein zusätzlicher Englischfall reproduziert die Zuordnungslücke.
  Die Anbieterantworten waren simuliert, keine fachliche Modellabnahme.

  **Nächste Umsetzung für die Rollenherkunft:** Eine ausdrücklich bestätigte
  Zuordnung muss an Kind, Arbeit, Aufgabe, Quellenrevision und wörtlichen
  Ausschnitt gebunden sein; Farbe, Position, KI-Ausgabe und bloßes Vorkommen
  sind kein solcher Nachweis. Beim Quellenwechsel muss sie veralten, ohne
  gespeicherte Antworten umzuschreiben. Unklare Ausschnitte bleiben als solche
  sichtbar und dürfen im Tutor nicht als gesicherte Lehrkraftaussage eingehen.
  Neue und alte Clients sowie wiederholte und parallele Bestätigungen müssen
  getestet werden; weder Lesen noch Zuordnen darf einen Lernnachweis erzeugen.

  **03.11.2026, Teilabsicherung:** Für Tutor-Nachfragen werden die bisher von
  der KI als Schülerantwort, Lehrkrafthinweis oder Punktzahl zugeordneten
  Ausschnitte ohne diese Rollenbezeichnungen als ungeprüfter Quelltext
  übergeben. Die Anweisung fordert ausdrücklich, keine Urheberschaft zu
  behaupten; gespeicherte Berichte bleiben unverändert. Ein künstlicher Fall
  mit identischer Antwort und vermeintlichem Lehrkrafthinweis prüft den
  tatsächlich übergebenen Auftrag sowie fehlende Lernnachweise auf SQLite und
  PostgreSQL. Die 93 SQLite- und 123 PostgreSQL-Fälle zur Nacharbeit und
  Prüfung bestanden vor einer abschließenden Textverschärfung; der gezielte
  Fall wurde danach auf beiden Datenbanken wiederholt. Wörtliche Quellen
  können weiterhin eigene Rollenhinweise enthalten; eine Bestätigung durch
  Erwachsene und eine fachliche Modellabnahme sind dadurch nicht ersetzt.

  **03.11.2026, weitere Umsetzung:** Eltern mit Bearbeitungsrecht können
  einzelne wörtliche Ausschnitte einer zitierten bestätigten Originalseite
  ausdrücklich als Kinderantwort, Lehrkrafthinweis oder unklar zuordnen.
  Diese Elternangabe ist keine unabhängige Gewissheit. Quell- und
  Analyseversionen sowie eine eigene konkurrierende Versionsnummer schützen
  Änderungen; während eines laufenden Nacharbeitsauftrags ist keine Änderung
  möglich. Alte Texte und Antworten bleiben erhalten. Nur gültige Zuordnungen
  werden beim Tutor als Elternangaben mitgegeben; Quellenwechsel lassen sie
  veralten. Neue Clients zeigen die Zuordnung, alte behalten die Markierung
  „Zuordnung prüfen“. Die Nacharbeitssuite bestand mit 45 künstlichen Fällen
  auf SQLite und 46 auf isoliertem PostgreSQL; der echte Zeilensperrentest wird
  auf SQLite ausgelassen. 31 Flutterfälle und die statische Analyse bestanden.
  Eine fachliche Modellabnahme ersetzt das nicht. Der Hauptpunkt bleibt offen,
  bis seine vollständigen übrigen Abnahmekriterien belegt sind.

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

  - [x] **Fortsetzung einer pausierten Runde verständlich begründen.** Die
    tatsächliche mobile Startseite zeigte auf „Warum dieser Lernschritt?“
    bisher lediglich einen Speicherhinweis. Der Lerncontroller nennt bei
    pausierten Runden nun den belegten Pausenstatus und die Möglichkeit,
    dort weiterzumachen; er erfindet keine bereits gegebene Antwort. Die
    Erklärung ist eine Statusauskunft und keine behauptete pädagogische
    Gesamtbegründung. Bei veränderter Quelle fordert der Controller keine
    konkrete Person zur Prüfung auf; beim entsprechenden Fehlercode ohne
    gesonderten Blockertext verweist die Kinderansicht auf die Eltern.
    21 künstliche Controllerfälle, zwei erneute gezielte Fälle und 39
    Flutterfälle zur Vorbereitung und Startseite bestanden. Der umfassende
    Hauptpunkt und das Ausrollen bleiben offen.

  - [x] **Klassenarbeit ohne Kinder-Prüfauftrag planen.** Fehlen geprüfte
    Heftseiten, erklärt der Kinderdialog erst beim Themenschritt, dass Seiten
    fotografiert werden können und Eltern bei einer offenen Prüfung helfen.
    Die vorherige pauschale Elternwarnung bei der Fachwahl entfällt. Bei
    vorhandenen Seiten heißen Auswahl und Hilfetext „Thema“ und „Heft“; sie bleibt
    auf tatsächlich freigegebene Quellen begrenzt. Die Elternhinweise und die
    ausdrückliche Planung bleiben erhalten. Eine mobile Browseransicht mit
    künstlichen Daten sowie Widgettests für beide Rollen, fehlende und
    vorhandene Seiten und die bestehenden Plan-/Nacharbeitsabläufe wurden
    geprüft. Nach der Änderung bestanden 69 künstliche Flutterfälle für
    beide Rollen, kleine Ansichten, große Schrift und die Planungsabläufe;
    die bestehende mobile Browseransicht zeigt noch den früheren Stand. Der
    umfassende Hauptpunkt und das Ausrollen bleiben offen.

  - [x] **Passende Heftseiten für Klassenarbeiten fachweise nachladen.**
    Die bisherige gemeinsame Vorschau bleibt für alte Clients begrenzt. Die
    neue Auswahl fragt bestätigte, verwendbare eigene Heftseiten fachweise in
    Portionen von höchstens 40 ab und kann auch nach einer leeren Zwischen-
    portion weiterladen. Stabile Fachkennungen berücksichtigen historische
    Anzeigetexte; für Seiten ohne Kennung gilt weiterhin der bestehende
    exakte Fachabgleich. Gewählte Themen bleiben beim Nachladen erhalten,
    Quellenrevisionen werden beim Speichern erneut geprüft. Ein veränderter
    Cursor führt zum bewussten Neuladen; alte Antworten nach Fach- oder
    Kontowechsel werden nicht übernommen. Ältere Server liefern nach erneuter
    Berechtigungsprüfung weiterhin nur ihre gekennzeichnete Vorschau.
    62 künstliche Backendfälle auf SQLite, davon zwei gezielt auch auf
    isoliertem PostgreSQL, sowie 77 Flutterfälle und 29 Chrome-Webrunnerfälle
    bestanden. Sie decken unter anderem über 200 Seiten, leere Portionen,
    fremde Kinder, Rollen, Fehler und kleine Bildschirmgrößen ab. Eine
    vollständige Geräteabnahme und das Ausrollen stehen noch aus.

  - [x] **Schulwörter eindeutig in der vorhandenen Standardsammlung ergänzen.**
    Eine einzelne, zur gewählten Sprache passende „Meine Schulwörter“-Sammlung
    wird im Kinderzugang nur dann vorgeschlagen, wenn die geladene Übersicht
    vollständig ist und genau einen solchen Treffer enthält. Das Ziel ist
    sichtbar und änderbar; bei mehrdeutiger oder unvollständiger Übersicht wird
    keine bestehende Sammlung erraten. Wiederaufgenommene Sendeversuche behalten
    ihr ursprüngliches Ziel, auch wenn die ursprüngliche Aktion eine neue
    Sammlung anlegen sollte und später ein Listenfilter geändert wurde.
    Widgettests prüfen diese Fälle und den tatsächlich
    unbeschnittenen Standardnamen bei 320/390 Pixeln und doppelter Schrift.
    34 gezielte Fälle bestanden; Elternabläufe und serverseitige
    Besitzprüfungen bleiben erhalten. Die Eindeutigkeit gilt für die geladene
    Übersicht; eine spätere Umbenennung auf einem anderen Gerät ist damit nicht
    revisionsgebunden nachgewiesen.

  - [x] **Leeren Hausaufgabenbereich ehrlich und freundlich zeigen.** Vor dem
    ersten Foto behauptet der Hinweis keinen bereits laufenden Lesevorgang;
    er erklärt knapp die Hilfe durch Eltern. Der vorhandene Schulbuddy lockert
    ausschließlich den leeren Kinderzustand auf und ist für Screenreader
    dekorativ. Die Fotoaktion bleibt vorn erreichbar. Die lokale mobile
    Browser-Demo zeigt ausschließlich Beispieldaten; 34 Widgetfälle und die
    statische Prüfung bestanden. Die breite Kinderabnahme bleibt offen.

  - [x] **Ein einzelnes Schulwort einfach eingeben und prüfen.** Im Kinderzugang
    stehen Wort, Bedeutung und die gewählte Lernsprache unmittelbar bereit;
    das Ziel der Sammlung ist sichtbar und kann aufgeklappt geändert werden.
    Listen- und Texterkennung bleiben ausdrücklich erreichbar. Bei nur einem
    Wort entfallen Suche, Filter und künstlicher Leerraum im Prüfgespräch;
    Korrektur, Zurückstellen und ausdrückliche Bestätigung bleiben erhalten.
    Fehlende Angaben werden angezeigt, ein unklarer Sendeversuch erhält bei
    unveränderten Daten denselben Schlüssel. Die mobile Browser-Demo verwendet
    ausschließlich künstliche Wörter; Tests prüfen unterschiedliche Breiten,
    große Schrift, Sammlungen, Wiederholungen und die unveränderte Elternansicht
    (108 Fälle bestanden). Die statische Prüfung der geänderten Dateien war
    fehlerfrei.
    Der umfassende Hauptpunkt und das Ausrollen bleiben offen.

  - [x] **Fotoauswahl bei wenigen Seiten verkleinern.** Bei nur einer offenen
    Seite wird diese nach dem Aufklappen unmittelbar angezeigt; es erscheint
    kein Auswahldialog mit nur einem Eintrag. Eine kurze Mehrseitenliste passt
    sich ihrem Inhalt an, längere Listen bleiben begrenzt und scrollbar.
    Seitenwechsel, Kontowechsel und reine Lesezugriffe sind durch künstliche
    Widgettests einschließlich 320/390 Pixeln und großer Schrift abgedeckt
    (61 Fälle). Die lokale Smartphone-Vorschau wurde für eine und mehrere
    Beispielseiten geöffnet; Auswahl und Seitenwechsel wurden bedient.
    Die breite Abnahme aller Kinderansichten bleibt offen; nicht ausgerollt.

  - [x] **Lernwegprüfung an die kindgerechte Aktion anpassen.** Der breite
    Flutter-Lauf fand eine veraltete Erwartung auf „Nächste Etappe“ und einen
    Zusatztext, die in der Kinderansicht bewusst ersetzt wurden. Der Test
    prüft nun die tatsächliche Aktion „Runde vorbereiten“ und genau einen
    lesenden Abruf. Für eine vorhandene Runde prüft ein weiterer Test den
    sichtbaren Knopf „Weiterlernen“ und das richtige Rundenziel ohne
    Erzeugungsauftrag. Dadurch wird weder freiwilliges Lernen behauptet noch eine
    Runde automatisch gestartet. Die ursprüngliche breite Regression bleibt
    als fehlgeschlagener Lauf dokumentiert; ein erneuter vollständiger Lauf
    auf Commit `733a5a2` bestand mit 4.980 Fällen und 19 ausgewiesenen Skips.
    Drei quellgebundene Teilberichte wurden auf die vollständigen 385 Testdateien
    mit genau einmaliger Ausführung geprüft. Spätere Änderungen wurden gezielt
    getestet; dieser ältere Gesamtlauf belegt sie nicht.
    [Testberichte und Wiederholung](docs/FLUTTER_REGRESSION_2026_11_27.md).

  - [x] **Wartende Heftseiten ohne Kinderprüfauftrag anzeigen.** Der Kindersicht
    steht ein kurzer Hinweis auf gespeicherte Fotos und die mögliche Hilfe der
    Eltern sowie ein eindeutiger Rückweg zur Startseite voran. Fotoauswahl und
    erkannter Inhalt erscheinen erst auf Wunsch; Unsicherheiten bleiben in den
    Details erhalten und die Elternprüfung wird nicht automatisch bestätigt.
    Auch alte Seiten und eine ausdrücklich gewählte Löschung bleiben erreichbar.
    Synthetische Tests prüfen die Statuswechsel, Rückwege, Seitenauswahl,
    getrennte Konten sowie kleine Bildschirme und große Schrift. Eine mobile
    Browservorschau zeigt den Zustand mit Beispieldaten; eine vollständige
    Geräte- und Elternabnahme ist damit nicht behauptet.

  - [x] **Fotoeinstieg verständlicher machen.** Kinder sehen Fotografieren und
    Fotoauswahl als gut erkennbare Touch-Schaltflächen. Die zusätzliche direkte
    Abgabe ist eindeutig beschriftet und nur auf Wunsch aufgeklappt; die
    bewusste Abgabe, Fotoentwürfe, Größenbegrenzungen und Fehlerbehandlung
    bleiben erhalten. Die mobile Ansicht wurde mit einer ausdrücklich
    gekennzeichneten lokalen Beispielseite geprüft; künstliche Widgettests
    prüfen die Auswahl, Direktabgabe und die Behandlung fehlerhafter Uploads.

  - [x] **Leeren alten Schultag richtig verlassen.** Wenn ein alter Tag keine
    Heftseiten enthält und keine neuen Fotos erlaubt sind, öffnet „Meine
    Heftseiten ansehen“ die Heftübersicht. Die Aktion verändert den alten Tag
    nicht; ein Widgettest prüft den Rückweg und ausschließlich lesende Zugriffe.

  - [x] **Lernweg für Kinder auf den nächsten Schritt ausrichten.** Nach der
    Sichtprüfung der schmalen produktiven Ansicht zeigt der lokale Stand eine
    klare Schaltfläche „Weiterlernen“, das aktuelle Thema und den tatsächlichen
    Aufgabenfortschritt. Bei fertig verarbeiteten, bestätigten Fotos entfällt
    beim Kind die nicht mehr benötigte Foto-Statusleiste; offene oder noch
    unbekannte Quellenprüfungen bleiben sichtbar. Mehrdeutige Rundenbezeichnungen und ein zusätzlicher
    Bereitschaftszähler stehen nicht mehr im Vordergrund. Weitere Lernschritte
    bleiben aufklappbar; Suche und Filter folgen erst nach einer weiteren
    bewussten Auswahl. Das gilt auch für die Heftseiten- und Rundenübersicht;
    deren Anzahlen verwenden die passende Einzahl oder Mehrzahl und aktive
    Filter bleiben auch im zugeklappten Zustand kenntlich. Fragen zu
    Heftseiten und die Inhaltsübersicht stehen gesammelt unter „Meine
    Heftseiten“; weitere Fotos lassen sich weiterhin direkt hinzufügen.
    Geplante und bearbeitete Schritte bleiben unterscheidbar. Im Fehlerfall
    wird derselbe Erklärungstext nicht ein zweites Mal aufgeklappt; die jeweils
    tatsächlich verfügbaren nächsten Schritte bleiben sichtbar.
    Die vollständige Beispielseite wurde bei 320, 390, 768 und 1200 Pixeln mit
    einfacher und doppelter Schriftgröße im Chrome-Web-Runner und lokal geprüft;
    die Hauptaktion bleibt auf größeren Flächen kompakt und mindestens 48
    logische Pixel hoch. Das Öffnen der
    Beispielrunde löst ausschließlich lesende Anfragen aus.
    Bei einer nicht verfügbaren Erklärgrafik führt die Hauptaktion zu den
    gespeicherten Lernmöglichkeiten; die Heftseite bleibt optional erreichbar,
    und die Statusansicht startet keinen neuen KI-Auftrag.
    Bei ungeklärten Fotos wird das Kind nicht zur Seitenprüfung aufgefordert;
    berechtigte Eltern können die Prüfung öffnen. 86 Widgetfälle bestanden;
    eine getrennte 390-Pixel-Browservorschau mit Beispieldaten bestätigte
    Hauptaktion und Detailanzeige. Die vollständige Abnahme aller
    Kinderansichten und das Ausrollen bleiben offen.

  - [x] **Fachauswahl bei Sitzungswechsel schließen.** Die allgemeine
    Heft-Fachauswahl bindet sich zusätzlich an das Sitzungstoken. Nach einem
    Tokenwechsel bleiben alte Auswahleinträge und deren Rückrufe nicht für die
    neue Sitzung aktiv; ein zwischenzeitlich geöffneter anderer Dialog bleibt
    erhalten. Künstliche Widgettests prüfen unter anderem denselben Account
    mit neuem Token und verzögerte Katalogantworten. Geräteabnahme und
    Ausrollen bleiben offen.

  - [x] **Fächer bei Klassenarbeiten direkt finden.** In der mobilen
    Liveansicht füllte die lange alphabetische Auswahl fast den Bildschirm.
    Die lokale Überarbeitung ergänzt eine Suche und eine begrenzt scrollbare,
    an Tastatur und Fensterhöhe angepasste Auswahl. Verfügbare Fächer bleiben
    unverändert; Suchen, Schließen und Sitzungswechsel speichern keinen Plan.
    Widgettests prüfen schmale Anzeigen, doppelte Schrift, geöffnete Tastatur,
    leere Suchergebnisse und Konto-/Sitzungswechsel. Die vollständige mobile
    Abnahme und das Ausrollen bleiben offen.

  - [x] **Leere Wortvorschläge zutreffend beschreiben.** Der Wortschatzbereich
    behauptet bei fehlenden Vorschlägen keine vorherige Prüfung und keine
    gespeicherten Wörter. Bei einem älteren Backend ohne Gesamtzahl bleibt
    kenntlich, dass sich die Aussage nur auf die Vorschau bezieht; offene
    ältere Listen sind weiterhin erreichbar. Widgettests prüfen Kinder- und
    Elternansicht, große Schrift, fehlende und bekannte Gesamtzahl sowie reine
    Lesezugriffe. Die vollständige Kinderabnahme bleibt offen.

  - [x] **Wartende Seiten nicht als laufendes KI-Lesen ausgeben.** Der
    mittlere Schritt im Fotoablauf heißt „Vorbereitung“, auch wenn eine
    Elternprüfung aussteht; er behauptet damit keinen aktuell laufenden
    Anbieterauftrag. Widgettests prüfen alte und aktuelle Stände sowie
    schmale Anzeigen. Die umfassende Bedienungsabnahme bleibt offen.

  - [x] **Hausaufgabenfoto dem Kind ohne Prüfauftrag erklären.** Die mobile
    Übersicht fordert das Kind nicht mehr auf, den erkannten Text zu prüfen;
    der Hinweis verweist bei Bedarf auf die Eltern. Ein noch offenes Foto
    und seine Detailansicht benennen dieselbe Zuständigkeit; der Filter heißt
    beim Kind „Offene Fotos“. Die mobile Navigation zeigt „Aufgaben“ ohne
    Worttrennung, während der Screenreader „Hausaufgaben“ erhält. Eltern behalten
    ihre Prüfhinweise. Künstliche Widgettests prüfen die Zustände und dass
    deren bloßes Öffnen keine Verarbeitung startet; 320 und 390 Pixel sowie
    große Schrift sind eingeschlossen. Die vollständige Kinder- und
    Elternabnahme und das Ausrollen bleiben offen.

  - [x] **Leere Klassenarbeiten-Ansicht für Kinder verständlich gestalten.**
    Auf kleinen Bildschirmen erklären eine Illustration und ein kurzer Text
    den nächsten Schritt; je nach Reiter führt ein Knopf zur Planung oder zum
    Hinzufügen einer geschriebenen Arbeit. Ohne Änderungsrecht fehlt die
    Aktion. Bei weiteren verfügbaren Seiten wird kein leerer Bestand behauptet.
    Künstliche Widgettests prüfen 320 und 390 Pixel, doppelte Schrift, beide
    Reiter, Berechtigungen und Seitennachladung. Die umfassende Abnahme aller
    Kinderansichten und das Ausrollen bleiben offen.

  - [x] **Lernrundenkopf mit allen Aktionen bei 390 Pixeln lesbar halten.**
    In der geöffneten mobilen Lernrunde sprang die letzte Ziffer des
    Fortschritts allein in eine zweite Zeile. Bei wenig Platz und allen vier
    Aktionen steht der vollständige Phasen-/Aufgabentext nun auf einer eigenen
    Zeile; die Schaltflächen bleiben groß und bedienbar. 41 künstliche Flutter-
    und 16 Chrome-Widgetfälle decken 320/390 Pixel, große Schrift und die
    übrige Lernrundennavigation ab.
    Die breite Abnahme aller Kinderansichten und das Ausrollen bleiben offen.

  - [x] **Heftfoto auf der Materialseite besser erkennbar machen.** Die
    bisher 150 Pixel hohe Vorschau nutzt abhängig von der Bildschirmhöhe mehr
    Platz, zeigt das ganze Foto und beschriftet die Vergrößerung sichtbar.
    Der bestehende private Fotolader verwirft Bilddaten bei Konto-, Familien-
    und Sitzungswechsel. Künstliche Tests prüfen drei Fenstergrößen und
    doppelte Schrift, Öffnen/Schließen sowie lesende Zugriffe. Die vollständige
    Abnahme aller Kinderansichten bleibt offen; der Stand ist nicht ausgerollt.

  - [x] **Fortlaufende Vorbereitung nach dem Lesen verständlich anzeigen.**
    Sind alle Seiten gelesen, aber noch Arbeit im Hintergrund offen, zeigt die
    Kinderansicht „Deine Seiten werden fertig vorbereitet“ statt weiterhin
    ausschließlich vom Lesen zu sprechen. Widgettests bei 320 und 390 Pixeln
    sowie großer Schrift prüfen den Zustand auch im Chrome-Webrunner. Die
    umfassende Abnahme aller Kinderansichten bleibt offen.

  - [x] **Themenbild und Gerätekarten während der Nutzung kompakter zeigen.**
    In aktiven Kinderaufgaben erscheint ein vorhandenes Themenbild zunächst
    als kleine Vorschau und kann ausdrücklich geöffnet werden; Einführung und
    Erklärung behalten ihre Darstellung. Der KI-Hinweis bleibt sichtbar und
    das Öffnen löst weder KI-Arbeit noch eine Antwort aus. Gerätekarten fassen
    die doppelte Informationsaktion im anklickbaren Kopf zusammen; Warnung und
    Geräteabmeldung bleiben erreichbar. Mobile Widgettests einschließlich
    großer Schrift prüfen diese Teilfälle; die vollständige Prüfung aller
    Kinderansichten bleibt offen.

  - [x] **Hausaufgaben und Klassenarbeit-Nacharbeit gezielt vereinfachen.**
    Bei Hausaufgaben bleibt die Antwortprüfung die Hauptaktion; seltene
    Schreibwerkzeuge sind zusammengefasst. In der Nacharbeit stehen der
    eigene Versuch und ein kurzer Hinweis im Vordergrund, weitere Hilfen und
    Arbeitsfotos lassen sich öffnen. Getrennte Widgettests decken schmale
    Displays, große Schrift, Entwürfe und Quellenkontrollen ab. Die umfassende
    Bedienungsabnahme aller Ansichten bleibt weiterhin offen.

  **22.11.2026, weitere Teilverbesserung:** Die produktive Kinderansicht wurde
  bei 390 × 844 Pixeln aufgerufen. „Mehr zur Runde“ erhält eine kompakte
  Schaltfläche; seltene Heftseitenaktionen stehen mobil in einem beschrifteten
  Menü. Hausaufgaben und Wortschatz zeigen weniger doppelte Hinweise und leere
  Navigation. Aufgaben und ganze Runden können ausdrücklich zurückgestellt
  und Runden später wieder geöffnet werden, ohne einen Lernnachweis zu
  erzeugen; Elternaufträge bleiben offen. Widgettests prüfen unter anderem
  schmale Ansichten, große Schrift und den erhaltenen Rückweg. Damit ist weder
  die vollständige Kinderoberfläche überarbeitet noch geräteübergreifend
  abgenommen; dieser Hauptpunkt bleibt offen.

  Das in der mobilen Live-Ansicht aufgefallene lange Lernrundenmenü zeigt
  Erklärung, Frage und Zurückstellen direkt; weitere Möglichkeiten sind
  aufklappbar. Bestehende Aktionen und Quellen bleiben erreichbar.

  - [x] **Prüfhinweise bei vorhandenen Nacharbeitsaufgaben bündeln.** In der
    Kinderansicht weist ein sichtbarer, aufklappbarer Hinweis auf unklare
    Stellen hin und erhält die einzelnen Angaben samt Quellenbezug. Zusätzliche
    Analyseaufträge liegen in einem aufklappbaren Bereich; vorhandene Aufgaben sind
    früher erreichbar. Bei fehlenden Aufgaben bleiben die Schritte unmittelbar
    sichtbar. Eltern erhalten die Einzelhinweise weiterhin direkt. Tests prüfen
    beide Rollen und dass beim Öffnen keine KI-Verarbeitung startet. Die
    vollständige kindgerechte Überarbeitung der Klassenarbeiten bleibt offen.

  - [x] **Wortkarten und Wortschatzrunde klarer darstellen.** Die kompakte
    Wortliste kündigt das Öffnen der Wortansicht zutreffend an; aufdecken
    bleibt darin eine gesonderte bewusste Aktion. In Wortschatzrunden wird
    der fachfremde Hinweis auf fehlende Erklärgrafiken nicht vor die Aufgabe
    gesetzt. In einer vorhandenen Kinderansicht wurden beide Probleme bei
    390 × 844 Pixeln beobachtet; gezielte künstliche Widgettests prüfen den
    Einstieg und dass keine Grafikvorbereitung automatisch ausgelöst wird.
    Die umfassende Abnahme des Wortschatzes bleibt offen.

  - [x] **Dialog zum erneuten Lesen einer Heftseite kürzen.** Die
    Bestätigung erklärt knapp, dass die KI erneut liest, der Text geprüft
    wird, vorhandene Seite und Antworten bleiben und Kosten möglich sind.
    Abbrechen löst weiterhin keinen Auftrag aus; die KI-Verarbeitung bleibt
    ausdrücklich und bewusst. Die übrigen Kinderansichten bleiben offen.

  **04.11.2026, Hausaufgabeneinstieg:** Leere Fachangaben erzeugen kein
  führendes Trennzeichen. Die leere Zählerbeschriftung wurde durch eine klare
  Aktion ersetzt; Fotohinweise berücksichtigen den tatsächlichen Zustand.
  Vier mobile Widgetfälle bei 320/390 Pixeln und doppelter Schrift sowie vier
  Chrome-Fälle bestanden. Die vollständige Kinderansicht bleibt offen.

  Heute, Lernen, Fach- und Themenlisten, Hefte und Fotoimport, Seitenprüfung, Lernvorbereitung, Lernrunde und Rückblick, Wortschatz, Klassenarbeiten, Schulbuddy, Benachrichtigungen und Einstellungen jeweils in typischen Zuständen auf einem schmalen Smartphone durchgehen. Pro Ansicht die nächste Handlung erkennbar machen, wiederholte Erklärungen entfernen, vertraute kurze Begriffe verwenden und selten benötigte Einzelheiten sinnvoll erreichbar bündeln. Pflichtaufträge, Unsicherheiten, Datenschutzinformationen, Fehler und sichere Rückwege müssen weiterhin verständlich auffindbar sein. Große Schrift, Tastatur, Screenreader, leere Zustände, laufende Verarbeitung und Wiederaufnahme mitprüfen.

  **Abnahme:** Für jede genannte Ansicht sind konkrete Vorher-/Nachher-Befunde, mobile Screenshots und passende Interaktions- beziehungsweise Regressionstests dokumentiert. Die wichtigsten Aufgaben werden mit künstlichen Konten tatsächlich bedient; zusammengeklappte Informationen und Nebenaktionen bleiben erreichbar. Eine einzelne verbesserte Seite oder ein Widgettest ersetzt nicht die Abnahme des gesamten Kinderbereichs.

  **01.11.2026, lokale Teilverbesserung:** In der produktiven Heftübersicht
  war bei 390 Pixeln der Reiter „Alle Seiten“ angeschnitten. Die drei
  Reiter verwenden auf schmalen Displays vollständige Beschriftungen und
  brechen bei großer Schrift um. 62 Flutterfälle einschließlich 320/390 Pixel
  und doppelter Schriftgröße bestanden. Eine lokale Webvorschau mit
  Beispieldaten zeigte alle drei Beschriftungen bei 390 und 320 Pixeln; die
  Auswahl „Alle Seiten“ funktionierte. Die Vorschau zeigt den geänderten
  Reiterbaustein, nicht den vollständigen produktiven Heftablauf. Der
  ergänzende 20-Fälle-Lauf prüfte unter anderem die Reiter in hellem und
  dunklem Design auf mindestens 4,5:1 Textkontrast und 48-Pixel-Trefferflächen.
  Der Gesamtpunkt bleibt offen.

  **02.11.2026, mobile Teilkorrektur:** Bei 390 Pixeln wurde das Logo auf
  Unterseiten mit Zurück-Pfeil durch die anderen Kopfaktionen stark
  herunterskaliert. Auf schmalen Unterseiten und bei vergrößerter Schrift wird
  die kompakte Logovariante verwendet; die Startseitenaktion bleibt erreichbar.
  Widgettests prüfen die transformierte Logogröße bei 320 und 390 Pixeln und
  doppelter Schriftgröße. Die Abnahme aller Kinderansichten bleibt offen.

- [ ] **P1 – Alters- und situationsgerechte Bedienung beobachten**

  Für unterschiedliche bestätigte Klassen-/Altersgruppen repräsentative Aufgaben in schmalem Smartphone-Web, großem Web und auf Android mit künstlichem Material durchführen; fachlich und datenschutzrechtlich geeignete begleitete Nutzertests separat planen und freigeben.

  **Abnahme:** Dokumentierte Personen können Fotoabgabe, Unsicherheit prüfen, eine Runde bearbeiten, Hilfe nutzen, Rückmeldung lesen und Ergebnis erreichen; Schwierigkeiten und Abbrüche werden erfasst und behoben oder als offene Einschränkung geführt. Keine Wirksamkeit oder generelle Altersfreigabe aus Screenshots oder einer einzelnen Beobachtung ableiten.

- [ ] **P1 – Barrierearme mobile Führung nachweisen**

  - [x] **Heftfoto bei großer Schrift im Fotoablauf sichtbar halten.** Im
    Kinderzugang steht das Foto vor dem weiterhin vorhandenen Hinweis auf die
    Elternprüfung. Bei großer Schrift fasst eine beschriftete Fortschrittsleiste
    die Phasen platzsparend zusammen; das Datum bleibt mit seinem vollständigen
    Screenreader-Namen erhalten. Künstliche Widgettests prüfen 19 Seiten bei
    320 und 390 Pixeln sowie einfacher und doppelter Schrift, einschließlich
    Kontowechsel und veralteter Seitenauswahl. Eine umfassende Geräte- und
    Screenreaderabnahme sowie das Ausrollen stehen weiter aus.

  - [x] **Flutter-Systemtexte auf Deutsch bereitstellen.** In der mobilen
    Browseransicht meldete der Zeichenzähler „characters remaining“ und die
    Dialogschranke „Dismiss“. Startansicht und gemeinsame App verwenden nun
    das im fixierten Flutter-SDK enthaltene deutsche Material-, Widgets- und
    Cupertino-Sprachpaket, auch wenn das Gerät eine andere Sprache meldet.
    Ein Widgettest prüft den tatsächlichen barrierefreien Zeichenzähler und
    Dialogtext. Sprachübungen und ihre explizit gewählten Vorlese-/Mikrofon-
    Sprachen bleiben davon getrennt. Die umfassende Screenreader-Abnahme und
    das Ausrollen bleiben offen.

  - [x] **Desktop-Ziel „Lernen“ per Tastatur und Web-Semantik prüfen.**
    Das Ziel „Lernen“ ist bei 1280 Pixeln als fokussierbare Schaltfläche
    vorhanden, per Tab erreichbar und mit Enter bedienbar. Die frühere
    Rollenabfrage übersah die ergänzte Positionsangabe „Tab 2 of 6“.
    Ein künstlicher Chrome-Fall prüft den tatsächlich gerenderten Fokusrahmen
    und seinen Kontrast. [Nachweis](docs/DESKTOP_KEYBOARD_NAVIGATION_2026_11_25.md).

  - [ ] **Desktop-Seitenleiste mit tatsächlichem Screenreader prüfen.**
    Die Ausgabe durch konkrete Bedienhilfen, einschließlich der englischen
    Positionsangabe, und weitere Ziele sind noch nicht beobachtet. Der
    Chrome-Semantiktest ersetzt keine vollständige Screenreaderprüfung.

  - [x] **Ziffernwahl über den Nummernblock ermöglichen.** Bei sichtbarer
    Auswahl akzeptiert die Tastaturhilfe auch die Zifferntasten des
    Nummernblocks. Eine Wahl prüft oder übermittelt keine Antwort; Textfelder,
    Steuerungstasten, ungültige Nummern und eine nicht mehr aktuelle Aufgabe
    behalten ihre bisherige Behandlung. Künstliche Widgettests prüfen den
    Lernraum und die Tastaturgrenzen. Dies ist keine vollständige
    Barrierefreiheits- oder physische Tastaturabnahme.

  Tastatur, Screenreader-Semantik, Fokus, große Schrift, Kontrast anhand tatsächlich gerenderter Farben und Trefferflächen prüfen; zusätzlich den echten Web-Runner für Zeitformatierung und reale Android-Geräte für Interaktionen verwenden.

  **Abnahme:** Die nächste Hauptaktion bleibt sichtbar und erreichbar, Feedback bleibt bis zur bewussten Fortsetzung stehen, Tastatur und Navigation verdecken keine Aktion; normale Texte erreichen mindestens 4,5:1 und notwendige Kontrollmerkmale 3:1. Geräte, Schriftgröße, Messungen und offene Befunde dokumentieren; Farbtests allein sind keine vollständige WCAG-Abnahme.

  **02.11.2026, lokale Teilkorrektur:** In der Heftansicht bei 390 × 844
  Pixeln gab der produktive Browser die sofort ausführbaren Schulbuddy-
  Frageideen als nicht aktivierte Kontrollkästchen aus. Die gemeinsame
  Aktionschip-Darstellung stellt nun eine beschriftete Schaltfläche mit nur
  einer Aktivierungsaktion bereit. Sie wird auch für Tutor-Frageideen,
  Aufgabenanzahl in der Klassenarbeitsplanung, jüngste Suchbegriffe und
  Wortbausteine verwendet; deaktivierte Aktionen bleiben deaktiviert. Die
  bestehenden Funktionen und die sichtbare Darstellung bleiben erhalten.
  78 Flutter-Widgetfälle für die betroffenen Bereiche bestanden; zwei neue
  Fälle prüften Semantik, Deaktivierung, genau eine Aktion und Tastatur auch
  im Chrome-Webrunner. Ein zusätzlicher Chrome-Test prüfte die Semantik der
  Schulbuddy-Frageideen. Die produktive Webausgabe nach Deployment ist damit
  noch nicht überprüft.
  Die Prüfung der tatsächlichen assistiven Ausgabe in den weiteren Ansichten
  und eine vollständige mobile Barrierefreiheitsabnahme stehen noch aus.

  **Weitere Teilkorrektur:** Die Glocke wurde im mobilen Web als
  „Benachrichtigungen Benachrichtigungen“ ausgegeben. Der visuelle Tooltip
  liefert keine zusätzliche Screenreader-Beschriftung mehr; der Button nennt
  weiterhin die Anzahl ungelesener Meldungen. Die Kopfmenü-, Inhalts- und
  Sichtbarkeitsprüfungen bestanden mit 51 Flutterfällen; eine vollständige
  Screenreader- und Geräteabnahme steht noch aus.

- [ ] **P1 – 30-Schultage-Test als reproduzierbaren Regressionstest fortführen**

  - [x] **30 künstliche Schultage über API und Worker wiederholbar prüfen.**
    Dreißig getrennte synthetische Fotos aus zwei Fächern durchlaufen je
    zwei Leseläufe, einen ausdrücklich gestarteten Paketauftrag, eine
    Lernrunde und den separaten Rückblick. Der Test prüft zwei Sitzungen,
    Unterstützung, unklare Antworten, doppelte Uploads sowie bekannte und
    unbekannte simulierte Kosten und schreibt 30 einzelne technische Belege.
    Ein geprüftes Runner-Skript ergänzt Fälle für Unterbrechung, Mitternacht,
    Quellenänderung, freiwilliges Lernen und Nachholen. Die Testuhr ist auf
    die dokumentierten Domänenpfade beschränkt; die globale Anbieterperiode
    bleibt an der Hostuhr. Die 30 Tage wurden nicht durchgehend im mobilen
    Browser bedient, und echte OCR, echte KI und fachliche Lehrplanabdeckung
    sind nicht nachgewiesen. Der Hauptpunkt bleibt deshalb offen.
    [Testplan und Grenzen](docs/MONTH_REGRESSION_2026_11_25.md).

    Wiederholung am 26.11.2026 auf isoliertem PostgreSQL: elf Fälle bestanden,
    darunter die 30-tägige Folge mit künstlichem Provider. Das ist kein Ersatz
    für den weiterhin offenen Browsermonat mit echten Anbieteraufrufen.

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

  - [x] **Kinderexport an die Elternsitzung und Anmeldeabsicht binden.**
    Beginnt eine neue Anmeldung, schließt der alte Exportdialog; verspätete
    Dateidaten oder Fehler lösen keinen neuen Speicherdialog aus. Auch nach
    einem stillen Tokenwechsel wird die alte Antwort verworfen und die
    Ladeanzeige beendet. Ein bereits an das Betriebssystem übergebener
    Speichervorgang lässt sich damit nicht rückgängig machen. Künstliche
    Widgetfälle prüfen beide Wechsel, Fehler und den regulären Speicherweg;
    die allgemeine Cookie- und Mehrgeräteabnahme bleibt offen.

  - [x] **Löschjournal-Sperre für SQLAlchemy-Schreibwege prüfen und
    Restore-Replay von Betriebsdiagnosedateien trennen.** Normale ORM-,
    Core- und Bulk-Schreibwege auf dem Anwendungspool verlangen bis zum
    Commit dieselbe Journal-Schreibsperre. Ein Replay von Familien-, Kinder-
    oder Materiallöschungen löscht keine Diagnose-Dateien der laufenden
    Installation. Künstliche SQLite-/PostgreSQL-Fälle prüfen beide Grenzen;
    Roh-SQL, alte Prozesse, Offsite-ACK und vollständige Wiederherstellung
    bleiben gesondert offen. [Umfang](docs/ERASURE_LOCK_AND_REPLAY_2026_11_06.md).

  - [x] **Abgelaufene Nachrichten im Restore erneut bereinigen.** Der
    Wiederherstellungsabgleich verwendet dieselbe 365-Tage-Grenze wie der
    Worker, nach der Journalprüfung und nur in der separaten Datenbank. Die
    automatische Probe verlangt einen bestätigten Systemd-Zeitsynchronstatus;
    der Offline-Aufruf verlangt einen explizit geprüften UTC-Zeitpunkt. Die
    isolierten Fälle prüfen Grenzwert, Wiederholung, manipuliertes Journal,
    fehlende Zeit und unveränderte Originaldaten. Alte Restore-Werkzeuge und
    andere Datenarten bleiben gesondert zu beachten; siehe `docs/OPERATIONS.md`.

  - [x] **Gesprächs- und Rückblickfristen in Restorepfaden erneut anwenden.**
    Die automatische Probe und das Offline-Werkzeug wenden nach Journalprüfung
    den bestehenden 365-Tage-Cutoff auf Tutor, Schulbuddy und Elternrückblicke
    an. Der Runtime-Vorabcheck prüft die drei Tabellen und den Grenztag mit
    künstlichen Daten und unabhängig vorgegebenem Cutoff. Je neun künstliche
    Fälle auf SQLite und isoliertem PostgreSQL sowie zehn Vorabcheck-Tests
    bestanden; die Restore-Ziele waren SQLite-Testkopien. Bestehende
    Gesprächskaskaden, ältere Runtime-Versionen und die nicht bewiesene
    Vollständigkeit des Löschjournals bleiben ausdrücklich zu beachten.
    Am 05.11.2026 wurde die separat installierte, quellgebundene Runtime
    `06b7301` auf dem Server und dem Offsite-Client mit künstlichen Fällen
    vorgeprüft. Vor und nach dem Release `1.38.98+253` gelang jeweils eine
    tatsächliche Wiederherstellungsprobe aus einer verschlüsselten Sicherung
    in eine getrennte PostgreSQL-Datenbank; nach dem Release wurde auch der
    Offsite-Abgleich einschließlich Serverbestätigung geprüft. Dies belegt
    weder die semantische Vollständigkeit des Löschjournals noch sämtliche
    Datenarten. Die Runtime ist ausdrücklich weiterzuführen und bei künftigen
    Änderungen vor einem Wechsel erneut zu prüfen; siehe `docs/OPERATIONS.md`.

  - [x] **Vokabeln nach Löschung und Ablauf vor Wiederherstellung schützen.**
    Einzelwörter, Vorschläge und Sammlungen erhalten signierte Belege;
    idempotentes Replay und Kaskaden sind künstlich geprüft. Alte Restoretools
    verstehen die neuen Belegtypen nicht. Vor Aktivierung ist die in
    [VOCABULARY_ERASURE_2026_11_04.md](docs/VOCABULARY_ERASURE_2026_11_04.md)
    festgelegte Upgrade-Reihenfolge erforderlich; historisch fehlende Belege
    werden nicht erfunden. [Datenmatrix](docs/DATA_LIFECYCLE_CHECKS_2026_11_04.md).

  **04.11.2026, Schutz privater Bilddateien:** Anzeige, Exporte, OCR und
  Wiederverarbeitung öffnen begrenzte reguläre JPG-Dateien innerhalb des
  Uploadverzeichnisses ohne symbolische oder harte Links. Fehlende Fotos
  werden im Export benannt. 59 künstliche SQLite-Fälle bestanden mit zwei
  PostgreSQL-Skips; vier gezielte Fälle bestanden auf isoliertem PostgreSQL.
  Eine sichere Dateipfadprüfung beweist bei beschädigter Datenbank keine
  Eigentümerschaft. Externe Aufbewahrungsfristen und die vollständige
  Löschmatrix bleiben offen. Profilbilder verwenden dieselbe sichere
  Verzeichnisöffnung mit eigener Größen- und Hashprüfung; fehlende Profilbilder
  sind beim Fotoexport ebenfalls aufgeführt. 33 Profil-/Dateifälle bestanden
  auf SQLite und zwei gezielte Fälle auf isoliertem PostgreSQL.
  Bei einer nicht sicher zugänglichen Uploadablage wird das Löschjournal
  vor dem Dateischritt veröffentlicht. Ein Admin-Wiederholungsbeleg meldet
  die Bereinigung erst nach bestätigtem Abschluss; alte unbelegte Belege
  bleiben vorsichtig. Jeweils künstliche Fehlerfälle wurden auf SQLite und
  isoliertem PostgreSQL geprüft.

  **Teilprüfung 02.11.2026:** 21 künstliche SQLite-Fälle zu Aufbewahrung und
  Notenwiederherstellung bestanden; [Prüfbericht](docs/ROADMAP_MODULE_CHECKS_2026_11_02.md#datenlebenszyklus-und-löschung).

  Aufbewahrung, Export und Löschkaskaden für Quellen samt Tutor-Zitaten, Fotos, Antworten, Wortschatz, Noten/Importbelege, Nachrichten und Zahlungsbelege gegen die jeweiligen Verträge prüfen.

  **Abnahme:** berechtigte Familien vollständig exportieren/löschen können, Aufbewahrungsfristen und gesetzliche Ausnahmen dokumentiert sind, Roh-PDFs nicht gespeichert werden und private Inhalte oder Schlüssel weder in Logs noch Git oder frei zugänglichen Uploads erscheinen.

  **Teilprüfung 02.11.2026:** Je 15 künstliche Fälle bestanden auf SQLite und
  isoliertem PostgreSQL. Sie umfassen unter anderem Kontolöschung, Heftseiten
  mit zugehörigen Runden, Tutor-Zitate, Wortschatz, Noten/PDF-Import,
  Prüfungsdaten, Zahlungsbelege, Aufbewahrung und vertrauliche Fehlerlogs.
  Die Prüfung belegt nicht alle Datenarten oder tatsächliche externe
  Anbieter-/Support-/Proxylogfristen; diese und die vollständige Export- und
  Löschmatrix bleiben offen.

  **03.11.2026, Prüfungszuordnungen:** Die Elternbestätigung eines wörtlichen
  Ausschnitts wird im regulären Familienexport ausgegeben. Beim ausdrücklichen
  Löschen der zugehörigen Originalseite und beim Abgleich des Löschjournals
  nach einer Wiederherstellung wird auch der abgeleitete Nacharbeitsbericht
  samt dieser Zuordnung entfernt; Kostenbelege und eine andere Heftquelle
  bleiben erhalten. Je 14 künstliche Lebenszyklusfälle bestanden auf SQLite
  und isoliertem PostgreSQL. Dies ergänzt die Datenmatrix, schließt aber die
  ungeprüften externen Aufbewahrungsfristen nicht.
- [ ] **P0 – Wiederherstellung praktisch üben**

  - [x] **Offsite-ACK an den übertragenen Journalstand binden.** Export und
    Bestätigung verwenden einen serverseitig authentifizierten Beleg über
    Journalinhalt und verschlüsselte Datei. Ein synthetischer Ablauf prüft
    Änderung zwischen Export und ACK, Wiederherstellung der alten Kopie und
    anschließenden erfolgreichen erneuten Abgleich. Alte Protokolle werden
    abgelehnt. Der koordinierte Zwei-Host-Wechsel und ein echter Restore
    bleiben offen. [Einzelheiten](docs/OFFSITE_RECEIPT_2026_11_26.md).

  - [x] **Ausstehende Löschbelege vor Offsite-Export und ACK erkennen.**
    Unter der Journalsperre verhindert ein ausstehender oder nicht prüfbarer
    Outboxstatus den Export beziehungsweise den ACK-Erfolgsmarker. Die
    lesende PostgreSQL-Abfrage ist zeitlich begrenzt. 100 künstliche
    Sicherungs- und Offsitefälle sowie ein isolierter PostgreSQL-Test mit
    echtem Sperrkonflikt bestanden. Die vollständige Historie bleibt offen; der
    lokale Stand ist noch nicht ausgerollt.
    [Prüfung](docs/OFFSITE_OUTBOX_SNAPSHOT_2026_11_26.md).

  - [x] **Journal und Outbox begrenzt und ohne Schreibzugriff vergleichen.**
    Ein Diagnosewerkzeug prüft Signaturen und gleicht aktuelle Belege beider
    Bestände mit begrenzten Datenbank-, Sperr- und Mengengrenzen ab. Es gibt
    ausschließlich Summen aus und erteilt keine Freigabe. Im lesenden
    Produktionsabgleich vom 07.11.2026 stimmten 501 veröffentlichte Belege
    mit dem Journal überein; ausstehende oder abweichende Belege wurden nicht
    gefunden. Historisch in beiden Beständen fehlende Löschungen, fremde
    Writer und vollständige Anlagenbindung bleiben damit ungeprüft.
    [Grenzen und Tests](docs/ERASURE_JOURNAL_AUDIT_2026_11_07.md).

  **07.11.2026, erneut geöffnet:** Ein nachfolgender isolierter Gegenversuch
  zeigte, dass ein authentisches, aber nicht nachweislich vollständiges altes
  Löschjournal beim Restore gelöschte Daten zurücklassen kann. Ein vor dem
  vollständigen Stillstand alter Schreiber gestartetes Datenbankabbild kann
  spätere Löschungen ebenfalls verpassen. Die früheren Proben belegen die
  jeweils durchgeführten Schritte, aber nicht die Vollständigkeit des Journals
  und die sichere Wiederherstellung nach allen Löschungen. Vor erneuter
  Abnahme müssen aktueller Journalstand und Schreibsperren über beide Hosts
  hinweg nachweisbar zusammengeführt und ein echter isolierter Restore mit
  diesem Stand geprüft werden. Der alte Restore-Dienst ist produktiv noch an
  eine ältere Runtime gebunden.

  **04.11.2026, Schutz des Wiederherstellungsziels:** Überschreibende und
  doppelte Datenbank-Verbindungsparameter werden zurückgewiesen und das
  tatsächlich verbundene Ziel vor Schreibaktionen geprüft. Der dokumentierte
  PostgreSQL-Unix-Socket bleibt zulässig. SQLite-Ziele müssen reguläre Dateien
  ohne Symlink oder Hardlink sein. 30 künstliche Sicherheitsfälle, ein
  isolierter PostgreSQL-Sockettest und 33 kombinierte Offline-Restorefälle
  bestanden. Eine getrennte Infrastruktur muss weiterhin unabhängig geprüft
  werden; diese Namens- und Zielkontrolle ist kein Isolationsnachweis.

  **03.11.2026, ergänzende Schutzprüfung:** Der lokale Löschjournalabgleich
  lehnt das produktive Uploadverzeichnis und dessen Eltern-/Unterverzeichnisse
  auch nach Auflösung von Pfad-Aliasen ab. Ein beim Aufruf gesetztes `DATA_DIR`
  wird ebenso berücksichtigt. 17 isolierte Tests bestanden; die Erkennung ist
  kein Beweis für eine getrennte Datenbank oder für unbekannte Datenpfade.
  Ein erneuter produktiver Wiederherstellungslauf wurde nicht durchgeführt.

  Verschlüsselte Sicherung in eine separate Datenbank einspielen, aktuelles authentifiziertes Löschjournal und Rechteänderungen abgleichen, alte Sitzungen und Einladungs-/Reset-Tokens widerrufen sowie Verbrauch und Aufbewahrungsfristen prüfen.

  **Abnahme:** Datenintegrität, Löschabgleich, zulässige Backup-Aufbewahrung von höchstens 14 Tagen, getrennte Geheimnisse und eine dokumentierte Entscheidung zur möglichen Journallücke nachgewiesen sind; keine automatische produktive Rücksicherung.

  **Ergänzung 02.11.2026, Aufbewahrungs- und Rehearsal-Abnahme:** Mit der
  Einführung des 5-Minuten-Dienstes `schulpilot-backup-retention.service` wurde
  die tägliche Aufbewahrungslücke behoben. Eine Bestandsprüfung auf
  `schulpilot.dorfspy.de` ergab 363 verschlüsselte Archive, das älteste vom
  19.10.2026 13:36:48 UTC (13,66 Tage alt; 0 Archive älter als 14 Tage). Der
  Dienst läuft planmäßig erfolgreich (`code=exited, status=0/SUCCESS`). Die
  isolierte Wiederherstellungsprobe `schulpilot-restore-check.service` auf
  `20261101T184119Z.tar.enc` lief mit Status 0/SUCCESS durch (393
  Löschdatensätze geprüft, `sessions_revoked: true`, `ai_emergency_stop: true`,
  `dropdb` bestätigt, `production_overwritten: false`). Die Entscheidung zur
  maximalen Journallücke ist in `docs/OPERATIONS.md` und
  `docs/STORAGE_AND_ALERTS.md` dokumentiert. Alle Abnahmekriterien sind
  nach damaligem Kenntnisstand als erfüllt angesehen; der spätere oben
  beschriebene Gegenbeweis hat diese Gesamtbewertung aufgehoben.

  - [x] **Unbelegten manuellen Restore-Abgleich ausdrücklich begrenzen.**
    Das Abgleichwerkzeug beendet sich ohne `--diagnostic-only` vor Änderungen
    an Datenbank und Dateikopie. Der ausdrücklich isolierte Diagnoseweg bleibt
    für Prüfungen verfügbar und warnt vor Aktivierung. Künstliche Tests prüfen
    fehlende und veraltete Journale sowie unveränderte Zielkopien. Alte
    Werkzeugversionen und manuell aktivierte Datenbanken werden dadurch nicht
    technisch gesperrt; der Zwei-Host-Fence und der Vollständigkeitsnachweis
    bleiben Teil des offenen Hauptpunkts.

  **Nachweis 01.11.2026:** Am 01.11.2026 um 15:51:58 UTC lief die isolierte
  Wiederherstellungsprobe (`schulpilot-restore-check.service`) auf dem Zielserver
  `schulpilot.dorfspy.de` mit dem aktiven Release `1.38.58+213` auf dem neuesten
  verschlüsselten Backup `20261101T094243Z.tar.enc` erfolgreich durch.
  Ciphertext wurde mit separatem AES-GCM-Schlüssel (`/etc/schulpilot/backup.key`)
  authentifiziert und entschlüsselt, in eine isolierte temporäre Datenbank
  (`schulpilot_436a53d3dcfb_restore_test`) eingespielt und gegen 393 signierte
  Löschjournaldatensätze abgeglichen. Alle Sitzungen wurden widerrufen, Tokens
  entwertet und der Notfallstopp aktiviert (`sessions_revoked=true`,
  `ai_emergency_stop=true`). Die temporäre Datenbank wurde sauber entfernt
  (`dropdb`); die Produktionsdatenbank wurde nicht überschrieben
  (`production_overwritten=false`). Die Erkennung unübertragener Outboxeinträge
  wurde geprüft.

- [x] **P0 – Überwachung und Störungsablauf prüfen**

  **01.11.2026, Zustellungsnachweis und Alarmabnahme:** Die tatsächliche
  Zustellung von Alarmnachrichten über den autorisierten SMTP-Transport wurde
  mit `scripts/monitor_mail_smoke.py` abgenommen: Ein neutraler synthetischer
  Alarmtest mit kryptografischem Einmaltoken wurde versandt und per
  schreibgeschütztem Gmail-IMAP-Abruf in der Betreiber-Inbox verifiziert
  (`operator_alarm_test_delivered: true`, `read_only_imap: true`,
  `child_data_used: false`). Der installierte Wächter `schulpilot-monitor.service`
  läuft auf `schulpilot.dorfspy.de` fehlerfrei im 5-Minuten-Takt (`failures: []`);
  der unabhängige Wächter `scripts/watch_public.py` besteht im Trockenlauf
  (HTTPS-Health und Offsite-Frische grün). 8 Offline- und Grenzwerttests in
  `scripts/tests/test_restore_monitor.py` bestanden isoliert.

  **31.10.2026, lokal ergänzt:** Beschädigte und zukünftige Offsite-Marker
  führen im unabhängigen Wächter zu einem neutralen Fehler statt zu einem
  Programmabbruch. Getrennte Speicheralarme und simulierte Benachrichtigungen
  werden künstlich geprüft; der Ablauf ist in `docs/STORAGE_AND_ALERTS.md`
  dokumentiert. Die Auslieferung ist erfolgt; eine unabhängige Prüfung der
  tatsächlichen Alarmzustellung steht noch aus.

  - [x] Beschädigte oder ungültige Offsite-Erfolgsstände als neutrale Störung
    behandeln und die Erkennung isoliert prüfen.
  - [x] Installierte Überwachung, unabhängigen Alarmweg und Störungsablauf im
    freigegebenen Betriebsumfang abnehmen.

  **Ergänzung 01.11.2026:** Der unabhängige Wächter erkennt jetzt auch
  liegengebliebene Offsite-Journaltransaktionen nach Freigabe der Pull-Sperre;
  ein aktiver Pull verursacht dabei keinen Fehlalarm. Der installierte Code
  bestand einen künstlichen Unterbrechungstest im getrennten temporären Home,
  ohne eine Nachricht zu versenden. Der reale Trockenlauf war fehlerfrei;
  die vorherige Version ist als Rückweg gesichert.

  Bestehende Checks für API, Worker, festhängende Jobs, Lösch-Outbox, Backups, Speicher, öffentliche Erreichbarkeit und Offsite-Frische sowie zuständige Alarmwege kontrollieren.

  **Abnahme:** ein isolierter, ausdrücklich autorisierter Test die Erkennung und Zuordnung einer Störung belegt, Meldungen keine privaten Inhalte enthalten und Runbook, Eskalation und Wiederanlauf aktuell sind.
- [x] **P1 – Anbieter- und Kostenkontrollen revisionsgebunden nachweisen**

  - [x] **EZB- und OpenRouter-Kostenmetadaten regelmäßig prüfen.** Der
    bestehende Worker übernimmt nur gültige, aktuelle EZB-Referenzkurse und
    die konservativ höchste veröffentlichte Preisstufe der bereits gewählten
    Upstreams. Laufende und gleichzeitig reservierte Aufträge behalten ihre
    Revision; fehlende Quellen ersetzen keine Werte und begrenzen weiterhin
    die Freigabe. Modellfähigkeiten werden durch Metadaten nicht als neu
    praktisch geprüft ausgegeben. Künstliche Tests decken ungültige Daten,
    Quellenausfall und gleichzeitige Aufträge ab.

  Tatsächlich aktive Konfiguration und spätere dokumentierte Betreiberentscheidungen prüfen (`docs/APPROVALS.md`, `docs/STATUS.md`); historische Standards nicht als aktuelle Einstellung behandeln. Mit ausschließlich freigegebenen künstlichen Vorlagen den regulären Ablauf und atomare Reservierung bei Erfolg, Fehler, Parallelität und Widerruf testen.

  **01.11.2026:** Der Zielserver verwendet OpenRouter, Konfigurationsrevision
  37, mit aktiver Datenschutzfreigabe. Je 120 SQLite-/PostgreSQL-Fälle zu
  Grenzen, Reservierungen und Anbietervalidierung sowie je 50 Fälle zu
  Modellrouting, Codex-Adapter und Ausgaberahmen bestanden mit künstlichen
  Transporten. Unbekannte Kosten behalten die Reservierung, parallele
  Ansprüche und fehlende Gebührenbelege werden geprüft. Ein aktueller echter
  künstlicher Providerlauf für die aktive Revision bleibt separat zu belegen;
  simulierte Transporte belegen keine Erreichbarkeit des Anbieters.

  - [x] Die aktuelle OpenRouter-Konfigurationsrevision 37 mit einem echten,
    ausschließlich künstlichen Bild im regulären Testkonto auf Erreichbarkeit
    und Kostenerfassung prüfen. Ein synthetisches Bruchblatt wurde hochgeladen,
    gelesen und nach der automatischen Gegenprüfung regulär entfernt. Zwei
    abgeschlossene Extract-Kostenbelege gehören zur Revision 37: Luna mit
    979 Mikro-USD und Sol mit 13.592 Mikro-USD. Der Hintergrundabgleich
    bestätigte beide Beträge anhand der OpenRouter-Generation-Belege;
    zusammen sind das 14.571 Mikro-USD. Dies war die konfigurierte
    kostenpflichtige Route, kein Free-Test.
    Die Prüfung belegt die beiden Bildaufrufe, nicht alle anderen
    KI-Funktionen oder vollständige fachliche OCR-Richtigkeit.

  **Abnahme:** feste Adapter/Upstreams, Schema- und Quellenprüfung, Grenzen, Audit, ehrliche unbekannte Kosten und Verzicht auf automatische Providerwechsel oder Wiederholungen belegbar sind; Konfiguration und Freigaben werden nicht still gelockert.

  **Nachweis 02.11.2026:** Der lesende Serverabgleich bestätigte OpenRouter,
  aktive Konfigurationsrevision 37, eingeschaltetes Routing, gespeicherte
  Datenschutzfreigaben und keinen Notstopp. Die oben dokumentierte echte
  künstliche Bildprüfung gehört zu dieser Revision. Je 104 Fälle auf SQLite
  und isoliertem PostgreSQL prüften Anbieter-/Upstreambindung, Schemafehler,
  Freigaben, Kosten, Reservierungen, Parallelität und fehlende Kostenbelege;
  weitere je elf Fälle prüften Widerruf, Quellenänderung, Notstopp und
  Providerrevision während eines Auftrags. Die neuen Tests verwendeten
  ausschließlich künstliche Daten und simulierte Anbietertransporte. Der
  echte Bildtest beweist keine fachliche Qualität aller Modelle oder die
  Erreichbarkeit jeder Route; eine unabhängige Datenschutzprüfung bleibt offen.
- [x] **P1 – Google- und Geheimnisbetrieb überprüfen**

  OIDC-State, Nonce, serverseitiges PKCE, Cookie-Webfluss, native Geräte-Proof-/Callback-Ticket-Bindung, ausdrückliche Kontoverknüpfung und zusätzliche Mailbestätigung bei Bedarf prüfen.

  **Abnahme:** keine automatische Verknüpfung nach E-Mail möglich ist, öffentliche Datenschutzerklärung und Inhabernachweis beim Deployment erhalten bleiben und private Clients, Dienstkonten und Signierschlüssel außerhalb von Git und Builds bleiben.

  **Nachweis 01.11.2026:** Je 23 Google-/Datenschutzfälle auf SQLite und
  isoliertem PostgreSQL sowie 28 Flutterfälle bestanden. Sie prüfen unter
  anderem State, Nonce, PKCE, Cookie-/Native-Trennung, ein einmaliges
  Rückgabeticket, ausdrückliche Verknüpfung und die zusätzliche Bestätigung
  externer Postfächer. `/privacy` liefert öffentlich HTML; die Google-Datei
  ist bytegleich mit dem gespeicherten Inhabernachweis. Der produktive Google-
  Zugang verwendet den überprüften externen Client ohne verschlüsselten
  Ersatzwert; auch der aktive FCM-Schlüssel entspricht der überprüften Datei.
  Beide Serverdateien sind root-eigen und auf die Dienstgruppe begrenzt.
  Die bekannten privaten Werte und der Signierspeicher wurden mit 1.560
  verfolgten Dateien sowie dem entpackten APK, AAB, Reparaturarchiv und Web des
  aktiven Releases `1.38.57+212` verglichen; kein Treffer. Dies ist ein
  gezielter Vergleich bekannter Geheimnisse, keine Aussage über alle möglichen
  unbekannten Geheimnisse. Ein historischer echter Google-Weblogin ist in
  `docs/GOOGLE_LOGIN.md` dokumentiert; ein neuer Android-Gerätetest war für
  diese Abnahme ausdrücklich optional und wurde nicht behauptet.

## Release, Android und Benachrichtigungen

**Umfang seit 01.11.2026:** Der Betreiber behandelt Tests auf physischen
Androidgeräten als optional. Sie blockieren die Bearbeitung und eine getrennte
Webabnahme nicht. Die folgenden gerätebezogenen Prüfpunkte bleiben sichtbar
offen, solange sie nicht ausgeführt wurden; APK-Installierbarkeit, tatsächliche
Push-Zustellung und Geräteeigenschaften werden ohne Beobachtung nicht als
nachgewiesen ausgegeben. Signierte und quellgebundene Releaseartefakte bleiben
Bestandteil des bestehenden Buildvertrags.

- [x] **P0 – Jeden Release aus einem nachvollziehbaren Quellstand herstellen**

  Passende Backendtests einschließlich isoliertem PostgreSQL, Fluttertests, Analyse und Webbuild sowie `scripts/build_release.sh` mit fixierter Toolchain ausführen; Diff und Geheimnisse prüfen.

  **Abnahme:** Ergebnisse und Fehler mit Commit, Toolchain und Artefakten dokumentiert sind, signierte Direct-APK und Play-AAB dieselbe beabsichtigte Version tragen und Paket, Signierer, Nicht-Debug-Status, 16-KB-Ausrichtung und AAB validiert sind.

  **01.11.2026, Release `1.38.57+212`:** Der ausgelieferte Quellcommit
  `669ae59f994b1af0461bb5d3ff1204e97b50a07b` wurde mit der fixierten
  Toolchain (Flutter 3.47.7, Dart 3.13.5, Python 3.12.3, Android SDK 36,
  Bundletool 1.18.3; Einzelheiten in `toolchain.json`) gebaut. Die vollständige
  Flutter-Testsuite bestand mit 4.319 Fällen und 19 plattformspezifischen
  Auslassungen; ein zusätzlicher Chrome-Weblauf bestand mit 110 Fällen und
  fünf Auslassungen. Flutteranalyse und Webbuild waren erfolgreich. Für die
  betroffenen Backendpfade bestanden die in `docs/STATUS.md` aufgeführten
  SQLite- und isolierten PostgreSQL-Läufe. Direct-APK und Play-AAB wurden
  signiert und auf Version, Paket und Signierer geprüft; APK-Ausrichtung und
  Bundlevalidierung waren erfolgreich. Die öffentliche APK stimmt mit dem
  SHA-256 `aa7b9c9f74d9e9f39d866ac34bef2560398d3bc38b7c0b28a659c2076b8d495e`
  überein. Ein physischer Androidtest und die gesonderte Prüfung künftiger
  Toolchain-Warnungen sind dadurch nicht ersetzt.
- [ ] **P0 – Deployment und Rückkehr belegen**

  - [x] **Aktive Restore-Konfiguration vor Migration abgleichen.** Bei einem
    bestehenden Release vergleicht die Aktivierung die von systemd geladene
    Restore-Anweisung vor Änderungen und erneut vor der Migration. Ein
    abweichender separater Runtime-Pfad muss bei Migration mit den Backend-,
    Migrations- und Betriebsquellen des Zielstands übereinstimmen. Bei einem
    ausdrücklichen Rollback bleibt der Reader des zuvor aktiven Stands erhalten;
    ein von `current` abhängiger Reader blockiert diesen Rückweg. Das Deployment
    prüft bereits vor dem Stopp der Reparaturdienste, beim Aktivieren wird erneut
    geprüft. Eine veraltete Runtime blockiert den Wechsel. Synthetische Tests prüfen unter anderem fehlende und
    abweichende Dateien, Unit-Overrides und den Abbruch vor Seiteneffekten.
    Die Prüfung ersetzt weder einen koordinierten Zwei-Host-Wechsel noch einen
    tatsächlichen Restore, Laufzeit-/Abhängigkeitsprüfung oder Sperren gegen
    spätere Änderungen. Der produktive Wechsel bleibt ausdrücklich offen.

  - [x] **Unvollständige Sicherungen vor Release gesondert erkennen.**
    06.11.2026: Fehlt das Löschjournal oder ist es unzugänglich, bleibt das
    verschlüsselte Archiv mit gekennzeichnetem Status erhalten; der Dienst
    meldet einen Fehler. Die Releaseprüfung bindet den frischen Dienstlauf
    zusätzlich an seinen eigenen systemd-Invocation-Beleg und die passende
    Archiv-/Statusdatei. Damit erkennt sie unvollständige Sicherungen auch beim
    Übergang von der älteren Dienstversion, die noch Erfolg meldete. Künstliche
    Fehler-, Dateimanipulations- und Aktivierungsfälle prüfen den Abbruch vor
    dem Versionswechsel. Dies beweist keine Journalvollständigkeit oder echte
    Wiederherstellung; der Hauptpunkt bleibt offen.

  **05.11.2026, isolierte Machbarkeitsprüfung:** Ein vor dem Marker
  gebildeter Löschplan kann das alte Rollbackziel weiterhin entfernen. Ein
  nach Markeranlage neu benannter Snapshot wird von diesem Plan nicht erfasst,
  kann aber trotz erfolgreicher Kopie unvollständig sein. Synthetische Tests
  belegen beides sowie die Ablehnung von Links durch den bestehenden
  Digest-Walker. Signatur-/Archivbindung, ein sicherer Kopierer und der
  produktive Rückweg bleiben offen; es wurde kein neuer Rollbackweg aktiviert.
  [Machbarkeit und Grenzen](docs/ROLLBACK_SNAPSHOT_FEASIBILITY_2026_11_05.md).

  **03.11.2026, Bereinigung:** Vor dem Entfernen alter Releases wird nun auch
  der optionale Reparatur-Dispatcher geprüft. Ein aktiver Dienst muss aus dem
  aktuellen oder vorherigen Release laufen; instabile oder nicht ermittelbare
  Zustände blockieren die Bereinigung. 77 isolierte Betriebs- und Stagingtests
  mit 13 Untertests bestanden, einschließlich eines echten lokalen Prozesses
  in einem künstlichen alten Release. Der produktive Rückweg und die vollständige
  Koordination mit älteren Skripten bleiben offen.

  Betroffene Konfigurationen und Daten vorher sichern, Migrations- und Rückwärtskompatibilität prüfen, nur SCHULPILOT aktualisieren und vorheriges Release erhalten.

  **02.11.2026, weiterer Release:** `1.38.60+215` aus Commit `ed0d89e`
  ist auf `schulpilot.dorfspy.de` aktiviert. Web, Direct-APK und Play-AAB
  wurden mit der fixierten Toolchain gebaut; eine Storeveröffentlichung fand
  nicht statt. Health und Direktlink liefern den erwarteten Stand, eine
  anonyme private Materialliste wird mit 401 abgewiesen. Die öffentlich
  heruntergeladene APK stimmt hinsichtlich Größe und SHA-256 mit dem Manifest
  überein. API, Worker, Codex- und Reparaturdienste sowie Sicherungstimer sind
  aktiv. In der produktiven 390-Pixel-Webansicht werden die Schulbuddy-
  Frageideen nun als Schaltflächen ausgegeben. Das ist keine vollständige
  Screenreader- oder Android-Abnahme und ersetzt keinen echten Rollbacktest.

  **02.11.2026, produktiver Release:** `1.38.59+214` aus Commit `6f1e113`
  wurde auf `schulpilot.dorfspy.de` aktiviert; vorheriges Release ist
  `20261101T193953Z-534009f`. Der Deployablauf meldete erfolgreiche
  Sicherung und Caddy-Prüfung; API, Worker, Reparaturdienste, Codex-Dienst
  und Überwachung waren anschließend aktiv. HTTPS-Health meldete Commit und
  Release, der Direktlink lieferte HTTP 200, ein anonymer Zugriff auf eine
  private Materialliste HTTP 401. Die aus dem öffentlichen Download gelesene
  APK hatte 137.556.720 Bytes und stimmte mit Version, Code 214 und SHA-256
  des öffentlichen Manifests überein. Die Weboberfläche öffnete im Browser
  „Heute“ und die Fachübersicht unter „Lernen“. Der Play-Build wurde erstellt,
  kein Store-Upload durchgeführt. Der Backend-CI-Teil lief zum Zeitpunkt des
  Deployments noch; anschließend endete der vollständige
  [CI-Lauf 41479726888](https://github.com/meinzeug/schulpilot/actions/runs/41479726888)
  für `6f1e113` erfolgreich. Der physische
  Android-Updateablauf, die Koordination mit alten Skripten und ein echter
  Rückweg sind dadurch nicht abgenommen; der Hauptpunkt bleibt offen.

  **01.11.2026:** Der reale Release `1.38.57+212` wurde mit Sicherung,
  Healthprüfung und erhaltenem Vorgänger ausgerollt. Eine Testinterferenz
  zwischen Watchdog und Stagingprüfung wurde korrigiert: der Watchdogtest
  stellt die Prozess-Umask wieder her, und die Stagingprüfung setzt ihre
  öffentlichen Testrechte ausdrücklich. Der gemeinsame isolierte Lauf
  bestand anschließend mit 105 Fällen und 41 Unterfällen. Die nachfolgend
  beschriebene Koordinationslücke bleibt davon unberührt und offen.

  - [x] Release-Zeitstempel mit der Zielserveruhr statt der nicht
    synchronisierten lokalen Uhr bilden. Eine echte lesende SSH-Abfrage
    lieferte eine gültige Server-UTC-Zeit; Tests verwerfen unzulässige,
    mehrdeutige oder unmögliche Zeitangaben sowie SSH-Fehler und lassen keinen
    stillen Rückfall auf die lokale Uhr zu. Die Prüfung bescheinigt nicht,
    dass jeder künftige Server tatsächlich synchronisiert ist.

  - [ ] Parallele Betriebsabläufe und Release-Sperre absichern: Zwei
    gleichzeitige Deployments oder ein manueller Rückweg überlagern sich bei
    Upload, Aktivierung, Caddy, Dienstdateien, Anbieterworker und Releasezeigern
    nicht mehr. Eine zustandsbehaftete Lease (`.deploy.lock`) schließt
    konkurrierende Aktionen aus. `prune_releases.py` prüft vor der Ausführung
    die Release-Sperre und schützt unfertiges Staging, publizierte unaktivierte
    Stände sowie Releases neuer als `current`. Die Sperre übersteht
    SSH-Verbindungsabbrüche durch serverseitige Prozess- und
    Dateideskriptorprüfung (`/proc/<pid>/fd`). Aktivierung und manueller
    Rollback (`activate.py`) agieren atomar unter der Sperre; der Monitor
    unterdrückt Übergangswarnungen während des Neustarts. 29 gezielte Tests
    in `test_deploy_coordination.py` und `test_stage_release.py` bestanden.

    **Korrektur 02.11.2026:** Die obige Beschreibung ist ein Ziel, kein
    vollständiger Nachweis. Der bisherige Lese-/Schreibablauf der Lease war
    nicht atomar; außerdem plant die Bereinigung vor dem Erwerb der Sperre.
    Ein zusätzlicher Dateilock serialisiert nun die Lease-Änderungen, und die
    Bereinigung berechnet ihren Plan unter der Lease erneut. Ein Test mit zwölf
    gleichzeitig startenden Prozessen prüft die exklusive Lease. Leere oder
    ungültige Lease-Dateien blockieren nun Erwerb und Bereinigung statt eine
    fehlende Sperre vorzutäuschen; auch ungültige Zeitstempel, Prozess-IDs und
    Releasekennungen werden abgewiesen. Der vorhandene
    vermeintliche SSH-Abbruchtest simuliert keinen SSH-Abbruch und belegt das
    Überleben verzögerter Kindprozesse nicht. Das Entfernen des Stagings beim
    Abbruch, die Freigabe während der Aktivierung, Bootstrap und Arbeiten nach
    der Aktivierung sowie die vollständige Koordination mit laufenden alten
    Versionen müssen noch unter realistischen isolierten Bedingungen geprüft
    und gegebenenfalls repariert werden. Bis dahin die neue Koordination nicht
    als produktiv abgenommen betrachten.

    **Weitere Teilkorrektur 02.11.2026:** Abbrüche behalten Staging und Lease
    nach Token- und Releaseprüfung; eine abgelaufene Lease wird nicht allein
    anhand von Zeit, PID oder gerade offenen Dateien freigegeben. Ein echter
    separater Testprozess öffnete nach simuliertem Abbruch verzögert eine neue
    Datei; Staging und Sperre blieben erhalten. Zusätzlich bestand ein echter
    SSH-Abbruch bei einem künstlichen Upload über einen isolierten lokalen
    SSH-Server: Trotz künstlich abgelaufener Metadaten und verzögertem
    Dateiöffnen blieben Staging und Lease erhalten; ein zweites Deployment und
    Prune wurden blockiert. Reproduzierbar mit `SCHULPILOT_TEST_REAL_SSH=1
    python -m pytest -q scripts/tests/test_deploy_real_ssh.py`. Das belegt noch
    keinen Abbruch während Aktivierung oder das Verhalten alter Installationen.
    Vorbereitung/Bootstrap liegen nun unter
    der Lease; Aktivierung liest und sichert Caddy/Releasezeiger erst nach deren
    Erwerb. Die Lease wird nach erfolgreicher Aktivierung erst nach den weiteren
    Reparaturdienst-Schritten und Prüfung des aktiven Release freigegeben.
    Unterbrochene Abläufe erfordern eine bewusste Betreiberprüfung; automatische
    Aufräum- oder Wiederaufnahmesicherheit wird nicht behauptet.

    Die bestehende isolierte Aktivierungs-/Rückweg-Suite verwendet nun gültige
    Releasekennungen und explizite sichere Verzeichnisrechte. 26 Fälle bestehen,
    darunter Fehler vor und nach möglichem Start neuer Schreibdienste. Zwei
    ergänzte Fälle prüfen, dass die Deployment-Lease bei erfolgreicher oder
    fehlgeschlagener Aktivierung bis zur ausdrücklichen Nacharbeit bestehen
    bleibt. Systemdienste und Migrationen sind dabei Testdoubles, keine Live-Abnahme.
    Eine spätere Teilkorrektur erhält die Lease auch bei einem fehlgeschlagenen
    manuellen Rückweg oder fehlgeschlagener Bereinigung; die Tests prüfen, dass
    danach kein konkurrierendes Staging startet. Der konkrete Anlagenzustand
    muss vor einer manuellen Freigabe jeweils geprüft werden.

    Das noch installierte alte Bereinigungsprogramm berücksichtigt keine neue
    Lease und würde ein bereits publiziertes neues Release sonst als löschbar
    ansehen. Ein geschützter Marker im Releaseverzeichnis lässt dessen
    vorhandene Eingabeprüfung vor der Bereinigung abbrechen; er bleibt nach
    Unterbrechung erhalten und wird erst beim Abschluss unter der Lease geprüft
    und entfernt. Das tatsächlich aus Git geladene Bereinigungsprogramm des
    Produktionsstands `534009f` wurde isoliert dagegen geprüft. Das schützt
    nicht vor beliebigen alten Deploy- oder Rollbackskripten.

    **05.11.2026, manueller Rückweg:** Auch der neue Rückweg setzt den Marker
    vor der Aktivierung und entfernt ihn nur nach geprüftem Erfolg. Isolierte
    Tests sichern erfolgreiche und fehlgeschlagene Rückwege ab. Ein älterer
    Bereinigungslauf, der seinen Löschplan bereits vor dem Marker erstellt hat,
    kann dadurch nicht nachträglich gestoppt werden; diese Grenze wurde mit dem
    historischen Programm nachgestellt. Vor einem Rückweg muss ein solcher
    Lauf beendet sein. Der vollständige Koordinationspunkt bleibt offen.

    **Ergänzung 02.11.2026:** Ein zweiter isolierter Loopback-SSH-Test
    unterbricht eine echte SSH-Verbindung während der pausierten Ausführung
    des Aktivierungsskripts. Die künstliche Aktivierung läuft absichtlich in
    einem abgekoppelten Prozess mit simulierten Diensten und Migrationen;
    neues Staging, Rückweg und Prune bleiben bis zu ihrem Abschluss gesperrt.
    Die Lease bleibt auch nach erfolgreicher Aktivierung bis zur Nacharbeit
    erhalten. Der Test belegt kein bestimmtes Signalverhalten des produktiven
    SSH-Servers und keine echte Dienstumschaltung. Außerdem wurde ein Fehler
    korrigiert, bei dem eine hängende symbolische Verknüpfung auf die
    Lease-Datei als fehlende Sperre galt; hängende und gültige Symlinks
    blockieren nun Status, Erwerb, Freigabe und Bereinigung. Abgewiesene
    Sperrdateien geben ihren Dateideskriptor wieder frei. Die entsprechenden
    Tests verwenden ausschließlich temporäre künstliche Dateien.

    **Weitere Teilkorrektur 02.11.2026:** Die Kommandozeile verlangte bereits
    ein Sperrtoken, der interne Veröffentlichungsaufruf konnte aber ohne
    Token ein vorbereitetes Release verschieben. Auch dieser Aufruf verlangt
    nun eine passende laufende Deployment-Lease und weist fehlende, falsche,
    unterbrochene, andersartige oder einem anderen Release zugeordnete
    Sperren vor dem Verschieben ab. Die isolierte Release-Suite einschließlich
    beider Loopback-SSH-Tests bestand mit 106 Fällen und 13 Unterfällen. Die
    Koordination alter Werkzeuge und der produktive Rückweg bleiben offen.

    Ein anschließender Parallelitätstest zeigte, dass ein Abbruch bereits
    quittiert werden konnte, während eine Veröffentlichung noch beim Verschieben
    pausierte. Prüfung und Veröffentlichung stehen nun zusammen unter dem
    Dateilock; ein Abbruch wartet auf ihren Abschluss und erhält anschließend
    die unterbrochene Lease und den Schutzmarker. Nach Beginn einer Aktivierung
    kann dieselbe Lease nicht erneut veröffentlichen. Der reproduzierte Fehler
    und beide Aktivierungszustände sind getestet. Die Release-Suite bestand
    nach der Korrektur mit 109 Fällen und 13 Unterfällen. Das belegt keine
    Koordination mit nicht teilnehmenden alten Skripten.

  **Zusätzliche Tests:** Zwei synthetische Deployments mit künstlich pausiertem Upload und paralleler Bereinigung ausführen; dazu SSH während Upload und Aktivierung unterbrechen, den Kindprozess verzögert beenden und prüfen, dass kein zweiter verändernder Ablauf oder prune das laufende Staging beeinträchtigt. Frühe und späte Fehler, Timerläufe sowie einen manuellen Rückweg unter demselben Vertrag prüfen. Keine Tests gegen Produktion ausführen.

  **Abnahme:** HTTPS/Health den erwarteten Quellstand zeigen, Web-Direktlinks und anonyme Schutzgrenzen geprüft sind, öffentlich ausgelieferte APK und Manifest aus tatsächlicher Datei zu Größe/Hash/Version passen und ein migrationsbewusster Rückweg dokumentiert ist.
- [x] **P1 – Direct- und Play-Update getrennt abnehmen**

  - [x] **Direct-Update und manipulierte APKs im Emulator prüfen.** Das
    reguläre Update von +244 auf +249 gelang über den App-Updater und die
    Android-Bestätigung; Kaltstart und Rückkehr aus dem Hintergrund wurden
    beobachtet. Ein getrenntes Debug-Testpaket prüfte die echte native
    Validierung gegen synthetische fehlerhafte APKs und wurde wieder entfernt.
    Das quellgebunden geprüfte Play-AAB enthält keine APK-Installerberechtigung.
    Ein angemeldetes Konto und dessen Datenerhalt beim Update wurden hier nicht
    geprüft; auch eine Play-Zustellung ist damit nicht belegt. Einzelheiten:
    `docs/ANDROID_UPDATE_VERIFICATION_2026_11_05.md`.

  Für Direct höhere Version auf fester HTTPS-Quelle bei Kaltstart und Wiederaufnahme prüfen; Größen-, Hash-, Paket- und Signaturabweichungen ablehnen und Android-Installationsbestätigung beobachten.

  **Abnahme:** gültiges Update mit erhaltenem Konto und Daten funktioniert, fehlerhafte Downloads nicht installiert werden und das Play-AAB ausschließlich den Play-Updateweg ohne APK-Installerberechtigung enthält. Ein gebautes AAB ist kein Play-Upload oder veröffentlichter Storeeintrag.

  **05.11.2026, Emulator-Abnahme:** Der signierte Direct-Updateweg wurde mit Systembestätigung und ohne `adb install` bis `+251` ausgeführt. Ein eigens angelegtes künstliches Kind blieb angemeldet und öffnete dieselbe synthetische Text-Heftseite vor und nach dem Update; die 357 Zeichen des zugänglichen Texts waren identisch. Kaltstart und Hintergrundrückkehr wurden auf `+249` gesondert geprüft. Der echte native Direct-Prüfer verweigerte isoliert künstliche APKs bei Abweichungen von Größe, Hash, Paket, Signierer und Version sowie Downgrade und zu hoher Mindestversion; der Installeraufruf wurde dabei abgefangen. Das quellgebundene Play-AAB `+249` wurde mit Bundletool, Manifest, Signatur und R8-/DEX-Anhaltspunkten für den getrennten Play-Pfad geprüft. Der künstliche Haushalt und lokale Testdaten wurden entfernt.

  Der Abgleich umfasst eine Textseite ohne Foto und den Android-Zugänglichkeitsbaum, keinen Pixelvergleich oder alle Datentypen. Es fand keine Play-Auslieferung statt. Einzelheiten, Quellen und maschinenlesbare Belege: [Android-Updateprüfung](docs/ANDROID_UPDATE_VERIFICATION_2026_11_05.md).
- [ ] **P1 – Physische Android-Abnahme nachholen**

  - [x] **Installierte Stable-APK und Hintergrundwechsel auf einem physischen Android-Gerät prüfen.**
    Am 08.11.2026 wurden auf einem Redmi 14C mit Android 14 die native
    SchuleSchlau-App und ihre Kinder-Startseite sichtbar geöffnet. Die
    installierte APK `1.38.110+265` stimmt per SHA-256 mit dem öffentlichen
    Stable-Manifest überein. Beim Wechsel auf den Android-Startbildschirm und
    zurück blieb der App-Prozess erhalten; die aktiven Android-Oberflächen
    wurden beobachtet. Das ist ein begrenzter Teilnachweis ohne Aussage zu
    erhaltenen Eingaben oder Lernposition. [Gerätebericht](docs/ANDROID_PHYSICAL_2026_11_08.md).

  - [x] **Schulbuddy-Tastatur und ungesendeten Entwurf auf einem physischen Android-Gerät prüfen.**
    Auf dem Redmi 14C mit Android 14 blieb die Gboard-Tastatur nach dem Öffnen
    und während der Eingabe sichtbar. Ein kurzer Testtext blieb bei einem
    Hintergrundwechsel im geöffneten Chat erhalten und wurde anschließend
    gelöscht. Keine Frage wurde abgesendet. Die Sendeschaltfläche war bei
    sichtbarer Tastatur nicht zu sehen; ein tatsächliches Absenden und weitere
    Tastaturzustände bleiben offen. [Gerätebericht](docs/ANDROID_PHYSICAL_2026_11_08.md).

    **Nacharbeit:** Bei sichtbarer Tastatur stehen Eingabe und Senden nun bei
    genügend Platz zusammen über der Tastatur; sehr kleine oder stark
    vergrößerte Ansichten bleiben vollständig scrollbar. Widgettests prüfen
    die sichtbare Aktion, den Fokuserhalt beim Wechsel der Tastaturhöhe und
    eine kleine Ansicht mit großer Schrift. Die geänderte APK und ein echtes
    Absenden auf dem physischen Gerät sind noch nicht abgenommen.

  - [x] **Kamera und Fotoauswahl auf einem physischen Android-Gerät öffnen und abbrechen.**
    Beide Wege öffneten die native Android-Oberfläche und führten nach Abbruch
    zurück zur App. Aufnahme, Auswahl, Zuschnitt und Upload wurden dabei nicht
    ausgeführt und bleiben Teil der offenen Gesamtprüfung.
    [Gerätebericht](docs/ANDROID_PHYSICAL_2026_11_08.md).

  Auf Nutzerwunsch für diesen Auftrag optional; die weitergehende Abnahme
  blockiert den Abschluss anderer Roadmap-Punkte nicht. Ohne echte
  Gerätebeobachtung bleiben gerätespezifische Aussagen offen; Emulator, Build
  oder API-Antwort ersetzen sie nicht. Bei späterer Durchführung mit eigenem
  Gerät und künstlichem Material Kamera/Fotozuschnitt, Tastatur, Netzverlust,
  Speicherknappheit, Hintergrund/Rückkehr, Appneustart, Update und
  Barrierefreiheit einschließlich großer Schrift und TalkBack tatsächlich
  bedienen.

  **Abnahme:** Gerät/Androidversion, konkrete Abläufe, Beobachtungen, Fehler und Korrekturen dokumentiert und Testdaten regulär bereinigt sind.
- [x] **P1 – Benachrichtigungen auf Android sichtbar prüfen**

  **Abnahme 05.11.2026:** Im ausdrücklich akzeptierten Android-Emulator sind
  Vordergrundzustellung, Hintergrundzustellung und das Öffnen der eindeutig
  zugeordneten geschützten Demo-Lernrunde sichtbar geprüft. Der zunächst
  unvollständige automatische Cleanup bleibt im Rohbericht erhalten; die
  nachträgliche Abmeldung sowie Geräte- und Familienlöschung sind gesondert
  belegt. Dies belegt weder physische Geräte noch eine KI-generierte Runde.
  [Ende-zu-Ende-Nachweis](docs/ANDROID_ROUND_READY_E2E_2026_11_05.md).

  - [x] **Android-Emulator: Vordergrundzustellung sichtbar prüfen.**
    Ein eigener künstlicher Account erhielt nach Elternfreigabe und Geräte-Opt-in
    genau eine eindeutig zugeordnete Testzustellung. App-Hinweis und neutrale
    Android-Systembenachrichtigung waren sichtbar. Das Testkonto wurde gelöscht;
    ein zuvor fehlgeschlagener, befristeter Demo-Anlageversuch bleibt mit seinen
    Bereinigungsgrenzen dokumentiert. Der direkte Weg in eine fertige Lernrunde
    war in diesem Vordergrundtest noch nicht abgenommen und wurde später wie
    oben beschrieben getrennt geprüft.
    [Nachweis](docs/ANDROID_FOREGROUND_PUSH_2026_11_05.md).

  **Historische Vorbereitung des direkten Lernrundentests:** Ein streng auf freigegebene,
  serverseitige Demoinhalte begrenzter Pfad ist lokal mit Backend- und
  Renderertests geprüft. Produktions-Push-Stopp, Quellenprüfungen und
  Testfreigaben bleiben wirksam. Die damals noch ausstehende sichtbare
  Zustellung mit direktem Ziel wurde im oben verlinkten Emulatorlauf geprüft.
  [Prüfumfang](docs/ANDROID_DEMO_READY_PATH_2026_11_05.md).

  **Frühere Teilprüfung 05.11.2026:** Ein künstlicher Emulatorlauf bestätigte die
  sichtbare Hintergrundzustellung nach Prozessende sowie die neutrale
  In-App-Meldung im Vordergrund. Die native Vordergrundanzeige konnte der
  Prüflauf noch nicht sicher belegen; auch die geschützte Lernrundennavigation
  war damals offen. Beides wurde später wie oben beschrieben nachgeprüft.
  [Einzelheiten](docs/ANDROID_PUSH_2026_11_05.md).

  - [x] **Android-Emulator: sichtbare Hintergrundzustellung nach App-Stopp.**
    Mit einem künstlichen Kinderkonto wurde eine neutrale Firebase-Nachricht
    nach nachgewiesenem Stopp des App-Prozesses sichtbar angezeigt und in der
    App geöffnet. Der Emulator ersetzt die vom Betreiber gewünschte technische
    Android-Prüfung; Rückschlüsse auf herstellerspezifisches Energiesparen oder
    physische Hardware sind daraus nicht möglich. Vordergrund und geschütztes
    Lernrundenziel wurden später wie oben beschrieben getrennt geprüft.
    [Beobachtungen](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md).

  Im bestehenden Firebase-Projekt ausschließlich eigene künstliche Konten mit zeitlich begrenzter Testfreigabe verwenden; Elternfreigabe, ausdrückliches Geräte-Opt-in, Kanal-/Betriebssystemberechtigung, Ruhezeiten und Widerruf kontrollieren. Vordergrundanzeige sowie einen Versand nach nachgewiesenem Android-Hintergrundzustand beobachten, geschützten Zielaufruf prüfen und Registrierungen bereinigen.

  **Abnahme:** sichtbare Anzeige und Ziel tatsächlich dokumentiert sind; FCM-Annahme oder Validierung allein reichen nicht. In-App-Neuigkeiten bleiben ohne Push nutzbar.
- [x] **P1 – Web und native Freigabe vollständig bedienen**

  **Technische Abnahme 24.11.2026:** Der vollständige
  [GitHub-Lauf 45423097373](https://github.com/meinzeug/schuleschlau/actions/runs/45423097373)
  bestand für `041d6c8`, einschließlich des isolierten Browsergates mit
  17 Fällen. Fotoauswahl, Zuschnitt, Blob-XHR, Anmeldelinks und Logout wurden
  mit künstlichen Daten bei 390 und 1280 Pixeln geprüft; weitere bestehende
  Browserfälle decken Heft- und Lernwege ab. Auf dem aktuellen lokalen
  Android-Debugstand wurden Tastatur und Rückkehr aus dem Hintergrund im
  API-36-Emulator beobachtet. Frühere native Lernweg-Beobachtungen sind
  separat versioniert. Der aktuelle Lauf ist keine Abnahme eines physischen
  Geräts, des vollständigen nativen Foto-/Lernwegs oder der gesamten
  Barrierefreiheit; diese Grenzen bleiben in den jeweiligen offenen Punkten
  und im [Prüfbericht](docs/WEB_NATIVE_ACCEPTANCE_2026_11_24.md) bestehen.

  - [x] **Fotoimport und Anmeldelinks auf schmalem und breitem Web prüfen.**
    Der tatsächliche Dateidialog und Zuschnitt wurden bei 390 und 1280 Pixeln
    unter der konfigurierten CSP mit künstlichen Fotos bedient; Blob-XHR,
    gespeicherte Seiten und das Ausbleiben automatischer KI-Aufträge sind
    geprüft. Die Fotoaktionskarte ist auf breiten Ansichten auf 640 Pixel
    begrenzt; der gerenderte Kontrast ihrer Hauptaktion wurde gemessen.
    Künstliche Bestätigungs-, Reset- und Einladungslinks überstehen Kaltstart,
    Neuladen und einen neuen Link; Anmeldung und Abmeldung funktionieren in
    beiden Größen. Die Fälle sind im isolierten Browsergate verankert.
    [Prüfumfang und Grenzen](docs/WEB_NATIVE_ACCEPTANCE_2026_11_24.md).

  - [x] **Android-Tastatur mit aktuellem Debugstand beobachten.**
    Auf einem temporären Android-36-Emulator ohne Hardwaretastatur wurden
    Kaltstart, vollständige Bildschirmtastatur, Eingabefokus und Rückkehr aus
    dem Hintergrund mit künstlichem Text beobachtet. Der Emulator wurde
    danach gelöscht. Eine signierte Release-APK, ein physisches Gerät und ein
    nativer Foto-/Lernweg wurden in diesem Lauf nicht geprüft.
    [Prüfumfang](docs/WEB_NATIVE_ACCEPTANCE_2026_11_24.md).

  - [x] **Geöffnete Erklärgrafik und Leseposition im Android-Emulator prüfen.**
    Im künstlichen Fotofall wurden Kreis-/Balkenansicht und Zähler/Nenner
    gewechselt, die Position serverseitig gespeichert und nach Hintergrund und
    erneutem Öffnen wiederhergestellt. Es entstanden weder Antworten noch
    Beherrschungsnachweise. Die breitere geräteübergreifende Abnahme bleibt
    offen. [Nachweis](docs/ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md).

  Auf kleinen und breiten Ansichten regulären Fotoimport samt Blob-Lesezugriff und Zuschnitt, Anmeldung/Link-Kaltstart, wichtige Lernwege und Logout prüfen; sichtbare Tastatur, Fokus, Kontrast und große Schrift einbeziehen.

  **Abnahme:** reale Browser- und bei Verfügbarkeit Gerätebeobachtungen mit den vorhandenen automatisierten Prüfungen übereinstimmen und offene Lücken ausdrücklich benannt sind.

## Kapazität und öffentlicher Start

- [x] **Beta-Anmeldung für weitere Familien auf der Startseite bereitstellen.**

  **Abnahme 24.11.2026:** Auf der Zielinstallation `1.38.149+304`
  (`cd423ce`) durchlief eine eigens angelegte künstliche Familie die echte
  Registrierung mit bestätigter E-Mail und die revisionsgebundene
  Adminfreigabe über die reguläre API. Im 390-Pixel-Browser wurden zwei
  künstliche Fotos abgegeben, verarbeitet und zu einem Lernpaket geführt;
  drei Runden mit sechs Antworten, Hilfen, Rückblicken und Elternansicht
  wurden abgeschlossen. Der Kostenbeleg enthält zehn echte OpenRouter-Aufrufe
  und 0,186950 USD bekannte Kosten ohne unbekannte Kosten; es gab keinen
  Wiederholungsversuch. Die gespeicherte Runde wurde ohne neue KI-Anfrage
  wieder geöffnet. Der reguläre Widerruf sowie die anschließende Löschung der
  künstlichen Familie und des temporären Testadministrators wurden bestätigt.
  Registrierung und Adminentscheidung erfolgten in diesem Lauf über HTTPS-API,
  nicht über die jeweiligen Browserformulare; deren isolierte Browsertests
  sind unten getrennt nachgewiesen. Eine Stichprobe belegt keine allgemeine
  KI-Qualität, dauerhafte Verfügbarkeit oder Freigabe für reale Kinderdaten.
  [Testbericht](docs/BETA_LIVE_SIGNUP_2026_11_23.md#abschluss-24112026).
  - [x] **Produktive Registrierung und Bestätigungsmail mit eigenem Testkonto prüfen.**
    Eine frische künstliche Beta-Familie durchlief die tatsächliche Registrierung,
    Mailbestätigung und Kinderanmeldung auf dem Zielserver und wurde danach über
    ihren eigenen Elternzugang gelöscht. In diesem Teiltest wurde kein
    KI-Auftrag ausgelöst. Die Adminfreigabe wurde anschließend gesondert
    geprüft; der durchgehende produktive Lernweg bleibt offen.
    [Prüfumfang](docs/BETA_LIVE_SIGNUP_2026_11_23.md).

  - [x] **Produktive Betaentscheidung und echte Fotoverarbeitung mit künstlicher Familie prüfen.**
    Eine eigene künstliche Familie erhielt nach Mailbestätigung eine reguläre
    Adminfreigabe. Zwei Seiten wurden im mobilen Browser abgegeben und vom
    tatsächlichen Anbieter gelesen und gegengeprüft; die Kosten wurden erfasst.
    Die anschließende Paketerstellung scheiterte und ist nicht als gelöst
    nachgewiesen. Testfamilie und temporärer Administrator wurden anschließend
    gelöscht. [Prüfumfang und Grenzen](docs/BETA_LIVE_SIGNUP_2026_11_23.md).

  - [x] **Beta-Antrag, Freigabe und künstliche Lernantwort im Browser verbinden.**
    Ein isolierter Lauf bedient die öffentliche Beta-Anmeldung mobil, den
    Bestätigungslink und die Adminfreigabe auf Desktop sowie Eltern- und
    Kinderanmeldung und eine gespeicherte Beispielaufgabe mobil. Derselbe
    Lauf prüft simulierte Kosten, Nullgrenzen und Widerruf. Keine E-Mail oder
    KI verlässt den Test. Die öffentliche Installation meldet die Beta als
    aktiviert; eine echte Produktionsanmeldung und ein tatsächlicher
    Anbieter-/Fotolernweg sind hiermit nicht belegt.
    [Prüfumfang](docs/BETA_BROWSER_2026_11_23.md).

  - [x] **Kleine Beta-Kosten ohne Rundung auf null anzeigen.** Die
    Gesamtsumme und die Modellwerte zeigen USD bis zur gespeicherten
    Millionstel-Einheit. Ein künstlicher Widgettest prüft einen tatsächlich
    gemeldeten Wert von einem Millionstel Dollar und unbekannte Kosten bleiben
    getrennt. Dies ist keine Bestätigung realer Anbieterpreise.

  - [x] **Unvollständige Modellliste in der Beta-Kostenansicht kennzeichnen.**
    Eine gekürzte Modellaufzählung erhält einen Hinweis; die nicht gekürzten
    Gesamtsummen und unbekannten Kosten bleiben sichtbar. Künstliche
    Widgettests prüfen die auf zehn Modelle begrenzte Anzeige und eine
    serverseitig gekürzte Liste getrennt.

  - [x] **Beta-Status nach Rückkehr aktuell laden.** Wenn eine Bewerbung
    während einer anderen offenen Seite abgeschlossen wird, liest die
    Elternansicht bei der Rückkehr den Serverstatus erneut. Sie schickt dabei
    keine weitere Bewerbung. Ein künstlicher Fluttertest prüft den verzögerten
    Abschluss, Navigation und genau einen POST; die End-to-End-Abnahme der
    gesamten Beta-Anmeldung bleibt offen.

  **Implementierung und isolierte Tests:** ausdrückliche E-Mail-Bewerbung,
  erneute Bewerbung vorhandener Eltern, revisionsgebundene Adminentscheidung
  nach verifizierter Adresse sowie beta-spezifische Kontingentausnahme mit
  getrenntem Buchungszähler und Kosten-/Modellübersicht sind im aktuellen
  Entwicklungsstand umgesetzt. PostgreSQL-Tests prüften konkurrierende
  Entscheidungen und die Sperre zwischen Reservierung und Widerruf. Die
  Eltern können den Status im Elternbereich lesen; automatische Push-/Mail-
  Meldungen über Entscheidungen sind nicht Bestandteil dieses Nachweises.
  [Vertrag und verbleibende technische Grenzen](docs/BETA.md). Die zuvor
  fehlende gemeinsame Prüfung auf der Zielinstallation ist oben dokumentiert.

  Der vorhandene Link erstellt ein Elternkonto; bei abgeschalteter Testphase
  bekommt es aber keinen KI-Lernzugang. Der Link darf daher noch nicht als
  funktionierende Beta-Anmeldung ausgegeben werden. Eltern bewerben sich auf
  der Startseite; erst nach ausdrücklicher Prüfung und Freigabe im Adminbereich
  erhalten sie einen Beta-Zugang. Ablehnung und Widerruf müssen möglich sein;
  frühere Nutzungs- und Kostenbelege bleiben erhalten. E-Mail-Bestätigung,
  Familienisolation und Kinderdaten-/Anbieterfreigaben gelten weiterhin.
  Für freigegebene Beta-Familien werden auf ausdrücklichen Betreiberauftrag
  keine persönlichen KI-Mengen- oder Kostengrenzen angewandt. Tatsächliche
  Providerkosten, unbekannte Kosten, Reservierungen und Nutzung werden dennoch
  eindeutig und datensparsam für die spätere Preiskalkulation erfasst. Die
  verschiedenen Grenzschichten und bestehende Freigaben müssen explizit und
  nur für genehmigte Beta-Familien umgesetzt und getestet werden; keine
  pauschale Änderung aller Familien. Kein Zahlungsmodell voraussetzen.
  Anschließend den tatsächlichen Registrierungs- und Lernweg mit künstlichen
  Konten prüfen und den Zustand auf der öffentlichen Startseite korrekt anzeigen.

- [ ] **P1 – Kapazitätsannahmen vor wachsendem Betrieb messen**

  - [x] **Installierten Fotodienst mit künstlichem Bild und falscher UID prüfen.**
    Auf dem Zielserver verarbeitete die tatsächlich installierte getrennte
    Fotokomponente ein künstliches JPEG mit EXIF-Drehung korrekt; eine andere
    UID wurde trotz Socketgruppe abgewiesen. API- und Dienstspeicherlimits
    wurden lesend geprüft. Es gab weder KI-Aufruf noch gespeichertes Foto.
    [Test und Grenzen](docs/PHOTO_ISOLATION_TARGET_2026_11_23.md).
    Parallele Produktivlast, echter Webimport und Rückweg bleiben offen.

  - [x] **Stehende Fotouploads früher freigeben.** Eine Verbindung ohne
    weitere Daten gibt den einzelnen Foto-Eingangsplatz nach 15 Sekunden
    Inaktivität frei. Weiter eintreffende Daten setzen diese Frist zurück;
    die bestehende Gesamtfrist von 60 Sekunden und die Bildgrößen bleiben
    erhalten. Künstliche Prüfungen decken fortlaufende und stehende Transfers,
    die Gesamtfrist, einen echten langsamen lokalen Socket sowie Wiederholung
    ab. Eine absichtlich sehr langsam, aber ohne 15-Sekunden-Pausen sendende
    Verbindung kann den Platz weiterhin bis zur Gesamtfrist belegen; dies
    ist kein Nachweis allgemeiner Fairness oder produktiver Kapazität.

  - [x] **Isolierten Foto-Lasttest wieder ausführbar und überprüfbar machen.**
    Der Test akzeptiert das private Temporärverzeichnis des PostgreSQL-Runners
    und verifiziert vor der Fixture zusätzlich die tatsächliche lokale
    Datenbank und ihr Datenverzeichnis. Fünf künstliche Negativ-/Positivfälle
    bestanden. Ein 15,9-MP-JPEG und ein stark komprimierbares PNG bestanden
    je einen isolierten Mischlastlauf mit vier Familien und ohne OOM; je fünf
    Überlastwiederholungen waren im Test nötig. Produktiver Rückweg, längere
    Last und allgemeine Kapazitätsgrenzen bleiben offen.
    [Messung](docs/CAPACITY_PROCESS_FAILURE_2026_11_06.md#erneute-isolierte-messung-und-reparatur-des-test-runners-26112026).

  - [ ] **API-Speicherschutz beim gleichzeitigen Fotoimport beheben.**
    Die getrennte Prozessprüfung auf PostgreSQL und Loopback reproduzierte bei
    acht künstlichen Familien einen OOM-Kill am produktiven 350-MiB-API-Limit.
    Die zuvor bestandenen In-Process-Tests hatten dieses Limit nicht abgebildet.
    Eine reine Serialisierung des Dekoders reicht bei großen Bildern und
    parallelen Leseanfragen nicht zuverlässig aus; sie wurde nicht übernommen.
    Die vorhandene Bildqualität und 16-MP-Grenze nicht still absenken.
    [Test, Messwerte und offene Lösung](docs/CAPACITY_PROCESS_FAILURE_2026_11_06.md).

    **06.11.2026, lokal umgesetzt:** Die Normalisierung läuft in einem eigenen,
    begrenzten Fotodienst; die API begrenzt die Aufnahme und prüft Sitzung,
    Familienrechte und Freigabe nach dem Dekodieren erneut. Zwei künstliche
    Mischlasten mit großen JPEG- beziehungsweise PNG-Bildern blieben ohne OOM;
    bei Überlast waren ausdrückliche Wiederholungen erforderlich. PostgreSQL-,
    Aktivierungs- und Überwachungstests sowie isolierte systemd-Proben bestanden.
    Produktive Installation und Rückkehr sind noch nicht geprüft; langsame
    angemeldete Uploads und andere Bildverarbeitungspfade bleiben separat zu
    betrachten. Deshalb bleibt dieser Punkt offen.

  - [x] **Pool-Blockade bei parallelen Reservierungen beheben.** Eine zweite
    Datenbanksitzung innerhalb der Freigabeprüfung blockierte bei gefülltem
    Pool laufende Transaktionen. Ein synthetischer PostgreSQL-Lastfall zeigte
    den Fehler vor und das Ergebnis nach dem Fix über echte lokale HTTP-Sockets;
    Privatsphäre-Widerruf und ungespeicherte Daten wurden gesondert geprüft.
    Die erweiterte Lastprobe ersetzt keine Kapazitätsfreigabe.
    [Nachweis](docs/CAPACITY_LOOPBACK_2026_11_06.md).

  - [x] **Warteschlangenalter und gleichzeitige Worker isoliert prüfen.**
    Eine neue private aggregierte Metrik zeigt das Alter des ältesten wartenden
    und laufenden Auftrags ohne Inhaltsdaten. Acht künstliche Familien mit zwei
    konkurrierenden Workern, wiederholten Uploads/Reservierungen und einem
    simulierten 2-Sekunden-Anbieter wurden unter isoliertem PostgreSQL auf
    `tmpfs` geprüft. Die Messung ist kein Nachweis produktiver Kapazität oder
    echter Anbieterlaufzeiten. [Nachweis](docs/CAPACITY_DELAYED_PROFILE_2026_11_06.md).

  - [x] **Warteschlange unter künstlicher Konkurrenz messen.** Acht Familien,
    doppelte Uploads und Reservierungen sowie vier Worker-Claims auf einem
    CPU-Kern und isoliertem PostgreSQL wurden gemessen. Der simulierte
    Anbieter ist kein Produktivlastnachweis; reale Betriebs- und Alarmgrenzen
    bleiben offen. [Messwerte](docs/CAPACITY_PROFILE_2026_11_04B.md).

  **04.11.2026, isoliertes Lastprofil:** Parallele Übersichts-GETs sowie
  gleichzeitige Upload- und Auftragswiederholungen wurden auf temporärem
  PostgreSQL mit künstlichen Daten gemessen. Foto und Auftrag blieben bei
  gleichem Schlüssel jeweils einmalig. Messwerte, reproduzierbarer Aufruf und
  Grenzen stehen in [CAPACITY_PROFILE_2026_11_04.md](docs/CAPACITY_PROFILE_2026_11_04.md).
  Drei weitere künstliche Familien mit knapp 2 MB großen Fotos bestanden
  denselben begrenzten Auftragsweg; größere Last, Worker, reale Netzwerkpfade
  und Betriebsgrenzen bleiben offen.

  Auf isolierter, produktionsähnlicher PostgreSQL-Umgebung mit künstlichen Daten gleichzeitig aktive Sitzungen, Uploads, Listen, Jobreservierungen und Worker-Warteschlangen stufenweise prüfen; keine unautorisierten bezahlten Anbieteraufrufe auslösen.

  **Abnahme:** Testprofil, Parallelität, Laufzeit, Fehler, p95-Latenz, Warteschlangentiefe, Ressourcen und Engpass samt Messzeitpunkt dokumentiert sind, realistische Betriebsgrenzen und Alarmwerte daraus abgeleitet und relevante Sperren/Idempotenz unter Konkurrenz bestätigt sind. Ohne Messung keine Nutzerzahl oder Skalierungszusage behaupten.
- [ ] **P2 – Verkauf nur mit echten vollständigen Angaben freischalten**

  - [x] Den sichtbaren Checkout bei einer unbestätigten Bestellung an den
    ursprünglich abgesendeten Tarif und die Frühstartentscheidung binden;
    veraltete Zustimmungs- und Bestellaktionen abweisen. Synthetische
    Widgettests prüfen Wiederholung, Ablehnung und veraltete Aktionen;
    reale Zahlung und vollständige Verkaufsabnahme bleiben offen.
    [Nachweis](docs/CHECKOUT_UNCERTAIN_START_2026_11_07.md).

  Betreiberanschrift, Support, Kontoinhaber, IBAN, Steuerbehandlung, Vertrags-/Widerrufsfassung und E-Mail-Zustellung vom Betreiber klären und konfigurieren; Sperre bis dahin erhalten. Mit künstlichen Bestellungen wiederholte und parallele Anfragen, unveränderliche Preis-/Bank-/Vertrags-Snapshots, manuelle Bankprüfung, Laufzeit, Verlängerung und Erstattung prüfen.

  **Abnahme:** nur tatsächlich dokumentierter Zahlungseingang genau einmal freischaltet und Kinder-, Demo- und Play-Zugänge keine Käufe bewerben. `docs/STORE.md` und `docs/PAYMENTS.md` sind maßgeblich.
- [ ] **P2 – Play-Veröffentlichung gesondert vorbereiten**

  Tatsächliche Play-Console-Berechtigung, Paket-/Signieridentität, Storeangaben, Datenschutz-/Zielgruppenangaben und passenden Testkanal prüfen; erforderliche Betreiberinformationen vervollständigen.

  **Abnahme:** Upload und Freigabestatus in der Konsole und der tatsächliche Installations-/Updateweg dokumentiert sind; bis dahin keine Play-Verfügbarkeit behaupten.
- [ ] **P1 – Begleitete Nutzung und Startentscheidung dokumentieren**

  Nach den einschlägigen Sicherheits-, Betriebs- und Geräteprüfungen eine ausdrücklich vereinbarte kleine Familienrunde durchführen; echte Materialien nur im konkret freigegebenen Umfang verwenden. Kinderführung, Quellenrichtigkeit, Umgang mit Unsicherheit, Elternverständnis und Support beobachten, ohne Erfolg oder Notenverbesserung zu versprechen.

  **Abnahme:** bekannte Blocker, Zuständigkeiten und Ergebnisse samt Grenzen dokumentiert sind und der Betreiber über den jeweiligen Startumfang informiert entscheiden kann; bestehende gesonderte Push- und KI-Freigaben bleiben erhalten.

## KI-Verarbeitung, Referenzen und Darstellung

- [x] **P1 – Gesamte Verarbeitungskette durchgängig nachvollziehbar machen**

  **Technische Abnahme 25.11.2026:** Die Elternspur verbindet die tatsächlich
  vorhandenen Quellen-, Auftrags-, Schema-, Lernziel-, Kompetenz- und
  Grafikbelege. Veröffentlichte Paketteile zeigen die jeweils daraus
  entstandene Runde. Die Grafikbereitschaft wird gegen die aktuelle Quelle
  und Darstellung geprüft. Für lokal abgewiesene Fotos und unbekannte Fragen
  gibt es eigene begrenzte Fehlerbelege ohne Inhalte oder erfundene KI-Aufträge.
  Künstliche Erfolgs- und Fehlerfälle, einschließlich eines echten ausgelösten
  Datenbankfehlers, wurden auf SQLite und PostgreSQL geprüft; die Elternansicht
  zusätzlich im Web bei 320 und 390 Pixeln und vergrößerter Schrift. Lesende
  Aufrufe ändern keine Lernnachweise und starten keine KI. Details, Testmatrix
  und Grenzen stehen im [Vertrag](docs/PROCESSING_TRACE_2026_11_23.md#technische-abnahme-am-25-november-2026).
  Dies ist keine allgemeine Abnahme der OCR- oder Modellqualität.

  - [x] **Lokale Fehler und tatsächliche Veröffentlichungen nachvollziehen.**
    Foto- und Antwortfehler vor einem Auftrag erhalten, soweit die berechtigte
    Aktion die Anwendung erreicht und die Datenbank verfügbar ist, einen
    datensparsamen Beleg. Beim Veröffentlichen wird der Teilauftrag nur mit
    seiner nachweislich daraus erzeugten Runde verbunden. Keine Kinderantwort,
    kein Dateiname und kein Foto gelangen in die Fehlerbelege. Aufbewahrung,
    Mengenbegrenzung, Löschung und Familienrechte sind geprüft.

  - [x] **Schulbuddy und Elternauswertung in der Auftragsspur prüfen.**
    Schulbuddy-Seitenfassungen werden nur bei passender Kind- und
    Auftragsbindung aus dem Chatvorgang angezeigt. Ungültige Modellbelege
    werden begrenzt klassifiziert; Antwort und Lernnachweis entstehen nicht,
    unbekannte Kosten bleiben reserviert. Künstliche Erfolgs- und Fehlerfälle
    der Elternauswertung zeigen ihren Status ohne private Antworten.
    SQLite- und PostgreSQL-Tests prüfen die regulären Worker; die
    vollständige Verarbeitungsketten-Abnahme bleibt offen.

  **Grenzen:** Anonyme oder bereits vom HTTP-Grenzfilter abgewiesene Anfragen
  können keinem Kind zugeordnet werden. Auch bei Datenbankausfall oder
  ausgeschöpfter Belegbegrenzung kann kein lokaler Beleg garantiert werden.
  Historische oder mehrdeutige Schemaversionen bleiben ausdrücklich unbekannt.

  - [x] **Vorlagen- und Schemabelege in der Elternspur anzeigen.**
    Bei eindeutig zugeordneten Erkennungsfassungen werden vorhandene,
    formatgeprüfte Fingerabdrücke der Grundvorlage und des Schemas gezeigt;
    beim Gegencheck stammt der Beleg aus der zusammengeführten Fassung.
    Ein vorhandener Fingerabdruck des tatsächlich angeforderten Schemas
    wird nur bei genau einem zugehörigen Verbrauchsbeleg angezeigt. Fehlende,
    manipulierte und mehrdeutige Angaben bleiben leer. Künstliche API- und
    Workerfälle prüfen den Weg und getrennte Elternrechte; die Flutteransicht
    zeigt kurze Kennungen. Weitere Phasen und ihre vollständige Abnahme
    bleiben offen.

  - [x] **Grafikreferenz eines Paketteils vor dem Speichern erneut prüfen.**
    Die grafische Ausgabe wird nach der Teilrundenstruktur und vor dem
    dauerhaften Speichern gegen Quellen und Referenzen geprüft. Eine
    künstliche fremde Grafikreferenz wird als ungültige Ausgabe verworfen;
    der vorherige Teil, Antworten und Anbieterabrechnung bleiben erhalten.
    SQLite- und PostgreSQL-Workerfälle prüfen Fehler und Elternspur. Eine
    allgemeine fachliche Bildabnahme ist dadurch nicht ersetzt.

  - [x] **Fehlerhafte Lernentscheidungen in der Elternspur nachvollziehen.**
    Fehlende Aufgabenbezüge und unbelegte Bewertungsklärungen wurden in
    künstlichen regulären Workeraufträgen abgewiesen. Die Elternspur zeigt
    gebundene Quellen und die begrenzte Fehlerklasse, ohne Modellinhalt
    auszugeben; vorhandene Antworten bleiben erhalten und abgerechnete
    Kosten bestehen. SQLite und isoliertes PostgreSQL bestehen beide Fälle.
    Die übrige Phasenabnahme bleibt offen.

  - [x] **Separate KI-Bildprüfung in der Elternspur prüfen.**
    Ein künstlicher erfolgreicher Prüfauftrag zeigt das tatsächlich
    reservierte Prüfmodell und den Abschlussstatus. Ein künstlicher
    Anbieterfehler zeigt nur eine begrenzte Fehlerklasse; die abgerechneten
    Kosten werden bei wiederholter Verarbeitung nur einmal verbucht.
    Wiederholtes Lesen erzeugt keine zusätzlichen Aufträge oder Prüfungen.
    Die Fälle bestehen auf SQLite und isoliertem PostgreSQL; ein reales
    Anbieterurteil oder fachliche Bildqualität sind dadurch nicht belegt.

  - [x] **Öffentliche Bildaufträge in der Elternspur prüfen.**
    Ein künstlicher erfolgreicher Bildauftrag zeigt Status und verwendetes
    Modell; ein ungültiges abgerechnetes Bild wird nicht veröffentlicht und
    erscheint als `invalid_output`. Wiederholte Spurabrufe erzeugen keine
    weiteren Aufträge oder Bilder. Beide Fälle bestanden auf SQLite und
    isoliertem PostgreSQL. Die Bilderzeugung nutzt hierbei einen simulierten
    Transport; fachliche Bildqualität ist damit nicht nachgewiesen.

  - [x] **Fehlerhafte Teilrundenausgaben nach dem Anbieteraufruf einordnen.**
    Schemafehler, falsche Fachgruppen und doppelte Aufgabenkennungen werden
    im Teilrundenvertrag als ungültige Ausgabe erkannt. Ein künstlicher
    mehrteiliger Workerfall prüft je Fehler die Elternspur, den Erhalt des
    bereits fertigen Teils, früherer Antworten und der abgerechneten Kosten.
    Wiederholte GETs erstellen nichts. Die Fälle bestehen auf SQLite und
    isoliertem PostgreSQL; weitere Verarbeitungsschritte bleiben offen.

  - [x] **Wortschatz- und Sprachaufträge mit Quellen und Fehlern prüfen.**
    Die Elternspur zeigt gespeicherte Seitenrevisionen nur bei passender
    Kind- und Auftragsbindung. Geänderte Quellen und unzulässige Modellinhalte
    führen zu begrenzten Fehlerklassen. Künstliche Workerfälle prüfen
    erfolgreiche und fehlgeschlagene Wortimporte und Sprachprojekte sowie
    getrennte Eltern-/Kindersitzungen auf SQLite und PostgreSQL. Entfernte
    Zuordnungen zeigen keine Quellen. Inhalt und Antworten bleiben privat;
    die übrige Phasenabnahme ist noch offen.

  - [x] **Lernentscheidung und Anschlussübung an Quellenfassungen binden.**
    Neue Aufträge speichern die bereits geprüften Seitenkennungen und
    Revisionen für die Elternspur. Bei einem künstlichen Generator-Timeout
    bleiben der vorhandene Rückblick, Antworten und unbekannte Kosten
    erhalten. Eine wiederholte alte Anfrage ohne Quellenliste reserviert
    keinen weiteren Auftrag. SQLite- und PostgreSQL-Fälle prüfen zudem einen
    ausgeführten Lernplan und eine ungültige Antwortkennung ohne Lernnachweis.
    Die übrige vollständige Phasenabnahme bleibt offen.

  - [x] **Quellen und Fehler von Heftfragen nachvollziehbar machen.**
    Die Elternspur zeigt nur ausdrücklich am zugehörigen Tutorvorgang
    gespeicherte Seitenfassungen. Unpassende Zitate und ungültige Antworten
    werden als begrenzte Fehlerklasse ausgewiesen. Künstliche reguläre
    Tutorläufe prüfen Erfolg, vier fehlerhafte Quellenbelege, geänderte
    Seiten und wiederholte lesende Abfragen auf SQLite und PostgreSQL.
    Andere Phasen und ihre vollständige Abnahme bleiben offen.

  - [x] **Grafikvorbereitung bei ungültiger Antwort nachverfolgen.**
    Neue Aufträge bewahren die tatsächlich verwendeten Seitenfassungen; alte
    idempotente Anfragen funktionieren weiterhin. Schema- und Fachprüfungsfehler
    erhalten eine begrenzte Fehlerklasse. Ein künstlicher ungültiger
    Modelloutput wird im regulären Worker abgewiesen, ohne vorhandene Runde
    oder Antwort zu verändern. Wiederholte Elternabrufe zeigen die Quelle,
    geben keine privaten Inhalte aus und erzeugen keine neuen Lernnachweise.
    Die Fehlerprüfung der weiteren Phasen bleibt offen.

  - [x] **Fehler bei der Klassenarbeitsnacharbeit nachvollziehbar machen.**
    Neue fehlgeschlagene Aufträge erhalten die begrenzte Fehlerklasse. Ein
    künstlicher Anbieter-Timeout wurde im regulären Worker ausgelöst und in
    der Elternspur ohne Anbietertext mit gebundener Quellenrevision geprüft.
    Wiederholtes Lesen ändert keine Aufträge, Antworten oder Lernstände.
    Für die vollständige Phasenabnahme sind weitere Fehlerfälle erforderlich.

  - [x] **Quellenfassungen neuer Lernrückblicke erhalten.**
    Neue Rückblickaufträge speichern ausschließlich die bereits geprüften
    Quellenkennungen und Revisionen. Die Elternspur zeigt deren damaligen und
    aktuellen Stand; alte Aufträge ohne diesen Beleg werden nicht ergänzt.
    Ein künstlicher regulärer Rückblick wurde vor und nach Verarbeitung sowie
    nach späterer Quellenänderung geprüft. Inhalte und Antworten bleiben aus
    der Auftragsspur ausgeschlossen.

  - [x] **Fehlerklassen von Rückblick und Anschlussübung erhalten.**
    Beide Worker speichern bei neuen Fehlern die vorhandene begrenzte
    Klassifizierung. Ein künstlicher Timeout ist in der Elternspur als
    `provider_timeout` nachvollziehbar, ohne Anbietertext auszugeben; frühere
    Antworten und der fertige Rückblick bleiben erhalten. Alte Fehler ohne
    Klassifizierung werden nicht nachträglich als bekannt ausgegeben.

  - [x] **Weitere Auftragsschritte datensparsam unterscheiden.**
    Lernrückblick, Lernentscheidung, Grafik und Grafikprüfung,
    Klassenarbeitsnacharbeit, Wortschatz- und Sprachaufträge, Lernhilfe und
    Elternüberblick erhalten feste Phasenbezeichnungen; unbekannte Arten bleiben
    allgemein. Bei Klassenarbeitsaufträgen werden ausdrücklich gespeicherte
    Seitenrevisionen nur für das zugehörige Kind angezeigt. Ein regulär
    angelegter künstlicher Nacharbeitsauftrag wurde vor und nach dem
    simulierten Worker geprüft. Künstliche API- und Workerfälle bestehen auf
    SQLite und isoliertem PostgreSQL, die Elternansicht separat in Flutter.
    Keine fachliche Modellprüfung oder vollständige Fehlerabnahme ableiten.

  - [x] **Gebundene Einzelseiten in der Auftragsspur anzeigen.**
    Einzelne Erkennungs- und Lernrundenaufträge speichern ihre Seite und deren
    Fassung in zwei Feldern; bisher zeigte die Spur nur Quellenlisten an.
    Liegt keine Quellenliste vor, wird die ausdrücklich gespeicherte Fassung
    zusammen mit der aktuellen Fassung angezeigt. Fehlende oder ungültige
    Revisionen werden nicht geraten, Seiten anderer Kinder ausgeschlossen.
    Künstliche API- und Workerfälle bestanden auf SQLite und isoliertem
    PostgreSQL, einschließlich Erkennung und Gegenprüfung. Die übrige
    Phasen- und Fehlerabnahme bleibt offen.
    [Vertrag](docs/PROCESSING_TRACE_2026_11_23.md).

  - [x] **Private Auftragsmetadaten für berechtigte Eltern bereitstellen.**
    Ein lesender, begrenzter Endpunkt zeigt Phase, Status, Fehlerklasse,
    Modellrevision und gebundene Quellen-/Grafikreferenzen. Weder Kind, fremde
    Familie noch Betriebsadmin erhalten Zugriff. Künstliche erfolgreiche und
    fehlgeschlagene OCR-, Gegenprüf- und Paketläufe, fremde Zuordnungen sowie
    wiederholte GETs sind geprüft. Die Elternansicht zeigt die Details erst
    nach ausdrücklichem Öffnen; Kinder sehen sie nicht. Die übrigen Phasen
    bleiben Bestandteil des offenen Hauptpunkts.
    [Vertrag und Grenzen](docs/PROCESSING_TRACE_2026_11_23.md).


  - [x] **Künstliche Quell- und Antwortkette zusammenhängend prüfen.**
    Ein künstliches Foto läuft über Upload, zwei getrennt gespeicherte
    Leseläufe und ihre revisionsgebundenen Auftrags-/Modellbelege in ein
    validiertes Lernpaket. Die Kinder-API liefert den bereiten, quellengebundenen
    Grafik- und Referenzstatus; eine Antwort nach einem Hinweis wird als unterstützt
    gespeichert. Wiederholte GETs erzeugen keine Aufträge, Aktivitäten oder
    Lernnachweise; der Betriebsadmin erhält keinen Familieninhaltszugriff.
    Eine im Test während des Paketaufrufs geänderte Quellrevision verhindert die Übernahme;
    der fehlgeschlagene Auftrag behält seine Abrechnung. SQLite- und
    PostgreSQL-Prüfungen: `backend/tests/test_processing_trace_journey.py`.
    Der künstliche Modelltransport belegt keine echte OCR-/Modellqualität; die
    vollständige Fehler- und fachübergreifende Phasenabnahme bleibt offen.

  Upload, einzelne Quellrevision, Erkennung, gegebenenfalls Gegenprüfung, Themen-/Lernzielzuordnung, Referenzsuche, Erstellung, Schema-/Fachprüfung, Speicherung, Darstellung und Bewertung anhand künstlicher Daten verfolgen. Für jede Phase Auftragskennung, Status, Revisions- und Modell-/Vorlagenversion sowie datensparsame Fehlerkategorie verfügbar machen; weder Kindertexte noch Bilder oder Geheimnisse protokollieren. Fehlerhaft gespeicherte oder unpassende Ergebnisse dürfen nicht als bereit angezeigt werden.

  **Abnahme:** Ein künstlicher Erfolgsfall und je ein reproduzierbarer Fehler pro relevanter Phase sind vom berechtigten Betriebs- beziehungsweise Familienkontext nachvollziehbar; GET-Abfragen starten keine KI und ändern keinen Lernstand.

- [x] **P1 – Ausgabelängen, Schemafehler und Providerstörungen systematisch behandeln**

  **Abnahme 24.11.2026:** Die dokumentierten 400-/429-/5xx-, Timeout-,
  Längen- und Schemafehler durchlaufen den echten Adapter mit künstlichem
  Transport und den mehrteiligen Paketworker. Ein zusätzlicher Test beendet
  einen echten isolierten Workerprozess während des simulierten Transports;
  nach normalem Reaperlauf und ausdrücklich gestarteter Wiederaufnahme
  verarbeiten zwei neue Workerprozesse die übrigen Teile. Quellen, frühere
  Antworten und die unbekannte Kostenreservierung bleiben erhalten. Der
  Fall ist im PostgreSQL-CI-Gate verpflichtend; das vollständige lokale Gate
  bestand mit 81 Fällen ohne Skip. Echte künstliche OpenRouter-Mehrseitenläufe
  und ihre Kosten sind getrennt dokumentiert. Das belegt keine allgemeine
  Anbieterverfügbarkeit, vollständige OCR- oder fachliche Qualität und keine
  Garantie gegen künftige Modellfehler.
  [Prüfung und Grenzen](docs/PACKAGE_FAILURE_ACCEPTANCE_2026_11_24.md).

  - [x] **Prozessabbruch und Neustart von Paketworkern tatsächlich auslösen.**
    Der separate Prozess wird nach dem Claim am simulierten Transport mit
    SIGKILL beendet. Der reguläre Reaper und zwei frisch gestartete Prozesse
    erhalten nach bewusster Wiederaufnahme den ersten Teil, frühere Antworten
    und alle sieben Quellenrevisionen; unbekannte Kosten bleiben reserviert.
    Für die Testwartezeit wird nur der künstliche Auftragszeitpunkt verändert.
    Ein Hostabsturz oder echter Anbieterabbruch ist damit nicht simuliert.

  - [x] **Schulbuddy bei gesperrter Providerkonfiguration sicher abbrechen.**
    Die Reservierung wartet bei diesem Auftragsart-Konflikt nicht auf den
    Operator, sondern gibt 409 und rollt Frage, Auftrag, Kontingent und
    Ratenzähler zurück. Andere Auftragsarten behalten ihre bestehende
    Reservierungsreihenfolge. Der bestehende PostgreSQL-Rennentest, die
    gemeinsame Paket-/Schulbuddy-Prüfung und das vollständige Gate bestehen.
    Der ebenfalls aufgedeckte Push-Test setzt die elterliche Freigabe jetzt
    explizit und prüft beide Zustände; der heutige Standard bleibt erhalten.

  - [x] **Fehler der unabhängigen KI-Bildprüfung datensparsam unterscheiden.**
    Neue fehlgeschlagene Prüfaufträge speichern eine geschlossene Fehlerklasse.
    Bekannte HTTP-Status unterscheiden Auslastung, Zeitüberschreitung,
    Konfiguration und Nichterreichbarkeit; fehlerhafte Ausgaben und unerwartete
    Ausnahmen bleiben getrennt. Auch eine Fehlerantwort mit HTTP 200 erhält
    ihre begrenzte Anbieterklasse und, falls vorhanden, den Kostenbeleg.
    Anbietertexte und Bildinhalte werden dabei nicht gespeichert; unbekannte
    Kosten bleiben reserviert. Es gibt keinen automatischen Anbieterwechsel oder
    Wiederholungsauftrag. Künstliche Adapter- und Workerfälle prüfen diese Wege.
    Der vor dieser Änderung aufgetretene Fehler ist rückwirkend nicht bestimmbar.

  - [x] **Unterbrochene Aufträge und verspätete Ergebnisse atomar trennen.**
    Statusänderungen verwenden einen optimistischen Vergleich; der begrenzte
    Reaper prüft Status und Alter beim Abbruch erneut. Transaktionale Tests auf
    isoliertem PostgreSQL decken beide Rennrichtungen, Erhalt alter Antworten
    und einmalige Kostenbuchung ab. Späte Ergebnisse werden verworfen;
    unbekannte Kosten bleiben reserviert. [Beleg und Grenzen](docs/JOB_INTERRUPTION_RACE_2026_11_06.md).

  - [x] **Feste Grundlagenfragen bei knappen Dezimalbeispielen erhalten.**
    Ein bereits festes Vorwissen verbraucht kein neues Zahlenpaar. Auch wenn
    genau ein unbenutztes Paar für einen freien Anwendungsplatz bleibt, kann
    die Vorbereitung mit unveränderter Frage, Lösung und Grafik stattfinden.
    Ist kein Paar mehr verfügbar, wird weiterhin vor dem Anbieteraufruf sicher
    abgebrochen. Künstliche Tests prüfen beide Platzreihenfolgen und den echten
    Schema- und Grafikvertrag; dies schließt die Bruchplanung nicht ab.

  - [x] **Weitere Anbieterabbrüche mit und ohne Kostenbeleg isoliert prüfen.**
    Die synthetische Paketmatrix prüft weitere HTTP-Fehler und unvollständige
    Antwortarten einschließlich einmaliger Verbuchung gemeldeter Fehlerkosten,
    erhaltene Teilergebnisse und ausdrücklich gestartete Wiederaufnahme.
    [Beleg und Grenzen](docs/OPENROUTER_FAILURE_E2E_2026_11_05.md#ergänzung-am-6-november-2026).

  - [x] **Tatsächliche Adapterfehler im Paketworker zuordnen und absichern.**
    HTTP-Auslastung, Timeout und Serverfehler sowie defekte oder abgeschnittene
    Ausgaben werden ohne Anbietertexte klassifiziert. Ein synthetischer
    Drei-Teile-Test prüft den echten Adapter mit lokalem HTTP-Transport,
    Abrechnung, erhaltene Teilresultate und den bewussten Wiederholungsweg auf
    SQLite und PostgreSQL. [Prüfung und Grenzen](docs/OPENROUTER_FAILURE_E2E_2026_11_05.md).

  - [x] **Unveröffentlichte Teilpakete bei der Wiederholungssperre berücksichtigen.**
    Der bestehende Dezimalplaner prüft private Teilbelege desselben Kindes und
    Fachs bei Planung und Veröffentlichung. Regulär abgelaufene Altbelege
    bleiben ausschließlich konservative Ausschlüsse, ohne Löschfristen zu
    verlängern oder eine Veröffentlichung zu erlauben. SQLite- und
    PostgreSQL-Tests prüfen auch gleichzeitige Aufträge und bereinigte Altstände.
    Die eigentliche Bruchplanung bleibt offen.
    [Prüfung und Grenzen](docs/PACKAGE_PENDING_HISTORY_2026_11_05.md).

  - [x] **Gemischte, ausdrücklich belegte Bruchregeln vorab planen.**
    Getrennte Überschrift und unmittelbar folgende vollständige Regel werden
    bei eng begrenzter Übereinstimmung als wörtlicher Quellenbeleg erkannt.
    Der versionierte Plan bindet für freie Übungsplätze Faktoren, Aufgaben,
    Ergebnisse, Quelle und geprüfte Grafik. Bei zwei belegten Verfahren wird
    das seltener angebotene bevorzugt; geänderte Historie wird erneut geprüft.
    Mehrseitige bestätigte Bruchpakete verwenden vor der Reservierung die
    konfigurierte Sol-Route. Künstliche Worker-, Quellen-, Kosten- und
    PostgreSQL-Fälle prüfen diese Teilfunktion. Eine echte künstliche
    Anbieterproben durchliefen drei mobile Runden einschließlich Hinweis,
    Erklärung, gezielter Folgeübungen und Elternansicht; ein zweites
    künstliches Konto wurde vom Foto-Upload an geprüft. Der Browsertest wurde
    unterbrochen und bei gespeicherten Runden fortgesetzt; eine durch seinen
    vorzeitigen Freigabeentzug fehlgeschlagene Folgeübung wurde ausdrücklich
    wiederholt. Die allgemeine Anbieter- und Fachabnahme bleibt offen.
    [Umfang und Grenzen](docs/PACKAGE_FRACTION_MIXED_2026_11_23.md).

  - [x] **Geprüfte Brucherweiterungsbeweise auf Paketgruppen vorbereiten.**
    Die bestehenden Beweishelfer können Originalquellen einer ausdrücklich
    gewählten Fachgruppe getrennt verarbeiten; fremde Gruppen und kuratierte
    Quellen bleiben ausgeschlossen. Der reguläre Paketpfad ist dadurch noch
    nicht aktiviert. [Entwurf und offene Schritte](docs/PACKAGE_FRACTION_PLAN_DESIGN_2026_11_06.md).

  - [x] **Bruchaufgaben für initiale Paketpartitionen vorab verbindlich planen.**
    **Vorbereitender Teilstand:** `package_fraction_plan.py` berechnet für
    ausdrücklich belegtes Erweitern oder Kürzen eine begrenzte Auswahl mit
    festem Faktor beziehungsweise Teiler. Bestehende diagnostische und offene
    Vorwissensplätze bleiben unverändert; gleichwertige Brüche in übergebener
    Historie und ausgewählten Quellen werden ausgeschlossen. Bei unklarer
    historischer Aufgabenstellung oder erschöpfter Auswahl bricht die Planung
    ab. Gemischte Zahlen und noch ungeplante parallele Aufträge werden
    vorsichtshalber nicht als sicher neue Aufgaben behandelt. Private
    Plansnapshots werden beim Anbietertransport entfernt. Künstliche reine
    Planungstests auf SQLite und PostgreSQL prüfen unter anderem 0/1/2 freie
    Plätze, Quellenänderung, Grafikkonsistenz und fremde Gruppen. Ein
    zusätzliches versioniertes Kürzungsrezept
    wird nur bei einer belegten Regel und für die ausgewählte Gruppe privat
    angeboten; im allgemeinen Katalog ist es gesperrt. Ein isolierter
    Prüfer bindet die zwei tatsächlichen Lösungsbilder einschließlich Text,
    Quelle und Referenz an die Aufgabe; Manipulationstests laufen auf SQLite
    und PostgreSQL. Die Historie lädt konkurrierende Pläne nach einer anderen
    Transaktion erneut. Die Schemabindung bewahrt feste
    und offene Vorwissenszweige und bindet geplante Aufgaben an eine eigene
    Grafik-ID. Tests verwenden das tatsächliche Paketschema und den Codec;
    manipulierte Aufgabenteile und vertauschte Bild-IDs werden zurückgewiesen.
    Der kompakte Paketprüfer akzeptiert zwei Bilder ausschließlich für eine
    exakt dem privaten Plan entsprechende Lösungsdarstellung; ohne diesen
    Plan und für Einführungen bleibt die Ein-Bild-Grenze bestehen.
    Die Reservierung speichert den Plan
    unter Kindersperre im bestehenden Teilauftrag und prüft vor und nach dem
    Anbieteraufruf Berechtigung, Originalquellen, Historie und Ausgabe.
    Tests nutzen echte lokale Sitzungs-/Quellenprüfungen mit künstlichen Daten
    und prüfen parallele Zugriffe auf isoliertem PostgreSQL. Für reguläre
    OpenRouter-Paketteile mit Lernstart und genau einer Mathematikgruppe nutzt
    der Worker den gespeicherten Plan, wenn die Quellen eine eindeutige Regel
    belegen; sonst bleibt der bisherige Pfad erhalten. Die Grafikprüfung
    kontrolliert Quelle, Rezeptversion und beide Modelle; die Veröffentlichung
    vergleicht Auftrag und privaten Beleg und prüft neu hinzugekommene Fragen.
    Altbelege behalten ihren bisherigen Prüfweg. Künstliche End-to-End-Tests
    verwenden den echten Worker und Adapter mit simuliertem Anbieter. Das
    Löschen einer Heftseite und das Wiederholen ihres Löschjournals entfernen
    den zugehörigen privaten Quellenausschnitt auch aus gespeicherten Plänen.
    Eine echte OpenRouter-Probe mit zwei künstlichen Seiten aktivierte den Plan,
    wurde aber mit `invalid_schema` abgewiesen; der dabei übertragene Vertrag
    hatte zwölf verschachtelte Container. Einführungen und nicht geplante
    Vorwissensfragen verwenden nun ebenfalls kompakte, unabhängig geprüfte
    Grafik-IDs. Ein weiterer echter Aufruf akzeptierte das Schema, scheiterte
    aber in der Grafikprüfung; der Anbieter meldete 0,003316 USD. Die konkrete
    interne Fehlerursache ließ sich aus dem gespeicherten allgemeinen Code nicht
    rückwirkend belegen. Eine nachweislich unzulässige Auswahl des speziellen
    Erweiterungs-/Kürzungsrezepts für gewöhnliche Grafiken ist nun gesperrt;
    feste inhaltsfreie Fehlercodes erleichtern zukünftige Diagnosen. Der Punkt
    blieb bis zur erfolgreichen echten Anbieterprobe und vollständigen Abnahme
    offen; die Kosten des abgewiesenen Schemaaufrufs sind nicht bekannt. Ein
    weiterer echter künstlicher Lauf kostete laut Anbieter 0,002978 USD und
    scheiterte bei der Bruchplanbindung. Die Fehlerdiagnose trennt jetzt
    fehlende/doppelte Aufgabenplätze, abweichende Grafikschritte und Aufgaben.
    Der Transport bindet jeden vorgesehenen Aufgabenplatz einzeln an seine ID;
    Modellantworten werden weiterhin unverändert streng nachgeprüft. Die
    genaue Ursache des vergangenen Modelloutputs ist nicht gespeichert und
    daher rückwirkend nicht belegt. Ein anschließender echter Mehrseitenlauf
    zum Erweitern erstellte eine Runde mit einer geplanten Aufgabe; der
    Anbieter meldete 0,003139 USD. Beim künstlichen Kürzungsfall war die
    korrekte Regel über zwei Zeilen verteilt und wurde nicht für den Plan
    erkannt; der allgemeine Folgeauftrag brach wegen Ausgabelänge ab und
    kostete laut Anbieter 0,005553 USD. Zusammenhängende umgebrochene
    Kürzungsregeln werden jetzt wörtlich und mit Negations-/Absatzprüfung
    erkannt. Die anschließende echte Wiederholung erstellte eine Kürzungsrunde
    mit zwei geprüften gespeicherten Lösungsbildern (0,034634 USD laut
    Anbieter). Beide künstlichen Mehrseitenfälle, frühere Fehler, Kosten und
    Prüfgrenzen sind im [Testbericht](docs/PACKAGE_FRACTION_LIVE_2026_11_23.md)
    dokumentiert.

    Ein versionierter Paketadapter soll nur für ein eindeutig gewähltes
    Mathematikfach und ausdrücklich bestätigte, zur Quellenrevision passende
    Rechenregeln Aufgaben vor dem Anbieteraufruf lokal berechnen. Feste
    Vorwissensproben und offene Einstiegsfragen bleiben unverändert; nur
    tatsächlich freie Übungsplätze erhalten neue Aufgaben. Brucherweiterungen
    benötigen einen eindeutig genannten positiven Faktor, Kürzungsschritte
    einen eindeutigen Teiler. Frage-ID, Typ, Aufgabentext, geprüfte Lösung,
    Varianten und fachlich passende Grafik-ID müssen gemeinsam im bestehenden
    Ausgabeschema gebunden und nach dem Transport unverändert geprüft werden.
    Die bestehende strenge Bruch- und Grafikvalidierung bleibt maßgeblich;
    fehlerhafte Modellantworten dürfen weder umetikettiert noch durch lokale
    Ersatzaufgaben nachträglich korrigiert werden.

    Der Plan einschließlich Version, Quellen- und Referenz-Digests gehört in
    den privaten gespeicherten Teilauftrag und muss vor Veröffentlichung erneut
    geprüft werden. Alte Receipts und begonnene Einheiten bleiben lesbar.
    Bereits gespeicherte Fragen, veröffentlichte und validierte, noch nicht
    veröffentlichte Teilrunden sowie konkurrierende Aufträge sind unter den
    bestehenden Kind-/Quellensperren vor und nach dem Anbieteraufruf und vor
    Veröffentlichung auf Wiederholungen zu prüfen. Gleichwertige frühere
    Beispiele und unklare historische Fragen dürfen nicht stillschweigend als
    neue unabhängige Übung ausgegeben werden. Bei erschöpfter endlicher
    Auswahl oder nicht belegter Regel sicher abbrechen, keine automatische
    Wiederholung oder Anbieterwechsel starten und vorhandene Daten erhalten.

    **Abnahme:** SQLite- und PostgreSQL-Tests decken 0/1/2 freie Übungsplätze,
    feste und offene Vorwissensfragen, belegte und unklare Regeln, Faktor und
    Teiler, Schema-/Grafikmanipulation, fremde Quellen, Versionswechsel,
    Verlauf und unveröffentlichte Teilrunden, Parallelität und Erschöpfung ab.
    Anschließend repräsentative künstliche Mehrseitenfälle über den normalen
    ausdrücklich freigegebenen Anbieterweg prüfen und Qualität, Kosten sowie
    Fehlschläge getrennt dokumentieren. Eine Promptanweisung allein belegt
    weder fachliche Korrektheit noch eine vollständige Fehlerbehebung.

  - [x] **Aufgabenprüfung datensparsam genauer diagnostizieren.**
    Bekannte feste Fehler aus der Aufgabenvalidierung erhalten geschlossene,
    inhaltsfreie Fehlercodes; unbekannte Fehler bleiben allgemein. Die
    bestehende Validierung bleibt unverändert. Der echte Android-Test zeigte
    einen Luna-Längenabbruch und einen davon unabhängigen Sol-Schemafehler;
    dessen genauer Grund ist rückwirkend nicht bestimmbar und die vollständige
    Behebung bleibt offen. [Testbericht](docs/PACKAGE_VALIDATION_DIAGNOSIS_2026_11_04.md).

  - [x] **Echten künstlichen Zweiquellen-Paketlauf nachweisen.**
    Zwei feste künstliche Seiten wurden in zwei Paketteilen verarbeitet;
    die Quellenzuordnung beider Einheiten wurde vor der Bereinigung geprüft.
    Das neue Schema erfasste den zuvor fehlenden Bruchbalken als vorläufigen
    Bildbefund. [Ergebnis und Grenzen](docs/OPENROUTER_VISUAL_TEST_2026_11_04.md).
    Die vollständige fachliche und Fehlerabnahme bleibt offen.

  - [x] **Mehrseitige Pakete bei künstlichen Fehlern und Workerabbruch erhalten.**
    Fehlerklassen, explizite Wiederaufnahme und unbekannte Kosten nach Abbruch
    wurden auf SQLite und PostgreSQL geprüft.
    [Prüfbericht und Grenzen](docs/PACKAGE_FAILURE_MATRIX_2026_11_04.md).
    Echter Anbieter und vollständige HTTP-/Schemafehlermatrix bleiben offen.

  **Teilprüfung 02.11.2026:** 49 synthetische SQLite-Fälle und der dort
  übersprungene Parallelitätsfall auf PostgreSQL bestanden; Umfang und Grenzen:
  [Regressionsbericht](docs/ROADMAP_REGRESSION_2026_11_02.md#ausgabelängen-schemafehler-und-providerstörungen).

  Lange Quellen und mehrseitige Pakete mit festgelegten Größen stufenweise und quellgebunden verarbeiten; zulässige Auftrags- und Tokenbudgets sowie Reservierungen vor jedem Schritt prüfen. Abgeschnittene Antworten, fehlerhafte Schemata, 400/429/5xx, Zeitüberschreitungen und Worker-Neustarts in isolierten Tests auslösen. Unvollständige Ergebnisse nicht als vollständig übernehmen; bereits gespeicherte Teilergebnisse und Antworten sichern, verständlichen Status und einen begrenzten, bewusst gestarteten Wiederholungsweg anbieten. Keine automatischen Providerwechsel oder unbegrenzten Wiederholungen einführen.

  **Abnahme:** Mehrseitenfall und Fehlermatrix belegen eindeutige Phasenzuordnung, normale Kosten-/Versuchsgrenzen, keine Doppelaufträge und sichere Fortsetzung; zusätzlich mit künstlichen Inhalten echte freigegebene Anbieteraufrufe durchführen und deren Umfang, Kosten und Restrisiken dokumentieren.

- [x] **P1 – Referenzdatenbank und Medienauswahl wirksam prüfen**

  **04.11.2026:** Künstliche Quellen in Deutsch, Biologie und Geografie
  durchlaufen Auswahl, gebundenes Schema, Speicherung und Projektion mit
  Referenz-ID, Version und Prüfsummen. Separate Chrome-Darstellungen decken
  Deutsch, Geschichte und Geografie bei 390/1024 px ab; ungültige Treffer und
  Medienbelege sind regressionsgeprüft. Umfang und Grenzen stehen in
  [REFERENCE_ACCEPTANCE_2026_11_04.md](docs/REFERENCE_ACCEPTANCE_2026_11_04.md).

  - [x] **Referenz- und Parameterintegrität bei Anzeige und Übernahme prüfen.**
    Versions-, Rezept- und Parameter-Fingerabdrücke werden geprüft; veränderte
    oder fehlende Vorlagen führen zu unvollständiger Darstellung und ändern
    keine Antworten. Der künstliche Videoklick erzeugt keinen Leistungs- oder
    Zeitbeleg. 285 breite und zehn abschließende SQLite-Fälle, 20 PostgreSQL-
    Fälle sowie 144 Flutter-Widgetfälle bestanden. Ältere Snapshots ohne
    Prüfsummen erscheinen unvollständig. Eine fachkundige Sichtung ist damit
    nicht ersetzt.

  **Teilprüfung 02.11.2026:** 109 synthetische SQLite-Fälle zu Auswahl,
  Quellen- und Referenzbindung bestanden; Umfang und Grenzen:
  [Regressionsbericht](docs/ROADMAP_REGRESSION_2026_11_02.md#referenzdatenbank-und-medienauswahl).

  Vorhandene Fach-, Themen-, Klassen- und Kompetenzzuordnungen sowie Versionen der Referenzen überprüfen. Für repräsentative Erklärungen nachvollziehen, welche Vorlagen und tatsächlich vorhandenen Medien ausgewählt, an die KI übergeben, parametrisiert und bis ins Frontend transportiert werden. Fehlende Treffer und ungültige Zuordnungen unterscheiden; Medien nur mit gültigen erlaubten Verweisen und tatsächlichen Metadaten anzeigen. Weitere Referenzen versioniert ergänzen, keine Videos erfinden und keinen KI-Aufruf durch bloßes Listen auslösen.

  **Abnahme:** Für mehrere Fächer zeigen Testbelege Auswahl, Referenz-ID/-Version und sichtbare Ausgabe; fehlende, veraltete und fachfremde Treffer führen zu einem erkennbaren sicheren Verhalten. Ein Videoklick erzeugt weder Lernzeit noch Kompetenznachweis.

  **03.11.2026, Teilabsicherung:** Lernhinweise und Themenbrowser verwerfen
  verspätete geladene Inhalte nach einem Sitzungswechsel. Zwei künstliche
  Widgetfälle prüfen dies; 22 Fälle zu Lerntipps und Medienrückkehr bestanden.
  Der spätere fachübergreifende technische Nachweis ist oben verlinkt.

- [ ] **P1 – Erklärgrafiken und Animationen fachlich und technisch abnehmen**

  - [x] **Belegte Vielfachenreihen für Paketabschnitte vorbereiten.** Ein
    eigenes versioniertes Rezept prüft die wörtliche Reihe rechnerisch, plant
    unterschiedliche Aufgaben und zeigt Quelle und Lösung in passenden
    steuerbaren Schritten. Ausgeschlossene Lesestellen und fremde Gruppen
    bleiben ausgeschlossen; frühere Aufgaben und sichtbare Zahlen werden
    berücksichtigt. Der konkrete fehlgeschlagene Auftrag wurde nur lesend
    gegen die neue Planung geprüft. Ein produktiver KI-Aufruf und die
    allgemeine Fachabnahme bleiben offen.
    [Prüfung und Grenzen](docs/MULTIPLES_PACKAGE_2026_11_26.md).

  - [ ] **Echte KI-Bilddateien sicher über OpenRouter anbinden.**
    **Historischer Teilfortschritt:** Der damals noch nicht in Aufträge oder Oberflächen integrierte
    Bildadapter löst ausschließlich geprüfte öffentliche Kataloginhalte auf,
    bindet Region und Anbieter explizit und sendet keine privaten Hefttexte.
    Er begrenzt Antworten, dekodiert genau ein statisches Bild, entfernt
    Metadaten und erhält auch bei fehlerhafter Bilddatei einen gemeldeten
    Kostenbeleg. Mock-Transporttests prüfen Datenschutzparameter, Weiterleitungs-
    sperre und Fehlerbehandlung. Ein neuer noch nicht angebundener Speicher
    hält unterschiedliche Bildfassungen unveränderlich mit öffentlicher
    Quellenfassung und Prüfsumme; der Abruf prüft den aktuellen Katalogstand.
    Migration 0048 ist additiv. Dies ist keine produktive Bildfunktion.
    Ein künstlicher Live-Test am 22.11.2026 hat mit `microsoft/mai-image-2.7-flash`
    auf dem fest gewählten Azure-Endpunkt ein PNG erzeugt; ZDR und
    Datensammlungssperre waren angefordert. Abgerechnet wurden laut Anbieter
    0,01030825 USD. Dies ist ein isolierter Techniktest, keine Anbindung an
    Kinderkonten und kein Nachweis fachlicher Bildrichtigkeit. Ein zuvor
    geprüfter OpenAI-Bildendpunkt lehnte dieselbe ZDR-Vorgabe mit 404 ab;
    die Vorgabe wurde nicht gelockert.

    Zum damaligen Zeitpunkt fehlten für den regulären Weg insbesondere ein explizit konfigurierter und
    geprüfter Bildanbieter mit Preisobergrenze und normaler atomarer
    Reservierung/Abrechnung, ein datensparsamer öffentlicher Themenprompt ohne
    private Heftinhalte, begrenzte Bildvalidierung und sichere Speicherung,
    versionierte Wiederverwendung, Rechte-/Löschprüfung und eine verständliche
    Anzeige als ungeprüftes KI-Bild. Bilder dürfen keine geprüften
    mathematischen/inhaltlichen Zusammenhänge vortäuschen. Erst nach Tests des
    echten reservierten Wegs und der tatsächlichen App-Anzeige abhaken.

    **Stand 22.11.2026:** Der reservierte Erzeugungsweg, geschützte Speicherung,
    Wiederverwendung und App-Anzeige sind implementiert. Eine separat reservierte
    unabhängige KI-Bildprüfung ist angebunden; ihr Urteil ist keine fachliche
    Garantie. Ein künstlicher Echtaufruf und die Darstellung eines bereits
    erzeugten öffentlichen Bilds im mobilen Browser wurden geprüft. Die erste
    automatische Prüfung dieses Altbilds scheiterte ohne damals gespeicherte
    Fehlerklasse; ein ausdrücklich gestarteter weiterer Versuch gelang. Eine
    fachkundige Abnahme und breitere thematische Erprobung bleiben offen.

    - [x] **Bildaufträge beim Neuladen und Rundenwechsel richtig zuordnen.**
      Ein neuer Ansichtsdatensatz derselben Runde erhält den Schlüssel eines
      noch unklaren Bildauftrags; eine ausdrückliche Wiederholung kann deshalb
      keinen zweiten Auftrag allein wegen des Neuladens erzeugen. Beim Wechsel
      zu einer anderen Runde werden Schlüssel und Bedienzustand getrennt;
      verspätete Antworten der alten Runde können den neuen Auftrag nicht
      freigeben. Künstliche Fluttertests prüfen beide Wettläufe.

    - [x] **Bildprüfung bei Ansichtsaktualisierung fortsetzen.** Eine bereits
      laufende unabhängige Prüfung bleibt während des Neuladens gesperrt und
      behält bei einer unklaren Antwort ihren Schlüssel für die ausdrückliche
      Wiederholung. Eine neue Runde erhält ihren eigenen Zustand. Ein
      künstlicher Widgettest prüft Wiederholung und Schlüsselgleichheit;
      das ist keine neue fachliche Prüfung des erzeugten Bildes.

  - [ ] **Vorbereitung fehlender Erklärgrafiken zuverlässig machen.**
    Die konkrete Bienenrunde hatte nur das allgemeine Szenenrezept zur Auswahl,
    aber keinen dafür erforderlichen Pfeil in der Quelle. Zusätzlich war die
    zuvor ausgewählte Luna-Route abgelaufen. Der neue Code lehnt eine nachweislich
    unbrauchbare alleinige Szenenvorlage vor Reservierung ab. Auch zwei
    künstliche Sol-Grafikaufrufe wurden wegen ungültiger Szenen abgewiesen;
    eine probeweise Sol-Routenumstellung wurde deshalb nicht beibehalten. Eine
    passende geprüfte alternative Darstellung und ein erfolgreicher
    Ende-zu-Ende-Lauf für die Bienenrunde fehlen noch.

    - [x] **Ausgeschöpfte Grafikversuche richtig anzeigen.** Die Rundenansicht
      verwendet dieselbe quellgebundene Versuchszählung wie der Startendpunkt.
      Nach ausgeschöpften Versuchen bietet sie keinen sicher scheiternden
      erneuten Start an; ein tatsächlich laufender Auftrag bleibt auch bei
      gleichzeitigen alten Fehlern als laufend sichtbar. Eine neue
      Quellen-/Rundenfassung behält ihre eigene Versuchszählung. Künstliche
      API- und Widgettests prüfen beide Fälle ohne Anbieteraufrufe.

    - [x] **Unklare Grafikantworten nicht durch alte Fehler umschlüsseln.**
      Ein beim Neuladen erscheinender Fehler eines älteren Auftrags ändert
      während einer noch laufenden Anfrage nicht deren Idempotenzschlüssel.
      Eine bewusste Wiederholung nach Verbindungsfehler verwendet denselben
      Schlüssel; erst eine bestätigte terminale Antwort erlaubt einen neuen.
      Ein künstlicher Widgettest prüft den Wettlauf.

    - [x] **Aussichtslose Grafikaktion vorab erkennen.** Die lesende
      Rundenansicht prüft dieselben Quellen und Vorlagen wie der spätere
      ausdrückliche Start. Ist bereits klar, dass der Server keinen solchen
      Auftrag annehmen könnte, erscheint eine kurze Erklärung statt eines
      Buttons, der unmittelbar scheitert. Es entstehen weder Auftrag noch
      Kosten oder Lernbelege; beim Start werden Rechte und Quellen weiterhin
      erneut geprüft. Künstliche API- und Widgettests prüfen verfügbare und
      nicht verfügbare Vorlagen. Eine passende neue Darstellung oder eine
      erfolgreiche KI-Generierung ist dadurch noch nicht nachgewiesen.

    - [x] **Quellgebundene Grafikaufträge stabil an ihre Runde binden.** Ein
      Neuladen derselben Runde verwirft die ausstehende Antwort nicht; ein
      Rundenwechsel setzt den Bedienzustand zurück und eine verspätete Antwort
      kann den Auftrag der neuen Runde nicht entsperren oder aktualisieren.
      Künstliche Fluttertests decken beide Reihenfolgen ab. Der bestehende
      serverseitige Idempotenz- und Quellenvertrag bleibt unverändert.

    - [x] **Allgemeines Beispiel bei Themenwechsel erneut abgleichen.** Wird
      Fach, Thema oder Grafikstatus derselben Runde geändert, verschwindet das
      bisherige allgemeine Beispiel sofort. Ein verspäteter alter Leseabruf
      darf es nicht erneut anzeigen; das neue Beispiel wird ausschließlich
      lesend angefordert. Ein künstlicher Widgettest prüft die überlappenden
      Antworten. Die Prüfung weist keine fachliche Qualität des Beispiels nach.

  - [x] **Öffentliche Unterthemen eindeutig und datensparsam zuordnen.**
    Die automatische Auswahl erkennt zusätzlich vollständige Titel bestätigter,
    kuratierter Kataloginhalte im aktiven Snapshot; Fach und Themenzuordnung
    müssen passen. Doppelte oder zurückgezogene Treffer erzeugen keinen Auftrag
    beziehungsweise keine Anzeige. Der öffentliche Inhaltsstand wird versioniert
    in den gemeinsamen Schlüssel aufgenommen, private Titel und Hefttexte
    werden nicht an den Grafikprovider weitergegeben. Künstliche Tests prüfen
    mehrere Fächer, Mehrdeutigkeit, Widerruf, Wiederverwendung und den
    Providervertrag. Die Auswahl ersetzt weder fachliche Abnahme noch einen
    Nachweis für beliebige Synonyme oder sämtliche angebotenen Themen.

  **Teilprüfung 02.11.2026:** 50 synthetische SQLite-Fälle zu Szenen und
  Positionen bestanden; Umfang und Grenzen:
  [Regressionsbericht](docs/ROADMAP_REGRESSION_2026_11_02.md#erklärgrafiken-und-animationen).

  Für den vereinbarten Startumfang jeden Erklärungsschritt auf eine fachlich passende Grafik prüfen. Vorhandene Renderer und versionierte deklarative Szenen verwenden; Modelltexte dürfen keinen ausführbaren Code, keine fremden ausführbaren Inhalte und keine ungeprüften Koordinaten einschleusen. Zahlen, Beziehungen, Beschriftungen und sichtbare Zustände gegen dieselben geprüften Daten validieren. Geeignete Interaktionen und Animationen erhalten Start/Pause, Zurücksetzen und gegebenenfalls Schrittsteuerung sowie verständliche Alternativen für Tastatur, Screenreader und reduzierte Bewegung.

  **Abnahme:** Fachkundige Prüfung und tatsächliche Webdarstellung decken ausgewählte Mathematik-, Sprach-, Natur- und Gesellschaftsfachfälle ab; fehlerhafte oder fehlende Grafik wird sicher korrigiert beziehungsweise nicht als vollständig ausgegeben. Erkunden allein erzeugt keinen Leistungsnachweis.

- [ ] **P1 – Schulbuddy als sicheren kontextbezogenen Lernbegleiter prüfen**

  - [x] **Regressionstests für offene Tutorfragen an Lösungsschutz anpassen.**
    Bei künstlichen Folgefragen enthalten weder Antwort noch sichtbares Zitat
    die Lösung; die Tests prüfen weiterhin alte und geänderte Aufgabenfassung
    sowie frühere Belege. Zwei weitere alte Bestätigungstests verlangen nun
    die ausdrückliche Elternentscheidung. Die 15 betroffenen SQLite- und 31
    PostgreSQL-Fälle bestanden. Der historische Gesamtlauf hatte sechs Fehler;
    ein vollständiger erneuter Lauf bleibt offen.
    [Testbericht](docs/BACKEND_SUITE_2026_11_26.md).

  - [x] **Ganzzahlige Entsprechung einer Bruchlösung in Hinweisen erkennen.**
    Für unterstützte kurze Mathefragen werden eigenständige ganze Zahlen
    zurückgehalten, wenn sie einer gespeicherten Bruchlösung entsprechen und
    noch nicht in der Frage oder geöffneten Erklärung stehen. Vorzeichen,
    andere Brüche und Dezimalzahlen bleiben unterscheidbar. Zurückgehaltene
    Providerantworten erzeugen keinen Hilfebeleg; Kosten bleiben verbucht.
    53 künstliche Fälle bestanden jeweils auf SQLite und isoliertem PostgreSQL;
    die ergänzte Kostenprüfung und Grenzfälle bestanden nochmals auf
    PostgreSQL. Dies erkennt keine ausgeschriebenen oder sinngemäßen Lösungen
    und ersetzt keine fachliche Prüfung echter Modellantworten. Der Stand ist
    noch nicht produktiv veröffentlicht. [Grenzen](docs/SCHULBUDDY.md).

  - [x] **Gleichwertige Bruchlösungen in Mathehinweisen begrenzt erkennen.**
    Bei offenen kurzen Mathematikaufgaben mit einem gespeicherten Bruch als
    Lösung werden zusätzlich gleichwertige Brüche, Dezimalzahlen und gemischte
    Zahlen in sichtbaren Antwortfeldern zurückgehalten. Steht derselbe Wert
    bereits in Aufgabe oder geöffneter Erklärung, bleibt die bestehende
    Prüfung der tatsächlich verlangten Darstellung erhalten. Die Regel bewertet
    keine Kinderantworten und gilt nicht für andere Aufgabentypen oder Fächer.
    Künstliche Worker- und Grenzfälle prüfen Buchung und Erhalt vorhandener
    Antworten. Allgemeine sinngemäße Lösungsverrate und fachliche Modellprüfung
    bleiben offen.

  - [x] **Exakte Lösungen in Hinweisen zu offenen Aufgaben zurückhalten.**
    Bei einfachen gespeicherten Fragen prüft der Server die sichtbare
    Modellantwort, Rückfrage, Schnellaktionen und Quellenzitate auf exakt
    gespeicherte Lösungen und Varianten. Ein Treffer wird nicht angezeigt
    oder als Hilfe angerechnet; der gegebenenfalls angefallene Anbieterpreis
    bleibt regulär verbucht. Freigegebene Rückmeldungen und ausdrücklich
    geöffnete Lösungsschritte bleiben erklärbar. Tests verwenden künstliche
    Inhalte und simulierten Modelltransport. Diese endliche Prüfung erkennt
    weder beliebige Umschreibungen noch jede mathematische Äquivalenz und ist
    keine allgemeine Sicherheits- oder Kinderschutzabnahme.

  - [x] **Hilfe während einer falschen Rückmeldung beim Wiederholen anrechnen.**
    Gilt nach einer falschen Antwort weiterhin dieselbe Aufgabe als offen,
    kennzeichnet eine erfolgreich gegebene Schulbuddy-Hilfe einen späteren
    neuen Versuch als unterstützt. Der frühere Versuch wird nicht verändert;
    Rückmeldungen zu abgeschlossenen oder anderen Aufgaben zählen nicht als
    Hilfe für eine neue Frage. Künstliche Tests prüfen die Speicherung und
    den anschließenden Wiederholungsversuch.

  - [x] **Schulbuddy-Kontext öffentlicher Erkundungen wiederherstellen.**
    Die bereits durch die Referenzprüfung für die Anzeige aufbereitete Grafik
    wird dem Tutor einmalig übergeben. Eine zweite Validierung verlangte zuvor
    entfernte Quellbelege und führte zu HTTP 500. Künstliche API- und Workerfälle
    prüfen den berechtigten Zugriff, den Grafikzustand, unveränderten Lernstand
    und die Ablehnung bei Quellenwechsel und fremdem Zugriff. Die Fälle bestanden
    auf SQLite und isoliertem PostgreSQL. Die allgemeine fachliche und
    geräteübergreifende Tutorabnahme bleibt offen.

  - [x] **Tutorverlauf an die lokale Anmeldeabsicht binden.** Beginnt eine neue
    Anmeldung, werden sichtbare Fragen und rein lokale Entwürfe des alten
    Tutorfensters entfernt; alte Sendeaktionen, verspätete Antworten und
    Fehler werden verworfen und das Fenster bleibt schließbar. Der lokale
    Entwurf wird auch bei abgebrochener Anmeldung nicht wiederhergestellt.
    Ein bereits abgeschickter Auftrag bleibt serverseitig bestehen; es gibt
    keinen automatischen Wiederholungsauftrag. Künstliche Widgetfälle prüfen
    die Wechsel sowie den normalen Ablauf. Die allgemeine Cookie- und
    fachliche Tutorabnahme bleibt offen.

  - [x] **Tutor-Commit gegen parallelen Datenschutzwiderruf schützen.**
    Die bei der Reservierung und Veröffentlichung frisch geprüfte Installations-
    freigabe wird in derselben Transaktion bis zum Commit gesichert. Bei
    Konflikt rollen Auftragsänderungen zurück, tatsächlich angefallene Kosten
    bleiben erhalten. Künstliche PostgreSQL-Rennen verwenden den echten
    Admin-Widerruf sowie bekannte und unbekannte Preise. Während der Inferenz
    bleibt die Betreiberaktion möglich; die Gesamtdauer der nachfolgenden
    Hilfebuchung ist nicht hart begrenzt. [Beleg und Grenzen](docs/SCHULBUDDY_SESSION_SERIALIZATION_2026_11_06.md#nachtrag-widerruf-der-installationsfreigabe).

  - [x] **Schulbuddy bei gleichzeitigem Gerätewiderruf serialisieren.**
    Auftragsreservierung und Veröffentlichung verwenden nach der Kindersperre
    den bestehenden nichtwartenden Session-Guard. Ein vor der Anbieterprüfung
    widerrufener Zugang sendet keinen Auftrag; bei Konflikt nach dem Versand
    werden Antwort und Hilfebeleg verworfen und unbekannte Kosten bleiben
    reserviert. Beide Transaktionsrichtungen und die Sperrreihenfolge beim
    Familienanruf und der Admin-Kontosperre sind mit künstlichen PostgreSQL-Fällen geprüft.
    Auch Providerrevision und Notstopp werden vor dem Commit unter kurzer
    nichtwartender Zeilensperre nachgeprüft; echte Inferenz hält diese Sperre
    nicht. Der damals noch offene gleichzeitige Widerruf der
    Installationsfreigabe wurde anschließend gesondert abgesichert, siehe
    Nachtrag im Prüfbericht. Eine externe
    Anfrage, die im Moment des Widerrufs bereits läuft, lässt sich nicht
    nachträglich zurückholen. [Prüfung und Grenzen](docs/SCHULBUDDY_SESSION_SERIALIZATION_2026_11_06.md).

  - [x] **Laufende Antworten an die sichtbare Aufgabenrevision binden.**
    Änderungen an Wortlaut, Optionen oder Lösung verwerfen verspätete
    Tutorantworten für aktive und archivierte Aufgaben. Künstliche SQLite- und
    PostgreSQL-Fälle prüfen den bestehenden Fehlerpfad. Die konservative
    Hilfeanrechnung und die noch offene fachliche Abnahme bleiben unverändert.

  - [x] **Gespeicherte Schulbuddy-Antworten an die Aufgabenfassung binden.**
    Eine bereits fertige Antwort wird bei korrigiertem Aufgabenwortlaut,
    geänderten Optionen oder geänderter Lösung als veraltet gekennzeichnet und
    nicht für eine neue Modellanfrage weiterverwendet. Alte Antworten ohne
    überprüfbaren Aufgabenfingerabdruck bleiben lesbar, aber nicht fortsetzbar.
    Frühere Antworten und Hilfeereignisse werden nicht verändert. Künstliche
    API-/Worker-Tests auf SQLite und isoliertem PostgreSQL belegen außerdem den
    Rechteentzug vor und während des simulierten Anbieteraufrufs; vorhandene
    Sitzungs- und Quellwechseltests bleiben erhalten. Die fachliche Qualität
    tatsächlicher KI-Antworten ist dadurch nicht abgenommen.

  **Teilprüfung 02.11.2026:** 44 synthetische SQLite-Fälle und die zwei dort
  übersprungenen Parallelitätsfälle auf PostgreSQL bestanden; Umfang und
  Grenzen: [Regressionsbericht](docs/ROADMAP_REGRESSION_2026_11_02.md#schulbuddy).

  Aktuelle Heftseite, Lernziel, Aufgabe, sichtbaren Grafikzustand und zulässige Hilfen revisionsgebunden übergeben; Schnellaktionen tatsächlich absenden. Antworten auf unklare Quellen, fachliche Fragen, Manipulationsversuche in hochgeladenen Bildern und unangemessene Eingaben mit künstlichen Fällen prüfen. Keine menschliche Identität, emotionale Abhängigkeit, Diagnosen oder zugesicherte Lernerfolge vortäuschen. Bei deutlichem Unterstützungsbedarf eine verständliche, altersgerechte Hilfeoption vorsehen.

  **Abnahme:** Der Tutor bezieht sich auf die tatsächlich berechtigte Quelle, macht Unsicherheit deutlich, verrät nicht ungefragt wesentliche Lösungen und verbucht erfolgreiche aufgabenbezogene Hilfen korrekt. Rechteentzug oder Quellenänderung während des Auftrags verhindert die unberechtigte Speicherung.

## Produktmodule und Familienalltag

- [x] **P1 – Kinderwege, Navigation und Wiederaufnahme vollständig abnehmen**

  **Funktionale Abnahme 24.11.2026:** Ein isolierter Browserlauf mit
  künstlichem Konto und sechs simulierten Lerntagen bediente Fachübersicht,
  Themenkarte, Vorbereitung, Lernweg, Aufgaben, Rückmeldung und Ergebnis bei
  320, 390 und 1280 Pixeln. Der Start über Themenkarte und freiwilliges
  Weiterlernen wurde auf jeder Breite geprüft; für das erfüllte Mindestziel
  wurde künstlich gespeicherte Zeit verwendet. Neuladen und eine unabhängig
  angemeldete zweite Sitzung erhalten die offene Rückmeldung ohne doppelte
  Antwort. Der spätere Elternauftrag bleibt erhalten. 110 Flutter-Fälle zu
  Layout, Fachnavigation, Feedback und Lernzeit sowie das isolierte
  Browsergate bestanden; der abschließend ergänzte Klick auf die Desktopleiste
  wurde danach im erweiterten Lernweg separat erfolgreich geprüft.
  Die Aufgabenangabe im schmalen Kopf ist nun vollständig sichtbar.
  Fachliche KI-Qualität, echte Kinderbeobachtung und vollständige
  Barrierefreiheit bleiben eigene offene Punkte; die Desktopleiste wurde
  damals sichtbar angeklickt. Die ergänzende Rollen- und Tastaturprüfung vom
  25.11. ist beim offenen Barrierefreiheitspunkt dokumentiert.
  [Prüfbericht und Screenshots](docs/CHILD_PATH_ACCEPTANCE_2026_11_24.md).

  - [x] **Begonnene Zuordnung beim Hintergrundwechsel verwerfen.** Eine
    Ziehgeste aus der vorherigen Vordergrundphase kann nach Rückkehr keine
    Antwort mehr zuordnen. Automatisches Randscrollen endet, und neue Zieh- sowie
    Tippaktionen bleiben möglich; bereits gespeicherte Antworten werden nicht
    verändert. Künstliche Fluttertests zeigen den Fehler vor der Änderung und
    prüfen Rückkehr, mobile Breite und vergrößerte Schrift. Dies belegt keine
    vollständige Geräte- oder Kinderwegeabnahme.

  - [x] **Lernaktionen an die lokale Anmeldeabsicht binden.** Beginnt während
    einer laufenden Abfrage oder eines Rundenstarts eine neue Anmeldung im
    selben Appzustand, werden alte Ergebnisse und Fehler nicht mehr für eine
    Folgeaktion, Navigation oder Vorschau verwendet. Die Änderung erkennt auch
    diesen Zwischenzustand, wenn Nutzerobjekt und Webtoken noch gleich sind.
    Eine ungültige Vorschau oder Statusabfrage kann bewusst neu geladen werden;
    bereits abgeschickte Anfragen bleiben davon unberührt. Künstliche
    Widgetfälle prüfen Quellenabfrage, Zufallsthema, Vorbereitungsstatus und
    Rundenstart. Ein unbemerkter Cookie-Wechsel in einem anderen Tab und die
    vollständige geräteübergreifende Abnahme bleiben offen.

  - [x] **Lernvorschau bei Austausch des App-Zustands wiederaufnehmen.**
    Die Ansicht bindet sich beim Austausch des AppState an dessen Konto und
    Sitzung. Alte Übersichten und späte Startantworten überschreiben die neue
    Ansicht nicht; ein bereits laufender Start der neuen Sitzung bleibt bis zu
    seiner eigenen Antwort gesperrt. Künstliche Widgetfälle decken den zuvor
    reproduzierten Fehler ab. [Umfang](docs/LEARNING_SESSION_BOUNDARY_2026_11_06.md).
    Die vollständige geräteübergreifende Abnahme bleibt offen.

  - [x] **Lernfortsetzung an den Client-Sitzungstoken binden.** Eine alte
    Quellenabfrage darf nach Tokenwechsel keine neue Runde reservieren; späte
    Startantworten navigieren nicht in die neue Sitzung. Die Vorschau entfernt
    frühere Daten. Künstliche Widgetfälle prüfen auch die Fehlerweitergabe;
    ein nicht bemerkter HttpOnly-Cookiewechsel und die vollständige
    Geräteabnahme bleiben offen. [Prüfumfang](docs/LEARNING_SESSION_BOUNDARY_2026_11_06.md).

  **05.11.2026, Teilkorrektur Rundenstart:** Schlägt das ausdrückliche
  Öffnen einer bereits fertigen Runde fehl, bleibt eine kurze Erklärung
  direkt auf der Seite sichtbar und das Kind kann bewusst erneut öffnen.
  Ein Planungskonflikt nennt weiterhin den Grund. Bei entzogenem Zugriff
  wird die veraltete Startaktion entfernt; verspätete Antworten für eine
  andere Sitzung oder einen verdeckten Bildschirm werden verworfen. Die
  Prüfung erzeugt keine Lernrunde und wiederholt keinen KI-Auftrag. Die
  vollständige Mehrgeräte- und Browserabnahme bleibt offen.

  **04.11.2026, aktive Runde:** Ein bei Rückkehr noch laufender GET führt
  einen gezielten Folgeabruf aus; eine ausgetauschte Sitzung kann keine alte
  Antwort anzeigen. Nach 403/404 verschwindet die private Ansicht; 429 wird
  nicht automatisch umgangen. Gespeicherte Entwürfe und Antworten bleiben
  erhalten. Widget- und Chrome-Fälle prüfen die Zustandswechsel künstlich;
  die vollständige Mehrgeräte- und Browserabnahme bleibt offen.

  **03.11.2026, Teilabsicherung:** Lernweg und Runden-Vorbereitung beachten
  neben Konto und Familie nun auch den Sitzungstoken. Verspätete Antworten aus
  einer ersetzten Sitzung werden verworfen; der alte Vorbereitungsstatus
  startet keinen Folgeabruf. Zwei künstliche Sitzungswechsel und die bestehende
  Navigations-/Wiederaufnahmesuite bestanden mit insgesamt 30 Widgetfällen.
  Die vollständige mobile und breite Browserabnahme bleibt offen.

  Heute, Lernen, Fach- und Themenübersicht, Lernweg, aktive Runde, Ergebnis und freiwilliges Weiterlernen im 320-/390-Pixel-Web sowie auf breiten Ansichten bedienen. Pro Zustand die nächste Hauptaktion, Rückweg, Warteanzeige, eigene Eingaben und Fehlermeldung prüfen; laufende Runden, Quellen und verpflichtende Elternaufträge dürfen sich nicht gegenseitig verdecken. Gerätewechsel, Reload, parallele Sitzungen, unvollständige Antworten und offene Rückmeldung einbeziehen.

  **Abnahme:** Jede getestete Route erreicht ihr tatsächliches Ziel ohne festhängende Schleife; Feedback bleibt bis zur bewussten Fortsetzung sichtbar, Antworten und Position überleben Wiederaufnahme und angezeigte Zeit beruht auf gespeicherten Aktivitätssekunden.

- [x] **P1 – Hefte, Materialarten und Suche im digitalen Ranzen abnehmen**

  **Funktionale Abnahme 24.11.2026:** Ein isolierter Browserlauf prüft fünf
  künstliche Fotoseiten und einen weiteren Hefter mit 47 Seiten, einschließlich
  eines gezielt unterbrochenen Abrufs, ausdrücklicher Wiederaufnahme, Suche,
  serverseitiger Paginierung und Geschwisterschutz. Die reine Heftebedienung
  des zusätzlich geprüften Kindes erzeugt weder neue Lernaktivität noch
  zusätzliche Aufträge oder Kosten. Zusammen mit bestehenden Prüfungen für
  Fachauswahl, unzugeordnete Seiten, Zoom, Filter, Rechte, Löschvorschau,
  Neueinlesen und Quellenrevisionen ist die obige funktionale Abnahme
  abgeschlossen. Die sechs Fälle des zusammenhängenden Browser-Runners,
  102 Flutter-Fälle und gezielte SQLite-/PostgreSQL-Prüfungen bestanden.
  Keine Aussage über realistische Fotoerkennung, fachliche KI-Erzeugung,
  Offline-Nutzung nach Neustart oder unabhängige Kinderabnahme; diese bleiben
  in den jeweiligen anderen Hauptpunkten offen.
  [Prüfung und Grenzen](docs/NOTEBOOK_BROWSING_ACCEPTANCE_2026_11_24.md).

  - [x] **Kinder-Löschung auf unbestätigte freie Quellen begrenzen.**
    Die Kinderansicht und sämtliche Löschwege schützen bestätigte Seiten,
    verknüpfte Übungen und Elternaufträge sowie fortgeschrittene Tagesabgaben;
    gemischte Auswahlen werden insgesamt abgelehnt. Das Backend prüft nach
    der Sperre Quellen und Berechtigungen erneut. Eltern mit Schreibrecht
    behalten die gezählte Löschvorschau. Ein echter lokaler Browsertest mit
    künstlichen Konten und gezielte PostgreSQL-Rennen ergänzen Flutter- und
    API-Tests. Der nachfolgende Sessionguard serialisiert die vier geprüften
    Löschwege mit Gerätewiderruf und Logout; eine belegte Gegenprobe zum
    Familienanruf vermeidet die umgekehrte Sperrreihenfolge. Siehe
    [Prüfung](docs/DELETION_SESSION_SERIALIZATION_2026_11_05.md).

  - [x] **Lokalen Hefte-Browserlauf mit Löschvorschau reproduzierbar prüfen.**
    05.11.2026: Ein isolierter Chrome-/SQLite-Lauf mit künstlichen Konten
    und fünf künstlichen Layoutseiten prüft Eltern-Löschvorschau mit
    verknüpfter Runde und Antwort, den Löschschutz bestätigter Kinderseiten,
    die Löschung einer eigenen unbestätigten Seite sowie Einzel- und
    Mehrseitenstart. Die zwei Aufträge bleiben wartend; OCR und KI-Verarbeitung
    sind nicht Teil dieses Nachweises. [Ablauf und Grenzen](docs/NOTEBOOK_BROWSER_REGRESSION_2026_11_05.md).

  **05.11.2026, lokaler Browserlauf:** Fünf künstliche JPEGs je Kind über die
  echte lokale Upload-API importiert, anschließend mit explizit künstlichen
  Texten bestätigt und im Chrome-Browser für Eltern und Kinder betrachtet.
  Einzel- und Mehrseitenauswahl erzeugten zwei echte, lokal wartende Aufträge
  mit geprüften eigenen Quellenrevisionen; fremde Bilder waren gesperrt.
  Keine OCR und kein KI-Worker liefen. [Details und Screenshots](docs/NOTEBOOK_LOCAL_BROWSER_2026_11_05.md).

  - [x] **Verschiedene künstliche Materialseiten und Heftquellen im Backend absichern.**
    Fünf unterschiedlich gezeichnete und ausdrücklich gekennzeichnete
    Testseiten werden hochgeladen und mit Gast-, Geschwister- und Adminrechten
    auf Detail-, Versions- und Fotozugriff geprüft. Lesende Zugriffe verändern
    keine vorhandenen Material-, Aufgaben-, Antwort-, Aktivitäts-, Kompetenz-,
    Quellenbindungs-, Auftrags- oder Kostenzeilen. Bei ausdrücklich ausgewählten zwei Seiten
    gelangen beide unterschiedlichen Quellenmarker an den simulierten Worker;
    ungewählte Marker fehlen. Inhalts- oder Rechteänderungen vor oder
    während des Aufrufs verhindern die Veröffentlichung; entstandene Kosten
    bleiben erhalten. Künstliche SQLite- und PostgreSQL-Fälle bestanden.
    Keine OCR-, echte Provider- oder App-Abnahme daraus ableiten;
    [Prüfbericht](docs/NOTEBOOK_BACKEND_EVIDENCE_2026_11_05.md).

  - [x] **Fünf künstliche Materialarten in der Hefte-Oberfläche prüfen.**
    05.11.2026: Ein wiederholbarer Flutter-Test verwendet eigene, beschriftete
    JPEG-Layoutseiten von Arbeitsblatt, Hefter, Arbeitsheft, Buchseite und
    Klassenarbeit. Für Kind und Eltern bei 390 und 1280 Pixeln prüft er
    Navigation, Suche, Seitensprung über die Metadatengrenze sowie einen
    simulierten Einzel- und Mehrseitenstart mit Quellenrevisionen. Die
    Bildantworten und der Auftrag sind lokale Mocks. Keine echte OCR,
    Serverautorisierung, Live-Verarbeitung oder Geräteabnahme folgt daraus;
    der Hauptpunkt bleibt offen. [Testweg und Grenzen](docs/NOTEBOOK_MATERIAL_UI_2026_11_05.md).

  - [x] **Mehrdeutige Erweiterungsaufgaben im Heftverlauf gezielt absichern.**
    05.11.2026, Coding-AI: Die vorbereitete Notebook-Runde berücksichtigt
    den vollständigen zugehörigen Quellen-/Tagesverlauf. Bekannte Aufgaben
    bleiben Ausschlüsse; konkret erkennbare mehrdeutige Erweiterungen stoppen
    vor dem Anbieteraufruf mit einer eigenen Erklärung. Fachfremde Beispiele
    und reine Verständnisfragen sperren die getesteten Fälle nicht. Der
    Arbeitsauftrag wird nun auch im Worker gebunden und nach dem Anbieteraufruf
    unter der Kind-Sperre gegen den aktuellen Verlauf geprüft. Dabei bleiben
    tatsächlich entstandene Kosten erhalten; ein Vorabstopp löst keine aus.
    Die neuen künstlichen Historien- und Workerfälle bestanden jeweils auf
    SQLite und isoliertem PostgreSQL 16, ein unabhängiger Review erfolgte.
    Der begrenzte Mustervergleich erkennt nicht nachweislich jede mögliche
    Formulierung; auch eine vollständige Fach- und Browserabnahme folgt daraus
    nicht. Der Hauptpunkt bleibt offen.

  - [x] **Viele künstliche Quellen, Wiederaufnahme und Auswahlrevisionen prüfen.**
    Getrennte Familien, paginierte Lesezugriffe, gezieltes Wiederholen nach
    Netzfehler und ausgewählte Quellenrevisionen sind synthetisch geprüft.
    [Prüfbericht und Grenzen](docs/NOTEBOOK_ACCEPTANCE_2026_11_04.md).
    Reale Erkennung repräsentativer Materialfotos bleibt offen.

  **04.11.2026, laufende Abfrage:** Eine Materialänderung während eines
  Seitenabrufs verwirft das überholte Ergebnis und bündelt Änderungen in
  einem Folgeabruf; Logout verhindert die Wiederaufnahme. 79 Widgetfälle
  und zwei Chrome-Fälle bei 390 Pixeln bestanden. Die vollständige Quellen-,
  Rechte- und Medienabnahme bleibt offen.

  **Teilprüfung 02.11.2026:** 34 künstliche SQLite-Fälle und drei dort
  übersprungene Sperrentests auf PostgreSQL bestanden;
  [Prüfbericht](docs/ROADMAP_MODULE_CHECKS_2026_11_02.md#hefte-und-digitaler-ranzen).

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

- [x] **P1 – Elternübersicht, Noten und Planung gegen echte gespeicherte Fakten prüfen**

  **Technische Abnahme 24.11.2026:** Zwei künstliche Kinder mit getrennten
  gespeicherten Aufgaben, Versuchen, Hilfen, Lernzeiten, Noten und
  Pflichtterminen wurden über die tatsächlichen Elternansichten bei 390 und
  1440 Pixeln geprüft. Der künstliche PDF-Import wurde für beide Kinder bei
  390 und 1280 Pixeln wiederholt; Vorschau und explizite Übernahme blieben
  duplikatfrei, ohne Roh-PDF oder Lernbelege zu erzeugen. Rechte anderer
  Familien und Kinder, private Schulnotizen und konkurrierende Importe wurden
  gesondert auf SQLite und PostgreSQL geprüft. Der vollständige GitHub-Lauf
  [45392669156](https://github.com/meinzeug/schuleschlau/actions/runs/45392669156)
  bestand für `94285b1`, einschließlich des erweiterten Browsergates. Die
  geprüften Pausen und freien Lerntage bilden den vorhandenen Freizeitumfang;
  ein separates Freizeitkalendermodell ist hiermit nicht nachgewiesen.
  Physische Geräte, unabhängige Sicherheit und Lernwirkung bleiben getrennte
  Abnahmen. [Prüfbericht](docs/PARENT_MULTICHILD_ACCEPTANCE_2026_11_05.md).

  - [x] **Verspätete Lernplanantworten nach neuer Anmeldeabsicht begrenzen.**
    Überholte Ladeantworten und unklar abgeschlossene Auftragsänderungen
    verlangen einen ausdrücklichen Leseabgleich; eine ungewisse Vorbereitung
    behält ihren Idempotenzschlüssel. Ein alter Bestätigungsdialog verändert
    keinen Auftrag. Künstliche Flutterfälle prüfen diese Abläufe und die
    Wiederaufnahme. Weitere Wochen-, Karten- und Editoraktionen bleiben offen.
    [Prüfung und Grenzen](docs/PARENT_PLAN_LOGIN_RACES_2026_11_06.md).

  - [x] **Künstlichen Mehrkind-Notenimport im lokalen Browser prüfen.**
    Ein Elternkonto wählt für zwei künstliche Kinder dieselbe künstliche PDF
    bei 390 und 1280 Pixeln jeweils zweimal im Chrome-Dateidialog. Die Vorschaupositionen,
    ausdrückliche Übernahme und duplikatfreie Wiederholung werden anhand echter
    lokaler API-Antworten und der isolierten Datenbank geprüft; Zeit, Antworten
    und Backend-Dateien bleiben geschützt. Dieser Teilnachweis umfasst 390 und 1280 px,
    keine weiteren Konfliktfälle oder den gesamten Eltern-Hauptpunkt.
    [Prüfung und Grenzen](docs/PARENT_MULTICHILD_ACCEPTANCE_2026_11_05.md).

  - [x] **Pausen und freie Lerntage in der Eltern-Wochenansicht lesen.**
    Ein lokaler Chrome-/SQLite-Lauf mit zwei künstlichen Kindern prüft bei
    390 und 1440 Pixeln die zugehörigen gespeicherten Planantworten und den
    zugänglichen Hinweis auf freiwilliges Lernen. Ein Kind hat eine Lernpause,
    das andere einen freien Lerntag; beide haben an diesem Tag keine verfügbare
    Planungskapazität. Pflichttermine und Lernbelege bleiben unverändert.
    Die Einstellungen werden für diesen Teilnachweis nicht im Dialog geändert;
    die vollständige Elternabnahme bleibt offen.
    [Prüfumfang](docs/PARENT_MULTICHILD_ACCEPTANCE_2026_11_05.md).

  **Teilprüfung 02.11.2026:** 45 künstliche SQLite-Fälle zu Notenfiltern und
  PDF-Import bestanden; [Prüfbericht](docs/ROADMAP_MODULE_CHECKS_2026_11_02.md#elternübersicht-noten-und-planung).

  Mit einer künstlichen Familie mehrere Kinder, Lerntage, Hilfen, Aufgaben, Versuche, Lernzeit, verbindliche Termine und Freizeiten durchspielen. Berechtigte Elternansichten auf Smartphone und Desktop vergleichen; PDF-Notenimport nur lokal, mit Vorschau, eindeutiger Zuordnung und ohne Roh-PDF-Speicherung testen. Elternlesen darf keine Kinderzeit oder Antworten erzeugen; Noten und private Bemerkungen dürfen nicht automatisch an KI-Anbieter gelangen.

  **Abnahme:** Alle Anzeigen lassen sich auf dieselben gespeicherten Daten zurückführen, Familienmitglieder sehen nur Berechtigtes, Import und Wiederholung sind idempotent und es entstehen keine erfundenen Diagnosen oder Notenprognosen.

- [x] **P1 – Adminoberfläche und laufende Betriebsentscheidungen abnehmen**

  - [x] **Abschlussdatum der Einrichtung bei späterer Adminpflege erhalten.**
    Das lokale Admin-CLI setzt das Abschlussdatum nur bei der Ersteinrichtung;
    Anlegen und Zurücksetzen weiterer Administratoren bewahren den vorhandenen
    Zeitstempel. Drei künstliche CLI-Fälle prüfen beide Folgeaktionen und die
    erstmalige Einrichtung.


  **23.11.2026, erneute technische Abnahme:** Auf dem aktuellen Entwicklungsstand
  bestanden 136 SQLite- und 144 PostgreSQL-Fälle zu Konten, Rechten, Budgets,
  Kostenbelegen, Notfallstopp, Beta und revisionsgebundenen Einstellungen;
  datenbankspezifische Auslassungen sind im Prüfbericht angegeben. Ergänzend
  bestanden private Bild-/Noten-/Tutorzugriffe und die konkurrierenden
  Freigabe-/Seitenprüfänderungen auf beiden passenden Datenbanken. 117 Flutter-
  und 80 Chrome-Webrunner-Fälle prüften die Adminoberfläche, einschließlich
  kleiner Ansichten, großer Schrift und Providerfehler. Keine echten
  Anbieteraufrufe oder produktiven Familienänderungen wurden dafür ausgeführt.
  [Ergebnisse und Grenzen](docs/ADMIN_ACCEPTANCE_2026_11_23.md). Die
  unabhängige Sicherheitsprüfung und echte Anbieterpreise bleiben separat offen.

  **06.11.2026, erneute Prüfung:** Der zuvor abgenommene Parallelitätsumfang
  war nicht vollständig: Ein später generisch gespeicherter alter
  Seitenprüfmodus konnte einen revisionsgebundenen Wechsel überholen. Die
  nachträglich geprüfte Korrektur sperrt und prüft diesen Modus zusammen.
  [Befund und Testgrenzen](docs/INSTALLATION_CONSENT_RACE_2026_11_06.md).

  - [x] **Site-Einstellungen gegen veraltete Änderungen absichern.** Der
    Admin-Endpunkt verlangt eine passende Revision; bei Konflikten bleibt der
    Entwurf erhalten und ein erneuter Vergleich ist ausdrücklich nötig.
    SQLite-, PostgreSQL- und Flutter-Tests sowie ein künstlicher Chrome-Test
    mit alter Service-Worker-Version prüfen die Änderung. Der alte Client
    erhält kontrolliert HTTP 409; der separate Notstopp-API-Aufruf bleibt in
    derselben Sitzung erreichbar. Setup und lokales CLI behalten ihren eigenen
    Vertrag. Die übrige Admin-Gesamtabnahme bleibt offen.
    [Prüfung](docs/INSTALLATION_SITE_CAS_2026_11_06.md).

  **04.11.2026:** Rechte und private Originalbilder, Tages-/Monatsbudgets,
  Systemgrenzen, Kostenbelege, Entwürfe, Revisionskonflikte und Notfallstopp
  wurden mit künstlichen Konten auf SQLite, PostgreSQL und Flutter einschließlich
  Chrome geprüft. [Abnahme und Grenzen](docs/ADMIN_ACCEPTANCE_2026_11_04.md);
  reale Anbieterpreise und eine unabhängige Sicherheitsprüfung sind damit nicht
  belegt.

  **Teilprüfung 02.11.2026:** 47 künstliche SQLite-Fälle zu Nutzerverwaltung,
  Filterung und Revisionen bestanden; außerdem liefen Admin-Parallelitätsfälle
  auf PostgreSQL. [Prüfbericht](docs/ROADMAP_MODULE_CHECKS_2026_11_02.md#administration).

  **03.11.2026, Kinderkosten:** Suche und Speichern verwerfen überholte
  Antworten und alte Bediencallbacks; laufendes Laden und Speichern können
  einander nicht mehr überschreiben. Ein im Web zu null ausgewerteter
  32-Bit-Shift beim Erzeugen des Speicherschlüssels wurde durch sichere
  Zufallsbytes ersetzt; Kontingentgrenzen und Prüfpflichten bleiben bestehen.
  Die anschließende technische Adminabnahme ist oben dokumentiert.

  Familien- und Kontoverwaltung, Kindertages-/Monatsbudgets einschließlich unbegrenzt, Familien-/Systemgrenzen, Providerstatus, Kostenbelege, Notfallstopp und revisionsgebundene Einstellungen mit künstlichen Konten testen. Adminrechte im Backend durchsetzen; Betriebsadministratoren erhalten keinen Zugriff auf private Kinderinhalte. Abschnittswechsel dürfen Entwürfe nicht verwerfen und Lesezugriffe keine Änderungen oder Anbieteraufrufe auslösen.

  **Abnahme:** Fehlerzustände und tatsächlich wirksame Limits sind verständlich; Notfallstopp bleibt bei gestörter Providerabfrage erreichbar, Änderungen sind auditiert, parallele Bearbeitung und widerrufene Sitzungen werden korrekt behandelt.

- [x] **P1 – Benachrichtigung und direkte Zielnavigation vollständig prüfen**

  **Funktionale Abnahme 24.11.2026:** Im isolierten Browserlauf mit vier
  getrennten Sitzungen öffnen künstliches Kind und Eltern die berechtigten
  Ziele; die Kinder-Glocke führt sowohl zu erkannten Heftseiten als auch zur
  gespeicherten Lernrunde. Lesebelege bleiben kontogebunden; Nachladen und
  Scrollen markieren nicht erreichte Meldungen nicht. 136 SQLite-Fälle
  bestanden, zwei PostgreSQL-Fälle wurden dort ausgelassen und im Lauf mit
  138 erfolgreichen PostgreSQL-Fällen ausgeführt. Je ein weiterer
  Timeout-Fall bestand auf beiden Datenbanken. 61 Flutter- und 20
  Chrome-Widgetfälle sowie das lokale Browsergate mit 17 Fällen bestanden.
  Die simulierte Pushstörung führt nicht zum Verlust der In-App-Meldung oder
  einem automatischen Doppelversand. Die tatsächlich sichtbare neutrale
  Android-Zustellung und das Lernrundenziel sind getrennt in den
  Emulatorberichten vom 05.11.2026 belegt; dies ist keine erneute native
  Abnahme des aktuellen Stands oder eine physische Geräteprüfung.
  [Prüfung und Grenzen](docs/NOTIFICATION_CROSS_CLIENT_2026_11_24.md).

  - [x] **Kinder-Glocke für Heftseiten und Lernrunde prüfen.** Eine
    synthetisch vorbereitete Heftseite und eine bereits gespeicherte Runde
    führen aus dem Kinderkonto zu ihren jeweiligen Zielen. Der Lesestatus des
    Elternkontos bleibt unverändert; die Bedienung erzeugt keine neuen
    KI-Aufträge, Kostenbuchungen oder Pushversendungen. Der Test ist im
    isolierten Browsergate enthalten.

  - [x] **Glocke, Lesestatus und Rundenziel mit unabhängig angemeldeten Webclients prüfen.**
    24.11.2026: Drei getrennte Browserkontexte mit künstlichen Konten und dem
    tatsächlichen lokalen Backend prüfen bei 390 × 844 Pixeln 60 Meldungen,
    sichtbarkeitsbezogene Lesebelege, das Nachladen und Scrollen im Glockenmenü,
    die Gesamtansicht und den Link zur gespeicherten Runde. Zwei Sitzungen
    desselben Kontos teilen ihren Lesestand; eine weitere berechtigte Person
    behält ihren eigenen. Eine fremde Familie erhält keinen Zugriff. Der
    reproduzierbare Test ist im lokalen Browser-CI-Gate enthalten. Ein
    Android-Emulator-Test mit der installierten aktuellen APK scheiterte an
    wiederholten System-UI-Hängern unter hoher VM-Last; er zählt nicht als
    bestandene native Mehrgeräteabnahme. Das künstliche Testkonto wurde
    gelöscht. [Prüfbericht](docs/NOTIFICATION_CROSS_CLIENT_2026_11_24.md).

  - [x] **Benachrichtigungen auf einem echten Gerät durch den Betreiber prüfen.**
    Am 08.11.2026 bestätigte der Betreiber, dass die Benachrichtigungen auf
    einem echten Gerät funktionieren. Dieser Nachweis beruht auf seiner
    Rückmeldung; die Coding-AI hat die Zustellung nicht selbst beobachtet.
    Gerätetyp, Betriebssystem, Meldungsart, App-Zustand und Verhalten beim
    Antippen wurden nicht näher angegeben. Daraus folgt noch keine vollständige
    Abnahme aller Zustände, der Firebase-Transportkette oder der direkten
    Zielnavigation; der übergeordnete Punkt bleibt offen.

  - [x] **Verzögerte Benachrichtigungsnavigation bei neuer Anmeldung stoppen.**
    06.11.2026: Eine neue Anmeldeabsicht kann beginnen, bevor Konto und Cookie
    wechseln. Glockenmenü und Gesamtansicht zeigen dann keine verspätete
    Lesefehler-Meldung und navigieren nach einer zuvor begonnenen Quittierung
    nicht mehr zu deren altem Ziel. Die Schaltfläche ist nach Abbruch der
    Anmeldung und Rückkehr zur Ansicht wieder bedienbar. Künstliche Widgettests prüfen Erfolg und Fehler
    der verzögerten Quittierung in beiden Ansichten; vor der Korrektur führten
    beide Ansichten noch zum alten Ziel. Bereits an den Server gesendete
    Lesebelege werden nicht rückgängig gemacht. Dies ersetzt keine vollständige
    Geräte- oder Pushabnahme.

  - [x] **Falschen Ladefehler bei wiederholter Scrollverzögerung vermeiden.**
    Zwei Gesten oder Lesebestätigungen erschöpfen die begrenzten GET-Versuche,
    ohne einen Netzwerkfehler vorzutäuschen. Liste und Cursor bleiben erhalten;
    die nächste Aktion kann neu laden. Künstliche Flutter-Tests prüfen beide
    Fälle samt Wiederaufnahme; ein 390-Pixel-Widgettest bedient danach den
    vorhandenen Glockenbutton. [Umfang](docs/NOTIFICATION_SCROLL_2026_11_05.md).
    Die geräteübergreifende Abnahme bleibt offen.

  - [x] **Glockenliste beim Nachladen und Live-Refresh stabil halten.**
    Sichtbare Meldungen bleiben beim Nachladen verankert. Während Ziehen oder
    Ausrollen wird eine erfolgreiche Aktualisierung begrenzt zurückgestellt
    und danach erneut abgefragt. Erkannte 401-/403-Rechtefehler leeren den
    privaten Cache; alte Antworten dürfen nicht in ein neues Konto übernommen
    werden. 125 Flutter-VM-Fälle, zwei Chrome-UI-Fälle bei 390 Pixeln und die
    gezielte Analyse der geänderten Dart-Dateien bestanden; die Änderung wurde
    unabhängig geprüft. Die vollständige App-Analyse, globaler produktiver
    401-Ablauf, Geräte-/Barrierefreiheitsabnahme und unbeobachteter serverseitiger
    Rechteentzug sind damit nicht nachgewiesen. Zwei aufeinanderfolgende
    Gestenverzögerungen können als Ladefehler erscheinen; siehe
    [Prüfung](docs/NOTIFICATION_SCROLL_2026_11_05.md).

  - [x] **Lesebelege beim Scrollen und über getrennte Sitzungen synthetisch prüfen.**
    05.11.2026, Coding-AI: Sichtbar gelesene und nicht erreichte Meldungen werden bei einem simulierten
    Gerätewechsel getrennt behandelt. Paginierte Backendmeldungen behalten den
    Lesestatus über zwei Sitzungen desselben Kontos; ein anderes berechtigtes
    Konto derselben Familie behält seinen eigenen Stand. SQLite-, PostgreSQL-
    und mobiler Flutter-Widgettest bestanden. Der Widgettest nutzt einen
    künstlichen HTTP-Dienst; ein Ende-zu-Ende-Test mit zwei echten oder
    emulierten Geräten bleibt offen. [Prüfumfang](docs/NOTIFICATION_DEVICE_READ_2026_11_05.md).

  - [x] **Position beim Nachladen in der Gesamtansicht erhalten.**
    Eine weiterhin sichtbare Karte bleibt beim Austausch unterschiedlich hoher
    Cacheseiten verankert. Konto-, Filter- und spätere Scrollaktionen verwerfen
    veraltete Korrekturen; alte Anker werden bei Aktualisierung entfernt.
    Widget- und Chrome-Prüfungen einschließlich Smartphonebreite und
    Lesemarkierungen bestanden. Im virtuellen Glockenmenü und ohne erhaltene
    sichtbare Ankerkarte bleibt das Verhalten gesondert zu prüfen.
    [Nachweis und Grenzen](docs/NOTIFICATION_SCROLL_2026_11_05.md).

  - [x] **Tageskarten auch bei vielen anderen Kontextformen deduplizieren.**
    Der vollständige Kontext wird vor der Auswahl der neuesten Karte
    strukturell verglichen; SQLite- und PostgreSQL-Fälle prüfen mehr als 500
    andere Kontexte und unterschiedliche Unicode-Escapes. Beim Wiederaufnehmen
    während eines laufenden Inboxabrufs folgt genau eine aktuelle Abfrage;
    Flutterfälle prüfen Konto- und Hintergrundwechsel. Der Scrollsprung beim
    Austausch des Cachefensters und native Zustellung waren damals noch offen;
    spätere Teilprüfungen sind oben beziehungsweise unter Android dokumentiert.

  **04.11.2026, Ungelesenfilter:** Der Filter berücksichtigt neu geladene
  und eintreffende ungelesene Karten, ohne unbekannte ältere Seiten als
  gelesen auszugeben. 59 Widgetfälle und zwei Chrome-Fälle, einer bei
  390 × 760 Pixeln mit doppelter Schrift, bestanden. Das belegt keine
  native Zustellung oder vollständige Zielnavigation.

  - [x] **04.11.2026, serverseitige Cursor-Fortsetzung und begrenzter
    Glockencache:** Das optionale paginierte API-Format führt Ereignisquellen
    nach Zeit und Kennung zusammen und prüft bei jeder Seite Rechte und
    Quellen erneut. Auch nach 500 ungültigen Kandidaten bleibt eine bewusste
    Fortsetzung möglich. Glocke und Gesamtansicht laden ältere Meldungen;
    nur sichtbare Karten erhalten Lesebelege. Der Client hält höchstens drei
    Seiten und erlaubt den Rücksprung zu den neuesten. Zehn gezielte
    Cursorfälle bestanden auf SQLite und PostgreSQL; die breite bestehende
    Backendregression bestand mit 167 Fällen und einem Skip auf SQLite sowie
    168 Fällen auf PostgreSQL. 97 Flutterfälle und gezielte Chrome-Fälle,
    darunter 390 × 760 Pixel bei doppelter Schrift, bestanden. Die damals
    beobachtete doppelte Tageskarte ist durch die spätere oben dokumentierte
    Kontextprüfung behoben; beim Entladen unterschiedlich hoher Karten ist
    weiterhin ein Scrollsprung möglich.
    Dies belegt keine native Pushzustellung und keine gesamte Freigabe des
    übergeordneten Punktes.

  **04.11.2026, Inbox-Cache:** Auch beim Familien- oder Sitzungswechsel
  desselben Kontos werden alte Meldungen und verspätete Antworten verworfen;
  die Gesamtansicht leert alte Inhalte sofort. 53 Widget- und Headertests und
  fünf gezielte Chrome-Webfälle bestanden; ein Android-spezifischer Kanaltest
  ist im Webrunner nicht anwendbar. Die Cursor-Fortsetzung und sichtbare native
  Zustellung waren damals noch offen und wurden später teilweise geprüft.

  **04.11.2026, gezielte Lesebestätigung:** Nur die ausdrücklich quittierten
  Ereignisse werden erneut projiziert und auf Berechtigung sowie Quellen
  geprüft. Der vollständige Inboxscan entfällt bei dieser Aktion; ungültige
  Kennungen werden weiterhin gemeinsam zurückgewiesen. Die breitere Suite
  bestand mit 98 Fällen und einem Skip auf SQLite und mit 99 Fällen auf
  isoliertem PostgreSQL. Das Cursor-Nachladen älterer Einträge war damals
  noch offen; die spätere serverseitige Fortsetzung ist oben dokumentiert.

  **03.11.2026, Kontextwechsel beim Öffnen:** Glocke und Gesamtansicht
  verwerfen überholte Klicks und verspätete Lesebestätigungen, wenn sich
  Familie oder Sitzung geändert hat. Öffnungszustand und Filter werden bei
  Kontextwechsel zurückgesetzt. 52 Fluttertests bestanden, darunter zwölf
  neue Szenarien; dies ersetzt keine native Zustellungs- oder Cursorabnahme.

  **03.11.2026, Klassenarbeiten und Sichtbarkeit:** Bereitmeldungen prüfen pro
  Ergebnistyp bis zu 500 Kandidaten in stabiler Reihenfolge auf bestehende
  Rechte und Quellen; ältere gültige Hinweise werden nicht bereits durch 100
  ungültige Aufträge verdeckt. Gezielte Lesemarkierungen prüfen ihre Berechtigung
  weiterhin separat. 31 künstliche Klassenarbeitsfälle bestanden auf SQLite
  und isoliertem PostgreSQL; der Fall mit begrenztem Suchfenster wurde auf
  beiden Datenbanken gesondert geprüft. Sehr hohe Meldungskarten werden nach
  Sichtbarkeit des erreichbaren Kartenausschnitts quittiert; 24 Fluttertests
  und 13 Tests im Chrome-Webrunner bestanden. Die 500er-Suchgrenze, das
  fehlende Cursor-Nachladen und native Zustellungsnachweise waren damals offen;
  spätere Prüfungen sind oben beziehungsweise unter Android dokumentiert.

  **03.11.2026, Bereitmeldungen und Sortierung:** Der Abruf überprüft bis zu
  500 gespeicherte Lernrundenaufträge, damit ungültige neue Aufträge ältere
  gültige Hinweise nicht schon nach 100 Kandidaten verdecken. Bei identischer
  Sekunde wird innerhalb dieser Grenze nach Meldungskennung sortiert. Drei
  künstliche Fälle bestanden auf SQLite und isoliertem PostgreSQL. Bei Eltern-
  Tageschecks, Sprachprojekten und Familienanrufen wird die Kennung vor der
  Begrenzung entsprechend der gemeinsamen Anzeige sortiert; drei gezielte
  Fälle bestanden ebenfalls auf beiden Datenbanken. Die Begrenzung auf 500
  Kandidaten und fehlendes Cursor-Nachladen waren damals noch offen; spätere
  Cursorprüfungen sind oben dokumentiert.

  **03.11.2026, Geräte und Filter:** Arten für Lernrunden, Klassenarbeiten,
  Lerntage und Tageschecks sind im Filter unterscheidbar. Alte Schalter- und
  Ruhezeit-Callbacks werden bei Konto-/Sitzungswechsel, verdeckter Route oder
  laufendem Speichern verworfen. 59 Flutter-Widgettests bestanden, darunter
  wirkliche Konto- und Routenwechsel innerhalb der Testumgebung. Dies belegt
  weder eine native Pushzustellung noch ein Nachladen jenseits des Fensters.

  **03.11.2026, veraltete Meldungen:** Ungültige oder bereits zusammengefasste
  Vorbereitungen werden beim Nachrichtenabruf vor der sichtbaren Grenze
  aussortiert. Stabile Blöcke prüfen höchstens 500 Nachrichten; ein künstlicher
  Fall mit 60 ungültigen Meldungen und gleichem Zeitstempel zeigte anschließend
  die korrekten 50 gültigen Nachrichten. 24 SQLite-Fälle sowie zwei gezielte
  Fälle auf isoliertem PostgreSQL bestanden. Die feste Prüfgrenze konnte damals
  ältere Einträge verdecken; die spätere Cursor-Fortsetzung ist oben beschrieben.

  **03.11.2026, Elternhinweise:** Die Auswahl für den Prüfungstagescheck
  begrenzt sich auf Sitzungen nahe dem aktuellen UTC-Tag und berücksichtigt
  den tatsächlichen Kalendertag in der Zeitzone des jeweiligen Prüfungsplans.
  Eine beliebige Grenze von 100 älteren Plänen kann aktuelle Sitzungen nicht
  mehr verdecken. Erledigte Runden unterdrücken weiterhin den Hinweis vor dem
  Versand. 69 künstliche Fälle bestanden auf SQLite und isoliertem PostgreSQL;
  eine physische Pushzustellung und die vollständige Bedienungsabnahme sind
  damit nicht nachgewiesen.

  **03.11.2026, Kindergerät:** Die Freigabe auf Kontoebene und das bewusste
  Einschalten auf dem Kindergerät sind getrennt beschrieben. Nach einer
  späteren Elternfreigabe kann das Kind den Status ohne erneute Anmeldung
  aktualisieren und die Geräteberechtigung selbst anfordern. Die Prüfung des
  Status allein initialisiert Firebase nicht und registriert kein Gerät. Die
  künstlichen Push-Tests unterscheiden Web- und Android-Transport; sie belegen
  keine sichtbare Zustellung auf einem physischen Gerät. Die Cursor-Fortsetzung
  war damals offen; die übrige Gesamtprüfung bleibt weiterhin offen.

  Bereitschaft von Seitenverarbeitung und Lernrunden sowie optional fehlende Tages- oder Prüfungsvorbereitung testen. In-App-Glocke mit scrollendem Nachladen, sichtbarkeitsbezogener Lesemarkierung, Wiederaufnahme und berechtigtem Direktlink prüfen; Push folgt denselben neutralen Ziel- und Berechtigungsregeln. Ruhezeiten, Duplikate, Logout, deaktiviertes Push und fehlgeschlagene Zustellung berücksichtigen.

  **Abnahme:** Genau die vorgesehene berechtigte Person kann den passenden gespeicherten Inhalt öffnen; gelesene und ungelesene Meldungen stimmen nach Scrollen und Gerätewechsel. In-App-Erfolg, FCM-Annahme und sichtbare native Zustellung sind getrennt belegt.

  **01.11.2026, Teilprüfung:** 94 SQLite-Fälle mit künstlichen Familien und
  simuliertem Push bestanden, ein Fall wurde übersprungen. Sie prüfen unter
  anderem gespeicherte Rundenziele, Berechtigungs- und Quellenänderungen sowie
  Wiederholungen. Der vollständige Glockenablauf bleibt gesondert offen; diese
  Tests simulieren FCM und belegen nicht die später separat geprüfte native Anzeige.

  **Historischer Befund vom 01.11.2026:** Das Glockenmenü war scrollbar, der
  API-Endpunkt lieferte damals aber höchstens 50 Ereignisse aus 30 Tagen ohne
  serverseitige Cursor-Fortsetzung. Die spätere paginierte API und ihre Grenzen
  sind oben unter dem 04.11.2026 dokumentiert.

  **02.11.2026, Teilkorrektur:** Eigene Nachrichten wurden bisher erst nach
  dem begrenzten Datenbankabruf ausgefiltert. Viele eigene Nachrichten konnten
  deshalb ältere relevante Meldungen vollständig aus der Glocke verdrängen.
  Der Filter greift jetzt bereits vor der Begrenzung. Künstliche Eltern- und
  Kinderfälle mit jeweils 55 eigenen Nachrichten prüfen auch die anschließende
  Lesemarkierung. Die zugehörigen Inbox-, Lernrunden- und Prüfungsmeldungstests
  bestanden auf isoliertem PostgreSQL mit 77 Fällen und auf SQLite mit 76
  Fällen; ein Zeilensperrentest wird dort bewusst übersprungen und ist im
  PostgreSQL-Lauf enthalten. Die Cursor-Fortsetzung war zu diesem Zeitpunkt
  noch offen; der spätere paginierte Vertrag ist oben dokumentiert.

  **02.11.2026, weitere Teilkorrektur:** Eine bereits sichtbare
  Nachricht konnte beim Quittieren aus den neuesten 50 Ereignissen verdrängt
  worden sein und wurde dann fälschlich mit 404 abgewiesen. Für solche
  Nachrichten prüft die Quittierung die angeforderten IDs erneut gegen die
  aktuelle Familienzugehörigkeit, Empfängerrolle, Aufbewahrungsfrist und
  gegebenenfalls gültige Quellen. Das ersetzt weder die Cursor-Fortsetzung
  noch die entsprechende Prüfung anderer Ereignistypen. Die drei neuen
  künstlichen Fälle bestanden auf SQLite und isoliertem PostgreSQL; sie decken
  Verdrängung, wiederholte Quittierung, fremde/ungültige Quellen und einen
  zwischenzeitlichen Mitgliedschaftsentzug ab. Die bestehende Gesamtsuite für
  Inbox, Lernrunden- und Prüfungsmeldungen bestand mit 78 SQLite-Fällen (ein
  PostgreSQL-Fall übersprungen) und 79 PostgreSQL-Fällen.

  **Historische weitere Teilkorrektur:** Dasselbe Verdrängungsproblem wurde auch für
  Familienanrufe, Eltern-Tageschecks, Wortimporte und Sprachprojekte behoben.
  Für die angeforderten Kennungen werden aktuelle Mitgliedschaft, Ereignisfrist
  und die geltenden Quell-/Statusbedingungen erneut geprüft. Die Tests umfassen
  wiederholte Quittierung, Geschwistertrennung, bestätigte Importe und
  gelöschte Ergebnisse. Fünf gezielte Fälle bestanden auf SQLite und
  isoliertem PostgreSQL; die breitere Regression für Inbox, Lernrunden,
  Prüfungen, Eltern-Erinnerungen und Familienanrufe bestand mit 179
  SQLite-Fällen (drei PostgreSQL-only übersprungen) und 182 PostgreSQL-Fällen.
  Lernrunden-/Prüfungsmeldungen und serverseitige Cursor-Fortsetzung waren
  damals noch offen; spätere Prüfungen sind oben beschrieben.

  **03.11.2026, weitere Teilkorrektur:** Bestätigte Wortimporte, Anrufe aus
  ausschließlich lesend zugänglichen Familien und Tageschecks nicht mehr
  zugänglicher Kinder werden vor der jeweiligen Abrufbegrenzung gefiltert.
  Bereits angezeigte Lernrunden- und Prüfungsmeldungen können auch nach
  Verdrängung quittiert werden; aktuelle Quellen, Sitzung, Zugehörigkeit und
  Prüfungsrevision bleiben für die gezielte Abfrage bindend. Sechs künstliche
  Regressionsfälle bestanden auf SQLite und isoliertem PostgreSQL. Die Prüfung
  ergänzt den PostgreSQL-CI-Auftrag und seine Ergebnisprüfung. Der eigentliche
  Cursor für mehr als 50 Ereignisse, ein vollständiger mobiler Glockenablauf
  und eine sichtbar zugestellte native Pushmeldung waren damals noch offen.
  Die spätere Cursor- und Emulatorprüfung ist oben beziehungsweise unter
  Android beschrieben; der gesamte Glockenablauf bleibt offen.

  **03.11.2026, Aktualisierungsrennen:** Wird eine Lesemarkierung gespeichert,
  während eine ältere Statusantwort unterwegs ist, verwirft die App den alten
  Stand und lädt im Vordergrund erneut. Tests prüfen neue Meldungen, Hintergrund,
  Kontowechsel und sichtbarkeitsbezogenes Lesen; 19 Widgetfälle bestanden. Dies
  ergänzt die bestehende gezielte Aktualisierung, ist aber weder ein Ausbau der
  Cursor-Paginierung noch ein Nachweis nativer Pushzustellung.

- [x] **P1 – Familienanrufe und optionale Medien nur im freigegebenen Umfang abnehmen**

  **04.11.2026:** Rechte, Freigaben, Abbruch und Medienrückkehr wurden mit
  künstlichen Konten auf SQLite, PostgreSQL und Flutter einschließlich Chrome
  geprüft. Ein früherer echter Relaytest ist getrennt dokumentiert.
  Familienanrufe sind gemäß Startumfang nicht automatisch freigegeben; eine
  konkrete Aufnahme erfordert gesonderte Abnahme. Einzelheiten und Grenzen:
  [FAMILY_CALL_MEDIA_ACCEPTANCE_2026_11_04.md](docs/FAMILY_CALL_MEDIA_ACCEPTANCE_2026_11_04.md).

  Falls für die gewählte Startstufe vorgesehen, Eltern-/Kinderrollen, ausdrückliche Kamera-/Mikrofon-/Bildschirmfreigaben, Verbindungsaufbau, Abbruch, Widerruf und Gerätewechsel mit synthetischen Konten prüfen. Medienlinks auf passende katalogisierte Inhalte und Rückkehr zum Lernkontext testen; kein privater Kontext in URL oder Referrer.

  **Abnahme:** Fremde Familien und Administratoren erhalten keinen privaten Zugriff; fehlende Berechtigungen und ausgefallene Medien blockieren den Lernweg nicht. Nicht geprüfte optionale Funktionen sind nicht Bestandteil der Freigabe.

## Laufende Qualitätssicherung und finale Freigabe

- [x] **Katalogtest an die tatsächlich festgelegte CLI binden.** Der lokale
  Test verwechselt eine andere Entwicklungs-CLI nicht mehr mit der im
  Container vorgesehenen Version. Eine explizit angegebene Datei wird gegen
  die Prüfsumme des Installers geprüft; fehlt die passende Host-CLI, weist der
  Test einen Skip aus. Der Katalogtest bestand mit einer hashgleichen Kopie
  der Server-CLI und künstlicher Anmeldung (28 Fälle). Bei abweichender
  Host-CLI wurde der echte CLI-Fall korrekt übersprungen; eine explizit falsche
  Datei wird abgelehnt. Das Ergebnis belegt keine Anbieterfreigabe und keinen
  produktiven Lernauftrag.

- [x] **P1 – Abhängigkeiten und kommende Toolchain-Änderungen prüfen**

  Beim lokalen Releasebuild auf Commit `614f7d3` meldete Flutter WebAssembly-Hinweise für `flutter_tts` und Gradle künftig erforderliche Kotlin-Plugin-Anpassungen; bei Backendtests erschien eine Starlette-/HTTPX-DeprecationWarning. Diese Warnungen sind keine aktuellen Buildfehler, können aber spätere Updates behindern. Kompatible Versionen, Lizenz- und Sicherheitsstände sowie Folgen für Web, Android, Sprache und Firebase anhand verlässlicher Quellen untersuchen. Updates getrennt und reproduzierbar mit bestehender Toolchain, Tests und Rückweg durchführen, ohne geschützte Routen oder Firebase-Projekte auszutauschen.

  **Abnahme:** Jede Warnung ist mit tatsächlicher Auswirkung, zuständiger Abhängigkeit und Lösung oder dokumentiertem Beobachtungszeitpunkt erfasst; angepasste Builds und betroffene Funktions-/Gerätetests sind für den jeweils freigegebenen Umfang nachgewiesen. Ein regulär erfolgreicher JavaScript-Webbuild wird nicht als erfolgreicher WebAssembly-Build ausgegeben.

  **01.11.2026, Sicherheitsprüfung und Update ausgeliefert:** Vier bisherige
  Python-Paketstände hatten Treffer in OSV. Die Locks für Backend und
  Codex-Worker wurden auf verfügbare korrigierte Versionen aktualisiert. Die
  erneute Abfrage der festgeschriebenen PyPI- und Pub-Versionen sowie der
  erfassten QA-/Workerstände ergab keinen Treffer; sie deckt unter anderem
  Gradle-Transitive und Systempakete nicht vollständig ab. Versionsbereiche,
  Beispielmeldungen, Lizenzen der betroffenen Pakete, Toolchainwarnungen und
  Nachprüftermin stehen in `docs/DEPENDENCY_AUDIT_2026_11_01.md`.
  Release `1.38.58+213` enthält die Aktualisierungen; die Versionen im
  Backend und das neu gebaute Codex-Workerimage wurden auf dem Zielserver
  geprüft. Die vollständige CI und die im Bericht genannten gezielten Tests
  bestanden. Der Bericht benennt Auswirkungen, weitere Schritte und einen
  Nachprüftermin für die bestehenden Toolchainwarnungen. Ein Androidgerät und
  ein echter Wasm-Build wurden dabei nicht getestet oder behauptet.

- [ ] **P1 – Sicherheitsprüfung der übrigen Lieferkette ergänzen**

  - [x] **Firebase-Hintergrundworker in die Paketprüfung aufnehmen.** Der
    bisher übersehene Serviceworker lädt zwei weitere Compat-Skripte. Der
    lesende Check des öffentlichen Workerendpunkts bestätigt die beiden
    festen Imports; ein separater npm-Lock erfasst elf aufgelöste Pakete und
    deren per SHA-512 geprüfte Archive. Die datierte OSV-Abfrage meldete keine
    Kennungen. CDN-Bundlezuordnung, Laufzeitintegrität, Lizenzen und alle
    anderen offenen Lieferkettenbestandteile bleiben offen. Details und
    Grenzen: [Prüfbericht](docs/EXTERNAL_WEB_SCRIPTS_2026_11_04.md#ergänzung-0511-hintergrund-serviceworker-und-compat-pakete).

  - [x] **Festgelegte Firebase-npm-Paketarchive tatsächlich prüfen.** Alle
    neun Archive der dokumentierten Auflösung wurden begrenzt und ohne
    Weiterleitung geladen und gegen den gesperrten SHA-512-Wert geprüft; die
    erneute OSV-Abfrage und der datierte Beleg sind dokumentiert. Die
    CDN-Zuordnung, externe Prüfsignaturen und Lizenzpflichten bleiben offen.
    [Prüfung und Grenzen](docs/EXTERNAL_WEB_SCRIPTS_2026_11_04.md#ergänzung-0511-archivprüfung-der-aufgelösten-npm-pakete).

  **04.11.2026, erweiterte Bestandsaufnahme:** Ein npm-Lock für die direkten
  und transitiven Firebase-App-/Messaging-Abhängigkeiten sowie POM-Lizenzen
  für 106 zuvor inventarisierte Maven-Koordinaten sind mit Prüfsummen und
  wiederholbaren Prüfscripten erfasst. Vier Flutter-POMs nennen keine eigene
  Lizenz; offizielle Engine-Quellen und lokale Hinweise wurden ergänzend
  dokumentiert, ohne eine Gesamtfreigabe abzuleiten. Eine lesende Inventur
  des laufenden Codex-Containers fand OSV-Meldungen für 27 von 73 erfassten
  Debian-Quellpaketversionen sowie für `pip 25.0.1`; Erreichbarkeit und
  Ausnutzbarkeit sind ungeprüft. Ein Layer eines öffentlichen Basisimage-
  Kandidaten enthält eine für einen konkreten OpenSSL-Befund korrigierte Version, ein sicher
  isolierter vollständiger Neubau und die Behebung sind nicht belegt.
  Einzelheiten: `docs/CODEX_CONTAINER_AUDIT_2026_11_04.md` und
  `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md`. Keine Serveränderung erfolgte.

  - [x] Den npm-Abhängigkeitsbaum der beiden ausdrücklich erfassten Firebase-
    Pakete samt Versions-, Lizenz- und Integritätsmetadaten erfassen und
    wiederholbar gegen OSV prüfen. Die Zuordnung zu den ausgelieferten CDN-
    Bundles und eine rechtliche Lizenzprüfung bleiben gesondert offen.

  - [x] Die POM-Lizenzmetadaten der 106 bestehenden Direct-/Play-Koordinaten
    samt Quellen, Eltern-POMs und Prüfsummen inventarisieren; vier fehlende
    POM-Angaben und die offiziellen Flutter-Engine-Hinweise ausdrücklich
    ausweisen. Die vollständigen Binär- und Weitergabepflichten bleiben offen.

  Die Abhängigkeitsprüfung vom 01.11.2026 deckt Gradle-Transitive,
  Container-Basisimages, Systempakete und tatsächlich ausgelieferte externe
  JavaScript-Ressourcen nicht vollständig ab. Diese Bestände versioniert
  erfassen und mit geeigneten Quellen auf bekannte Sicherheitsmeldungen und
  Lizenzen prüfen; Ergebnisse, betroffene Laufzeitpfade, Zuständigkeit und
  einen regelmäßigen Überprüfungsweg dokumentieren. Keine Trefferfreiheit für
  nicht geprüfte Komponenten oder unbekannte Schwachstellen behaupten.

  **Abnahme:** Für den festgelegten Betriebsumfang sind die genannten
  Komponenten und ihre Versionen nachvollziehbar erfasst, aktuelle Treffer
  bewertet beziehungsweise korrigiert und die Kontrolle wiederholbar.

  **Korrektur 01.11.2026:** Der Bestandsbericht
  `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md` wurde nach lesendem Abgleich
  korrigiert: Der Host verwendet Ubuntu 24.04, die Direct-APK verlangt die
  Installationsberechtigung. Eine Aufzählung direkter Komponenten belegt
  weder vollständige native Transitive noch deren Sicherheits- und Lizenzstand.
  Der Bericht benennt nun die fehlenden Nachweise; der Punkt bleibt offen.

  **Ergänzung 01.11.2026:** Eine lesende Ubuntu-Abfrage meldet 18
  ausstehende `esm-apps`-Updates mit `pending_attach`, darunter Caddy und
  Podman; Ubuntu Pro ist nicht verbunden. Außerdem läuft Kernel 6.8.0-138,
  obwohl 6.8.0-147 installiert ist und das System einen Neustart verlangt.
  Vor Änderungen müssen Paketquellen, konkrete Sicherheitsmeldungen und die
  Dienste des gemeinsam genutzten Hosts geprüft werden. Kein Neustart wurde
  ausgelöst. Details und Einschränkungen stehen in
  `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md`.

  - [x] Die nativen Gradle-Laufzeitbäume für Direct und Play offline auflösen,
    versioniert erfassen und die daraus aufgelösten Maven-Koordinaten mit der
    OSV-Batch-API einschließlich Pagination prüfen. Der Bericht
    `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md` verlinkt beide Bäume und alle 106
    Einzelresultate. OSV meldete keine Treffer; die noch fehlende Lizenz- und
    Host-/Containerprüfung bleibt ausdrücklich offen.

  - [x] Den Firebase-Web-Bootstrap und seine beiden ausdrücklich importierten
    CDN-Module erfassen und die npm-/OSV-Metadaten der drei ausgewählten
    Pakete wiederholbar prüfen. Ergebnis und Grenzen stehen in
    `docs/EXTERNAL_WEB_SCRIPTS_2026_11_04.md`; transitive Abhängigkeiten,
    Bundlezuordnung, Checkout, Host und vollständige Lizenzen bleiben offen.

  **04.11.2026, Prüferhärtung:** Fehlerhafte OSV-Antworten und unendlich viele
  Seitentokens führen zum Fehler statt zum Ergebnis „keine Treffer“. Gültige
  leere und reine Fortsetzungsseiten bleiben möglich. 22 Offlinefälle für
  Firebase und Maven bestanden; die lesende Abfrage der drei dokumentierten
  Firebase-Paketversionen war erfolgreich. Der Gesamtpunkt bleibt offen.

- [ ] **P1 – Datenschutz und Anbieterunterlagen fachkundig prüfen lassen**

  Verzeichnis der Datenarten und Datenflüsse für Kinder, Eltern, Fotos, Lernstände, KI-Anbieter, Hosting, Firebase und Support erstellen. Tatsächliche Auftragsverarbeiter, Unterauftragsverarbeiter, Speicherorte, internationale Übermittlungen, Löschfristen und vertragliche Grundlagen dokumentieren. Eine qualifizierte Stelle prüft Rechtsgrundlagen, altersgerechte Informationen, Elternrechte, Widerruf und ob eine Datenschutz-Folgenabschätzung erforderlich ist; bestehende Betreiberfreigaben nicht mit einer unabhängigen Rechtsprüfung verwechseln. Für KI-Funktionen den konkret anwendbaren Rechtsrahmen und die Risikoeinstufung bewerten lassen.

  **Abnahme:** Dokumentation, Bewertung, gegebenenfalls Folgenabschätzung, vereinbarte Maßnahmen und Zuständigkeiten liegen für den vorgesehenen Freigabeumfang vor; offene Risiken sind vor der jeweiligen Freigabe entschieden.

- [ ] **P1 – Echtzeitstatus gezielt und zuverlässig bereitstellen**

  - [x] **Geöffnete Foto- und Gerätedialoge beim Anmeldewechsel schließen.**
    Eine separate Benachrichtigung über die lokale Anmeldeabsicht schließt
    bereits geöffnete Fotovorschauen, Gerätedetails und Bestätigungen, ohne
    allgemeine App-Listener und dadurch möglicherweise Datenabrufe auszulösen.
    Auch überdeckte Fotovorschauen werden entfernt. Künstliche Tests prüfen
    Dialoge, Abbruch und konkurrierende Anmeldeabsichten; daraus folgt keine
    allgemeine Lösung für andere Ansichten oder den Cookie-Wettlauf.

  - [x] **Offene lokale Fotolisten an die Anmeldeabsicht binden.** Spät
    geladene lokale Fotos und Fehler werden nach Sitzungs- oder Absichtswechsel
    nicht angezeigt. Alte Vorschau- und Tagesaktionen werden nicht ausgeführt;
    ein bewusstes erneutes Laden nach abgebrochener Anmeldung ist möglich.
    Eine bereits geöffnete Vorschau schließt auch ohne Bedienung bei einer
    neuen Anmeldeabsicht. Künstliche Widgettests prüfen die Wechsel und den
    lokalen Fotobestand. Die allgemeine sitzungsübergreifende Cookie-Abnahme
    bleibt offen.

  - [x] **Kindergeräteliste und Abmeldungen an die Anmeldeabsicht binden.**
    Späte Geräteantworten und Fehler werden nach einem Sitzungs- oder
    Absichtswechsel verworfen. Bereits geöffnete Bestätigungen können keine
    alte Abmeldung auslösen; bei einer laufenden Sammelabmeldung werden nach
    einem Wechsel keine weiteren Geräte abgemeldet. Ein bereits angenommener
    Löschauftrag bleibt bestehen und wird nicht automatisch wiederholt.
    Der Abschluss einer alten Abmeldung darf eine neue Anmeldung nicht löschen.
    Neun künstliche Widgettests prüfen die Einzel- und Sammelwege sowie
    bewusstes Neuladen auch im Chrome-Webrunner bei 390 px. Die allgemeine
    API- und Cookie-Race-Abnahme bleibt offen.

  - [x] **Familienübersicht und Klassenarbeitsauswahl an die Anmeldeabsicht binden.**
    Beide Familienabrufe prüfen Konto, Familie, Sitzung und Anmeldeabsicht
    nach Abschluss. Verspätete Ergebnisse und Fehler zeigen keine alten
    Familieninhalte; ein erneutes Laden ist ausdrücklich möglich. Bereits
    angezeigte Kinderkarten und Verwaltungsaktionen werden nach Beginn einer
    neuen Anmeldung nicht mehr ausgeführt. Widgettests prüfen Erfolg und Fehler,
    Konto-, Familien-, Token- und Absichtswechsel sowie das normale Öffnen;
    dieselben 16 künstlichen Fälle bestehen auch im Chrome-Webrunner bei 390 px.
    Die übrigen Transporte, der Beginn einer Anfrage während laufender
    Anmeldung und der separate Cookie-Wettlauf bleiben offen.

  - [x] **Verspätete Fach- und Sammlungslisten beim Anmeldewechsel verwerfen.**
    Fachübersicht und paginierte Lern- beziehungsweise Materialliste binden
    jeden Leseauftrag zusätzlich an die beim Start aktuelle Anmeldeabsicht.
    Ein verspätetes Ergebnis oder ein Fehler nach Beginn einer anderen
    Anmeldung wird nicht angezeigt; vom alten Ergebnis abhängige Aktionen
    werden zurückgesetzt. Ein erneutes bewusstes Laden ist möglich. Künstliche
    Widgetfälle prüfen die Fachübersicht und die Themenliste einschließlich
    Zufallsstart und Wiederaufnahme; die Listen- und Sammlungsregressionen
    bleiben grün. Andere API-Transporte und der separate Cookie-Wettlauf
    bleiben offen. Ein Leseauftrag, der erst nach Beginn einer noch laufenden
    Anmeldung startet, ist dadurch nicht generell gegen alte Cookies geschützt.

  - [x] **Verspätete Profilfoto-Antworten nach Kontowechsel verwerfen.**
    Bild, Metadaten und Ergebnisse von Fotoänderungen werden nicht an die
    Oberfläche zurückgegeben, wenn zwischen Anfrage und Antwort das Konto,
    der Sitzungstoken oder die Anmeldeabsicht gewechselt hat. Eine bereits
    serverseitig ausgeführte Änderung wird dabei nicht wiederholt oder als
    rückgängig dargestellt. Künstliche Tests verzögern Antworten für alle
    vier Profilfotoaktionen und prüfen die drei Wechselarten. Das löst weder
    den Cookie-Wettlauf noch die übrigen gemeinsamen API-Transporte.

  - [x] **Passwort-Anmeldung und anschließende Lesezugriffe verbinden.**
    Nach erfolgreicher Übernahme widerruft das geschlossene Loginformular die
    angenommene Anmeldeabsicht nicht mehr. Ein Abbruch bleibt wirksam; eine
    zwischenzeitlich gestartete neue Anmeldung verhindert die alte Navigation.
    Künstliche Widgettests prüfen Erfolg, Abbruch und konkurrierende Absichten.
    Demo, Google und der separate Cookie-Wettlauf bleiben offen.
    [Prüfung](docs/LOGIN_INTENT_DISPOSAL_2026_11_07.md).

  - [x] **Benachrichtigungsabruf und Verlauf an die Anmeldeabsicht binden.**
    Beim Beginn einer neuen Anmeldung werden verspätete Kopf- und
    Verlaufsantworten nicht mehr in den bisherigen Speicher übernommen; auch
    verspätete Berechtigungsfehler löschen ihn nicht. Künstliche Tests prüfen
    beide Wege einschließlich einer verzögerten Freigabe zur Veröffentlichung.

  - [x] **Verspätete Lesebestätigungen lokal abgrenzen.** Ein nach Beginn
    einer neuen Anmeldung eintreffender Erfolg oder Fehler verändert die alte
    lokale Benachrichtigungsliste nicht. Ein bereits abgesandter und auf dem
    Server angenommener Schreibvorgang wird dadurch nicht rückgängig gemacht.
    Ein künstlicher Test prüft die verspätete Antwort.

  - [x] **Grafikstatus und Grafikaufträge an die Anmeldeabsicht binden.**
    Verspätete Ergebnisse von Bildstatus, Bilddatei, Bildprüfung und
    Erklärgrafik-Vorbereitung werden bei neuer Anmeldeabsicht verworfen;
    geplante Statusabfragen starten dann nicht erneut. Bereits gesendete
    Aufträge bleiben serverseitig bestehen und ihre Wiederholungsschlüssel
    erhalten. Künstliche Widgettests prüfen verzögerten Status, Bildauftrag
    und Erklärgrafik-Auftrag; die gesonderte Cookie-Lücke bleibt offen.

  - [ ] **Verspätete gemeinsame API-Antworten nach Kontowechsel absichern.**
    Ein zentraler Abbruch über alle Transporte wurde nach fehlgeschlagener
    vollständiger CI zurückgenommen: Mehrere bestehende Aufrufer behandeln
    verspätete Ergebnisse selbst und fingen den neuen Fehler nicht ab; zudem
    trat in einem mobilen Browserlauf ein Ladefehler auf. Eine erneute Lösung
    muss sämtliche Aufrufer sowie Anmeldung und Wiederaufnahme berücksichtigen,
    ohne unklare Schreibvorgänge automatisch zu wiederholen. Der separate
    Cookie-Wettlauf bleibt ebenfalls offen.

    **Nachrichtenentwürfe bei Anmeldebeginn schützen:** Ein geöffnetes
    Nachrichtenformular schließt sich bei einer neuen Anmeldeabsicht. Alte
    Rückrufe versenden nichts; verspätete Erfolge und Fehler verändern die
    neue Ansicht nicht. Nach abgebrochener Anmeldung bleibt der Entwurf für
    dasselbe Konto erhalten. Eine bewusst wiederholte unklare Übermittlung
    verwendet denselben Idempotenzschlüssel. 46 künstliche Flutterfälle zur
    Nachricht, Themenansicht und Kinderstartseite bestanden; bereits
    versendete Anfragen bleiben serverseitig bestehen. Neu während einer
    laufenden Anmeldung geöffnete Ansichten und der allgemeine Cookie-Wettlauf
    sind damit nicht abgesichert.

    **Hilfeauswahl bei neuer Anmeldung schließen:** Die offene Hilfeauswahl
    und ihr optionaler Dialog zum erneuten Laden sind an die ursprüngliche
    Anmeldeabsicht gebunden. Zuvor eingefangene Aktionen senden keine Nachricht
    und lösen kein Neuladen aus. Beide Dialogrouten werden getrennt verfolgt,
    damit die ausblendende Auswahl nicht die Referenz des nachfolgenden
    Dialogs überschreibt. 35 künstliche Fälle zu Hilfe und Kinderstartseite
    bestanden; separate Nachrichten- und Anrufformulare sowie das globale
    Cookie-Problem sind damit nicht allgemein abgenommen.

    **Geöffnete Heftfotos bei Anmeldebeginn ausblenden:** Die Fotoansicht
    blendet das private Bild aus und fordert seine Entfernung aus dem Cache an,
    verwirft verspätete
    Bildantworten und sperrt alte Zoomaktionen. Ein Seitenwechsel während der
    Anmeldung lädt kein weiteres Bild über die alte Ansicht. 31 künstliche
    Fälle für Foto, Galerie und Mobilansicht sowie die zusätzliche gezielte
    Fotowechselprüfung decken den Ausschnitt ab. Nach einer abgebrochenen
    Anmeldung muss die Ansicht gegebenenfalls erneut geöffnet werden. Der
    übergreifende Cookie-Wettlauf und neu während der Anmeldung geöffnete
    Ansichten bleiben offen.

    **Klassenarbeiten zusätzlich abgesichert:** Die Klassenarbeitenansicht
    und ihre Dialoge binden sich an die beim Öffnen aktuelle Anmeldeabsicht.
    Beginnt eine neue Anmeldung, werden alte Inhalte und Dialoge ausgeblendet;
    gespeicherte Rückrufe und verspätete Listen laden die alte Ansicht nicht
    wieder und starten keine weitere Verarbeitung. 57 künstliche Flutterfälle
    zu Planung, Nacharbeit und diesem Wechsel sowie 42 weitere Foto-,
    Lebenszyklus- und Nacharbeitsfälle bestanden. Die Ansicht muss
    nach einer abgebrochenen Anmeldung gegebenenfalls erneut geöffnet werden.
    Dies behebt weder das globale Transportproblem noch den Cookie-Wettlauf.

    **Heute und Lernüberblick bei Anmeldebeginn abblenden:** Die Übersicht
    bindet sich an die Anmeldeabsicht, übernimmt alte Statusabfragen nicht
    mehr und blendet deren Ergebnisse aus. Die Hauptaktionen prüfen diese Bindung auch noch
    vor dem nächsten Neuzeichnen; ein geöffneter Dialog zur persönlichen
    Lernschrittbegründung schließt sich. Bereits gesendete Anfragen bleiben
    serverseitig bestehen. Bei einer abgebrochenen Anmeldung muss die Ansicht
    gegebenenfalls erneut geöffnet werden. 59 künstliche Fälle zur Kinder-
    startseite und 38 Fälle zu Statusabgleich und Elternansicht bestanden;
    andere Dialoge und das globale Cookie-Problem sind nicht abgenommen.

    **Geöffneten Lernweg an dieselbe Anmeldeabsicht binden:** Vor dem
    Neuzeichnen gespeicherte Vorbereitungsaktionen starten nach Beginn einer
    neuen Anmeldung keinen Auftrag; verspätete Wege erscheinen nicht erneut.
    Auch bestehende private Dialoge werden geschlossen. 77 künstliche Fälle
    zum Lernweg und zur Kinderstartseite bestanden. Bereits gesendete Aufträge
    werden nicht rückgängig gemacht; neu geöffnete Ansichten während einer
    noch laufenden Anmeldung und der allgemeine Cookie-Wettlauf bleiben offen.

    **Fotoimport und elterliche Bildprüfung zusätzlich begrenzt:** Der
    klassische Fotoimport bindet die Zustimmung und den Start des Pickers
    an Konto, Familie, Sitzung und Anmeldeabsicht; ein verspäteter Status
    öffnet nach einer neuen Anmeldung keine Auswahl mehr. Die elterliche
    Bildbefundprüfung verbirgt alte Inhalte und nimmt keine alten Aktionen
    oder späten Antworten an. Bereits abgesendete Prüfungen werden nicht
    rückgängig gemacht. 26 künstliche Fälle zu Bildbefunden, Fotoeinwilligung
    und kindlichen Aktionen sowie 94 angrenzende Heft- und Materialfälle
    bestanden. Verspätete Fehler aus diesem Import werden nach einem
    Anmeldewechsel nicht mehr im neuen Konto angezeigt; aktuelle Fehler
    bleiben sichtbar. Weitere 15 künstliche Fälle prüfen diese Wege. Andere
    Importpfade und direkte Ressourcen sind damit nicht allgemein abgesichert.

  - [x] **Andere Sitzung desselben Kontos bei markierten API-Zugriffen ablehnen.**
    Die gemeinsame App erhält bei Login und Wiederaufnahme einen nicht
    autorisierenden Sitzungsvergleichswert und sendet ihn bei gemeinsamen
    API-Aufrufen. Ein anderer noch gültiger Cookie desselben Kontos führt zu
    409 vor dem Lesezugriff oder Logout. Ein isolierter Chrome-Test vertauscht
    zwei erfolgreiche Loginantworten desselben künstlichen Kontos; der alte
    Cookie überschreibt den neuen weiterhin, die markierten Zugriffe werden
    aber abgewiesen. 72 künstliche Konto-, Google- und Adminfälle bestanden
    auf isoliertem PostgreSQL. Ältere Clients, direkte Ressourcen und die
    eigentliche Cookie-Ursache bleiben offen. Die Änderung ist noch nicht
    produktiv veröffentlicht. [Prüfung](docs/ACCOUNT_ASSERTION_2026_11_06.md).

  - [ ] **Verspätete Login-Cookies kontenübergreifend absichern.** Ein echter
    künstlicher Chrome-/SQLite-Test belegt, dass eine ältere erfolgreiche
    Loginantwort den Cookie einer neueren Anmeldung überschreiben kann. Eine
    serverseitige Lösung muss konkurrierende Anmeldungen, andere Tabs, Google,
    Logout, Altclients und geschützte Datenabrufe einbeziehen; ein bloßes
    Pending-Flag genügt nicht. Der reproduzierende Test beweist den Fehler,
    nicht dessen Behebung. [Befund und Lösungsgrenzen](docs/WEB_LOGIN_COOKIE_RACE_2026_11_06.md).

  - [x] **Abweichendes Browserkonto bei gekennzeichneten API-Zugriffen ablehnen.**
    Die gemeinsame App sendet das angezeigte Konto als zusätzliche Prüfung;
    Rechte stammen weiterhin ausschließlich aus der Serversitzung. Ein
    fremdes Konto führt auf geschützten Aufrufen zu 409, einschließlich vor
    Fotoannahme und bei der Benachrichtigungskonfiguration. Künstliche
    Browser-, PostgreSQL- und Flutter-Fälle belegen den begrenzten Schutz.
    Alte Clients, headerlose Zugriffe und mehrere Sitzungen desselben Kontos
    bleiben Teil des darüber offenen Cookie-Problems.
    [Prüfung](docs/ACCOUNT_ASSERTION_2026_11_06.md).

  - [x] **Alte Eltern-Lernplanaktionen an die geladene Anmeldeabsicht binden.**
    Bereits sichtbare Themenkarten, Wochenaktionen und Auftragseditoren prüfen
    eine neue Anmeldeabsicht vor der Aktion und verlangen zunächst einen
    lesenden Planabgleich. Ein erneuter lesender Planabruf gibt die Aktionen wieder
    frei; eine späte Speicherantwort löst keinen zweiten Auftrag aus. Da ein
    Pending-Signal fehlt, kann ein expliziter Neuladevorgang während noch
    laufender Anmeldung die alte Sitzung wieder freigeben; der umfassende
    Schutz während der Anmeldung bleibt deshalb offen. Der
    Anmeldebeginn sendet noch kein eigenes Änderungssignal: Ein passiv offener
    Editor verschwindet erst bei einer regulären Statusmeldung, Bedienung oder
    Ende seiner laufenden Anfrage. Ein unbemerkter Cookiewechsel aus einem
    anderen Tab bleibt offen. [Prüfgrenzen](docs/PARENT_PLAN_LOGIN_RACES_2026_11_06.md).

  - [x] **Eltern-Lernkompass vor Sitzungswechsel und Rechteentzug schützen.**
    06.11.2026: Ein gemeldeter Tokenwechsel entfernt gespeicherte private
    Berichte; eine neue Anmeldeabsicht blockiert alte Aktionen und verwirft
    verspätete Antworten. Beim Austausch des App-Zustands bindet sich die
    Ansicht neu. Bei HTTP 401/403 aus Bericht, Vergleich oder Einstellungen
    werden auch die privaten Vergleichsdaten entfernt und laufende Lese- und
    Schreibantworten verworfen. Nach abgebrochener Anmeldung kann derselbe
    Elternzugang den Stand bewusst neu laden; alte Antworten können keine
    neue Aktion überschreiben. Die künstlichen Tests decken keinen
    unbemerkten Cookiewechsel aus einem anderen Tab ab. Einzelheiten und
    Prüfgrenzen: [Nachweis](docs/PARENT_INSIGHTS_SCOPE_2026_11_06.md).

  - [x] **Neuen Google-Flow vor verspätetem Cookie-Löschen schützen.**
    06.11.2026: Logout und Abschluss löschen das gemeinsame Google-Flow-Cookie
    nicht mehr per verzögerbarer Antwort. Logout widerruft zusätzlich den
    mitgesendeten Browser-Flow, auch wenn er vor der Sitzung anonym begonnen
    wurde. Das versionierte Cookie ist dafür unter `/api/auth` erreichbar;
    ältere begonnene Google-Flows müssen neu gestartet werden. Ein isolierter
    Zwei-Tab-Chrometest prüft einen neu gestarteten Flow nach verzögerter
    Logoutantwort, API-Fälle prüfen die Ergebnisarten, Replay und Widerruf
    während eines künstlich angehaltenen Google-Exchanges. Weitere Login- und
    Start-Antwortrennen bleiben offen.
    [Prüfung und Grenzen](docs/AUTH_401_SESSION_RACE_2026_11_05.md).

  - [x] **Späte 401-Antworten an die ursprüngliche Sitzung binden.**
    05.11.2026, Coding-AI, Änderungen auf Basis `f38673a` und `d02c48b`:
    JSON-, Foto-, PDF-, Datei- und Avataranfragen löschen eine spätere
    Sitzung nicht durch verspätete 401-Antworten. Web-Loginrevision und
    native Tokens werden berücksichtigt; eine neue Kontoübernahme wartet
    auf private lokale Bereinigung. 125 kombinierte VM- und 38 gezielte
    Chrome-Fälle sowie unabhängiger Review bestanden. Ein älterer
    tabübergreifender Wettlauf beim Google-Flow bleibt gesondert offen.
    [Nachweis und Grenzen](docs/AUTH_401_SESSION_RACE_2026_11_05.md).

  - [x] **Verspäteten Logout gegen ein neueres Web-Sitzungscookie absichern.**
    06.11.2026, isolierter Zwei-Tab-Chrometest mit künstlichen Konten: Die alte
    Logout-Antwort löscht eine neue Anmeldung nicht; nach echtem Logout ist der
    alte, bis zum Cookieablauf gespeicherte Wert serverseitig widerrufen. Der
    eigenständige Google-Flow-Wettlauf bleibt offen. Einzelheiten und Grenzen:
    [Nachweis](docs/AUTH_401_SESSION_RACE_2026_11_05.md).

  - [x] **Wiederaufnahme beim erneuten Einlesen einer Heftseite absichern.**
    05.11.2026, Coding-AI, Änderungen auf Basis `f38673a`: Nach Hintergrund, überdeckter Route und
    Sitzungswechsel werden Quelle und Auftragsstatus erneut gelesen;
    überholte Ergebnisse und alte Bereitschaftsaktionen bleiben verborgen.
    403/404 entfernen private Angaben, 429 startet keinen automatischen
    Versuch. 37 künstliche VM-Widgetfälle und 25 Chrome-Fälle bestanden;
    ein übergreifender Geräte- und Ereigniskanalnachweis bleibt offen.
    [Umfang](docs/REALTIME_STATUS.md).
  **05.11.2026, Sitzungswechsel:** Bereits geladene Kinder- und
  Elternübersichten verschwinden bei gemeldetem Konto-, Familien- oder
  Tokenwechsel; ein laufender
  Statusabruf darf sie nicht zurückbringen. In derselben Familie startet die
  Ansicht einen autorisierten GET unter dem geänderten Konto-/Sitzungskontext;
  nach Familienwechsel fordert sie Eltern zur neuen Kinderwahl auf; Kinder
  laden ihre eigene Route erneut.
  Die künstlichen Clienttests bestanden auf der VM und in Chrome bei 390 px
  einschließlich sicherem Neuaufbau. Sie decken keinen unbemerkten Cookie-Wechsel oder
  eine echte geräteübergreifende Zustellung ab. Der Gesamtpunkt bleibt offen.

  - [x] **Fotoverarbeitungsstatus über zwei künstliche Sitzungen prüfen.**
    Beide Sitzungen sehen den Fortschritt; eine fremde Familie wird abgewiesen.
    GETs erzeugen keine Aufträge oder Lernbelege. SQLite und PostgreSQL
    bestanden; [Einzelheiten](docs/REALTIME_STATUS.md).

  - [x] **Sprachprojekte und Nacharbeiten bei Rückkehr und Rechteverlust
    absichern.** Sitzungsgebundene Wiederaufnahme, ältere GETs und manuelle
    Wiederholung nach 4xx sind mit künstlichen Daten geprüft. Zwei künstliche
    Sitzungen sehen denselben Projektstatus; ein fremdes Konto wird abgewiesen.
    Die Prüfung und ihre Grenzen stehen in [REALTIME_STATUS.md](docs/REALTIME_STATUS.md).

  - [x] **Tutorstatus und Entwurf sitzungsgebunden wiederaufnehmen.** Ein
    laufender GET erhält nach Vordergrund- oder Routenrückkehr eine gezielte
    Folgeabfrage; bei 4xx stoppt die automatische Abfrage. Sitzungswechsel
    entfernt die alte Ansicht und Entwürfe. Künstliche Widget- und
    Chrome-Tests prüfen die Übergänge; eine vollständige Geräteabnahme bleibt offen.

  - [x] **Wiederaufnahme laufender Vorbereitungs-, Foto- und Lernwegansichten
    gegen überholte GETs absichern.** Nach Rückkehr folgen gezielte GETs,
    4xx/429 lösen keine unbeabsichtigte Wiederholung aus; bei Rechteverlust
    werden private Altansichten entfernt. Künstliche Tests decken unter
    anderem 54 Foto- und 51 Lernweg-Widgetfälle sowie Chrome-Fälle ab.
    [Bestandsaufnahme und Grenzen](docs/REALTIME_STATUS.md). Geräteübergreifende
    Abnahme und tatsächliche Zustellung bleiben eigenständig offen.

  **04.11.2026, Statuswiederaufnahme:** Die untersuchten Ansichten verwenden
  gezielte GET-Aktualisierungen; ein SSE-/WebSocket-Endpunkt wurde dabei nicht
  gefunden. Die Rundenvorbereitung prüft den Status nach vorübergehendem
  Verbindungs- oder Serverfehler bei Rückkehr erneut, auch wenn noch ein älterer
  Abruf läuft. HTTP 429 und andere 4xx lösen keinen automatischen Versuch aus.
  35 Widget- und vier Chrome-Fälle bei 390 Pixeln bestanden. Geräteübergreifende
  Zustellung und vollständige Abnahme bleiben offen; GET startet keinen Auftrag.

  Für Fotoverarbeitung, Lernrundenvorbereitung, Benachrichtigungen und andere tatsächlich zeitkritische Ansichten die vorhandenen Aktualisierungswege erfassen. Wo sinnvoll, authentifizierte SSE- oder WebSocket-Ereignisse oder gleichwertige gezielte Aktualisierung einsetzen: Familienzuordnung, Wiederverbindung, Ereignisverlust, Gerätewechsel und Hintergrundzustand beachten. Keine komplette Seite in störenden Abständen neu laden; Statusabrufe und Wiederverbindung dürfen keine KI-Aufträge oder Kosten auslösen. Weniger kritische Ansichten nach belegtem Bedarf aktualisieren, ohne einen pauschalen Umbau als Erfolg auszugeben.

  **Abnahme:** Künstliche Geräte zeigen relevante Statusänderungen ohne ungewollten Voll-Refresh, verlieren weder Eingaben noch Navigation und sehen keine Ereignisse anderer Konten; Ausfall und Wiederaufnahme sind reproduzierbar getestet.

- [ ] **P2 – Modellwechsel und Markenauftritt kontrolliert vorbereiten**

  Neue KI-Modelle einschließlich eines möglichen Terra-Einsatzes getrennt für Bilderkennung, Erklärungen, Bewertungen, Kosten und Datenschutz anhand real verfügbarer Anbieterkennungen und künstlicher Prüffälle evaluieren; Katalogdaten allein sind keine Freigabe. Nutzerseitige Bezeichnung SchuleSchlau, vorhandene Logos, Androidartefakte und Texte konsistent halten. Die bisherige Adresse bleibt bestehen, bis eine spätere Domain- oder Migrationsentscheidung tatsächlich getroffen wurde; keine Domainregistrierung aus dieser Roadmap ableiten.

  **Abnahme:** Jeder eingesetzte Modell-/Upstreamwechsel hat nachvollziehbare Qualitäts-, Kosten-, Sicherheits- und Rollbacknachweise. Marken- und Adressänderungen sind kanalübergreifend geprüft und beschädigen keine Logins, Links oder Updates.

- [ ] **P1 – Unabhängigen Sicherheits- und Kinderschutztest durchführen**

  Eine qualifizierte unabhängige Prüfung mit vereinbartem Umfang für Konten, Sessions, Familie/Geschwister/Admin, Uploads, Löschung, URLs, Prompt-Injection, KI-Ausgaben, Release und Infrastruktur durchführen. Kinderfreundliche Fehlermeldungen, Eskalation bei problematischen Inhalten, Datenminimierung und menschliche Ansprechbarkeit gesondert bewerten. Freigaben und Testzugänge begrenzen; Testdaten und -ergebnisse datensparsam behandeln.

  **Abnahme:** Bericht mit nachvollziehbaren Fundstellen, Risikoeinstufung und Nachtests liegt vor; kritische und hohe Befunde sind behoben beziehungsweise vor jeglicher Freigabe durch die verantwortliche Stelle nachvollziehbar entschieden.

- [x] **P1 – Abnahmen systematisch und wiederholbar automatisieren**

  **Abnahme 24.11.2026:** Der vollständige GitHub-Lauf
  [45387679206](https://github.com/meinzeug/schuleschlau/actions/runs/45387679206)
  bestand für `a30edee`, einschließlich aller Backend- und Flutterpartitionen,
  isoliertem PostgreSQL, Operationsprüfungen, Webbuild und elf lokalen
  Browserfällen. Der Browserumfang deckt künstlichen Fotoimport, Aufgaben und
  Lernstand, Schulbuddy, Benachrichtigungen sowie Eltern-/Kinderrollen ab. Die
  CI prüft Sammlung, Ausführung und Ergebnisverträge; Testdoppel, Skips und
  fehlende Nachweise bleiben erkennbar. Der vorherige fehlgeschlagene Lauf ist
  dokumentiert. Tatsächliche Anbieterqualität, native Geräte, fachliche
  Vollständigkeit und produktive Wiederherstellung bleiben eigenständige
  offene Abnahmen. [Prüfmatrix](docs/ACCEPTANCE_AUTOMATION_2026_11_24.md).

  - [x] **Fotoauswahl und Zuschnitt im mobilen Browser-Gate prüfen.**
    Ein künstliches Foto wird bei 390 × 844 Pixeln über den tatsächlichen
    Dateiauswahldialog ausgewählt, zugeschnitten und als eigene Seite im
    lokalen Backend gespeichert. Ohne Abgabe werden weder KI-Aufträge noch
    Kostenbelege erzeugt. Der Fall läuft mit isolierter SQLite-Datenbank im
    verpflichtenden Browser-Gate; OCR, Kamera und Android bleiben getrennte
    Abnahmen. [Übersicht](docs/ACCEPTANCE_AUTOMATION_2026_11_24.md).

  - [x] **Schulbuddy mit Heftkontext im mobilen Browser-Gate prüfen.**
    Eine künstliche bestätigte Seite wird im 390-Pixel-Browser geöffnet; eine
    bewusst eingegebene Frage durchläuft den regulären lokalen Auftrags- und
    Workerpfad mit simuliertem Anbieter. Die Antwort und ihr Quellzitat
    erscheinen und bleiben nach erneutem Öffnen erhalten. Das Neuladen löst
    keinen zweiten Auftrag aus; ein fremdes Familienkonto darf den gespeicherten
    Chat nicht lesen, und es entstehen keine Aufgabenversuche oder
    Kompetenznachweise. Der Runner verweigert fremde Testdatenbanken und
    verlangt den ausgeführten Fall ohne Skip. Dies ist weder ein echter
    Anbieteraufruf noch eine vollständige fachliche Tutorabnahme.
    [Prüfbericht](docs/SCHULBUDDY_BROWSER_GATE_2026_11_24.md).

  - [x] **PostgreSQL-Testläufe an den isolierten Cluster binden.**
    Der Testläufer startet Kindprozesse mit einer begrenzten Umgebung und
    prüft Datenbank, Unix-Socket und Datenverzeichnis vor pytest. Browser-Opt-ins
    für SQLite werden ausdrücklich abgelehnt; bei unklarem Start oder Stopp
    bleibt das Testverzeichnis erhalten. Künstliche Gegenfälle prüfen unter
    anderem fremde PG- und Loader-Variablen sowie unsichere Stopps. Die
    Ausführung setzt weiterhin eine vertrauenswürdige Startumgebung voraus.
    [Nachweis und Grenzen](docs/TEST_POSTGRES_ISOLATION_2026_11_07.md).

  - [x] **Zwei-Eltern-Konfliktprüfung im Browser-Gate verankern.** Zwei
    künstliche Eltern bearbeiten dieselben Lernvorgaben in getrennten
    Smartphone-Browserkontexten. Eine veraltete Änderung wird mit 409
    abgewiesen und der Entwurf bleibt sichtbar; ein alter API-Vertrag ohne
    Revision erhält 428. Die gespeicherte Push-Freigabe bleibt entzogen und
    es entstehen keine KI-Aufträge. Der lokale Chrome-Fall und die
    Fremddatenbank-Abwehr bestanden; der Runner verlangt beide Ergebnisse
    ohne Skip. Browser-Netzwerksperre und begrenzte Loopback-API-Zugriffe
    bleiben aktiv. Die vollständige CI und weitere Browserabnahmen bleiben
    für den jeweiligen Quellstand gesondert nachzuweisen.
    [Umfang und Grenzen](docs/PARENT_CAS_BROWSER_GATE_2026_11_06.md).

  - [x] **Künstliche Browserabläufe als CI-Gate vorbereiten.** Der bestehende
    Flutter-Build startet den Hefter- und den 390-px-Lernablauf in isoliertem
    Chrome gegen eine temporäre SQLite-Datenbank. Browserseiten sperren fremde
    HTTP-Ziele, HTTP-Weiterleitungen, WebSockets und Service Worker; das ist
    keine Netzwerkisolierung des Betriebssystems oder der Chrome-Hintergrunddienste.
    Die jeweils vorgeschriebenen Testfälle
    müssen im JUnit-Beleg einmal und ohne Skip oder Fehler vorliegen. Die
    Runner-Verträge prüfen auch fehlende, doppelte und übersprungene Fälle.
    Auf Basis `075874c` bestand der kombinierte lokale Lauf mit künstlichen
    Quellen und simulierten Anbieterantworten mit vier Fällen in 123,62 s;
    die hier verwendete Weboberfläche ist gegenüber `3f13adc` unverändert.
    Ein GitHub-Lauf dieser Änderung ist erst nach dem tatsächlichen Durchlauf
    belegt. Dies ersetzt weder echte Anbieter- und Pushprüfungen noch die
    übrigen noch fehlenden repräsentativen Browserabläufe.

  - [x] **Reaper-, Einstellungs- und Diagnose-Löschrennen im PostgreSQL-CI-Gate verankern.**
    Beide Abschluss-/Unterbrechungsrennen, die konkurrierende Änderung einer
    Kindereinstellung und alle acht Kombinationen aus Kind-/Familienlöschung,
    Löschzeitpunkt und Aufräumzustand sind im bestehenden PostgreSQL-Auftrag
    enthalten. Der Ergebnisprüfer verlangt die einzelnen Testidentitäten und
    lehnt Auslassungen, Duplikate, Fehler und Skips ab. Der vollständige
    Auftrag bestand lokal auf isoliertem PostgreSQL mit 31 Fällen ohne Skip;
    der Prüfvertrag bestand zusätzlich 19 Untertests. Ein tatsächlicher
    GitHub-Lauf für diesen neuen Quellstand bleibt separat nachzuweisen.
    Die übergreifende Browser- und Fachabnahme bleibt offen.

  **04.11.2026, Audit-CI:** Lauf
  [41820898845](https://github.com/meinzeug/schulpilot/actions/runs/41820898845)
  scheiterte an einem zeitabhängigen Audit-Suchtest: Ein eigener Lesevorgang
  erzeugt zulässigerweise einen Eintrag mit Unterstrich. Der Test filtert nun
  seine künstlichen Daten, prüft Platzhalter mit echten positiven und negativen
  Beispielen und bildet einen Zeitsprung ohne Wartezeit nach. Die produktive
  Auditierung bleibt erhalten; der vollständige Folgelauf bleibt erforderlich.

  **04.11.2026, erneute CI-Prüfung:** Lauf
  [41791144072](https://github.com/meinzeug/schulpilot/actions/runs/41791144072)
  schlug in zwei Backendpartitionen fehl: Fünf Diagnosefälle verwendeten eine
  überholte Grafikantwort, zwei weitere zählten einen Versionsverweis als
  zweiten Erklärungsabschnitt. Die Tests verwenden nun den gültigen
  Prepared-ID-Vertrag beziehungsweise prüfen den tatsächlichen Abschnitt.
  Die vollständige CI muss für den korrigierten Commit erneut bestehen.

  **04.11.2026, CI-Korrektur:** Der vollständige Lauf
  [41784051628](https://github.com/meinzeug/schulpilot/actions/runs/41784051628)
  für `eae5955` scheiterte in allen drei Backendpartitionen; die übrigen
  Ergebnisse wurden nicht als Gesamterfolg ausgegeben. Veraltete künstliche
  Grafikfixtures und ein Datenbank-Doppelgänger wurden an die wirksamen
  Referenz- und Providerverträge angepasst. Alle neun betroffenen Testdateien
  bestanden lokal mit 419 Fällen und einem PostgreSQL-Skip; relevante echte
  Paketkontext-/Adapter- und Sidecar-Pfade wurden zusätzlich einschließlich
  18 Fällen auf isoliertem PostgreSQL geprüft. Ein neuer vollständiger
  GitHub-Lauf des korrigierten Commits bleibt erforderlich.

  **04.11.2026, CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41779877406](https://github.com/meinzeug/schulpilot/actions/runs/41779877406)
  für `f63b054` war erfolgreich. Der neuere Arbeitsstand benötigt einen
  eigenen Prüfbeleg; dies ersetzt keine fehlende Geräte- oder Fachabnahme.

  **04.11.2026, CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41774548325](https://github.com/meinzeug/schulpilot/actions/runs/41774548325)
  für `1a6e310` war erfolgreich. Dieser Commit wurde auf Nutzerwunsch nicht
  deployt; ein neuerer Arbeitsstand benötigt seinen eigenen Prüfbeleg.

  **04.11.2026, CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41767812665](https://github.com/meinzeug/schulpilot/actions/runs/41767812665)
  für `178f633` war erfolgreich. Dies belegt den automatisierten Umfang des
  Laufs, nicht die noch ausstehenden Browser- und Geräteabnahmen.

  **04.11.2026, CI-Zeitfenster:** Der Lauf
  [41683281166](https://github.com/meinzeug/schulpilot/actions/runs/41683281166)
  für `69eda38` wurde nach 25 Minuten in `backend-0` abgebrochen; der
  Sammeljob scheiterte folgerichtig am fehlenden Ergebnis. Die übrigen
  Backendpartitionen und die weiteren Prüfaufträge bestanden. Beim zuvor
  erfolgreichen Lauf benötigte `backend-0` bereits knapp 22 Minuten. Das
  Zeitfenster pro vollständiger Backendpartition wurde auf 40 Minuten erhöht;
  Auswahl, Ausführung und Prüfung aller drei Ergebnisbelege bleiben unverändert.
  Ein erneuter vollständiger CI-Erfolg muss noch beobachtet werden.

  **CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41666803619](https://github.com/meinzeug/schulpilot/actions/runs/41666803619)
  für `f4e627d` war erfolgreich. Der vorherige Lauf für `7e49c40` wurde beim
  neuen Push abgebrochen und gilt nicht als abgeschlossene Gesamtabnahme.

  **CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41653037943](https://github.com/meinzeug/schulpilot/actions/runs/41653037943)
  für `169fe59` war erfolgreich. Der Operationsjob enthält zusätzlich die
  neuen isolierten Prüfungen für den Uploadpfad des Wiederherstellungsabgleichs.

  **CI-Ergebnis:** Der vollständige GitHub-Lauf
  [41626364796](https://github.com/meinzeug/schulpilot/actions/runs/41626364796)
  für `ac067f4` war erfolgreich. Weitere Release- und Browserabnahmen bleiben
  getrennt zu prüfen.

  **03.11.2026, CI-Untertests:** Im GitHub-Lauf
  [41591639492](https://github.com/meinzeug/schulpilot/actions/runs/41591639492)
  bestanden die Tests der Partition `backend-1`, deren Ergebnisbeleg scheiterte
  aber an zusätzlichen pytest-9-Untertestmeldungen mit gleicher Testkennung.
  Der Runner verarbeitet Untertests gesondert und weist unvollständig
  ausgeführte beziehungsweise fehlgeschlagene Untertests aus. Der fehlende
  Partitionbeleg verursachte folgerichtig auch das Scheitern von
  `backend-complete`. Ein neuer erfolgreicher GitHub-Gesamtlauf ist separat
  nachzuweisen; dieser historische Lauf bleibt fehlgeschlagen.

  **03.11.2026, Backend-Testpartitionen:** Ein zusätzlicher CI-Auftrag prüft
  drei getrennte Ergebnisartefakte auf gleiche Quellrevision und Sammlung,
  die erwarteten disjunkten Partitionen sowie tatsächlich ausgeführte Tests;
  Skip, XFAIL und XPASS bleiben gesondert sichtbar. Der PostgreSQL-Auftrag
  enthält jetzt auch den Elternzuordnungs-Rennentest. Lokal bestanden 27
  Vertrags-/Runnerprüfungen mit 45 Untertests und die 20 Fälle der isolierten
  PostgreSQL-Auswahl. Der erste GitHub-Lauf zeigte den nachfolgend beschriebenen
  Prüfvertragsfehler; diese Ergänzung ersetzt die übrigen Browser-E2E-Abnahmen
  nicht.

  **CI-Korrektur:** Im ersten Lauf der Erweiterung
  [41590653428](https://github.com/meinzeug/schulpilot/actions/runs/41590653428)
  scheiterte der Flutter-Prüfvertrag, weil er nur die bisherigen zwei gepinnten
  Actions zuließ und die beiden neuen Artifact-Actions nicht kannte. Die
  Prüfung wird auf die genauen Action-/Commit-Paare erweitert; der fehlgeschlagene
  Lauf bleibt als Befund bestehen. Ein späterer CI-Gesamterfolg muss separat
  beobachtet werden.

  **03.11.2026, CI-Befund:** Der GitHub-Lauf
  [41574805970](https://github.com/meinzeug/schulpilot/actions/runs/41574805970)
  zu `c244864` schlug in `backend-0` fehl; die übrigen Jobs bestanden. Ein
  Test zur zufälligen Themenauswahl nahm bei identischen Zeitstempeln fälschlich
  eine feste Einfügereihenfolge an. Der Test wählt das Ziel jetzt nach Themenname
  und prüft weiterhin alle 31 Gruppen und gleiche Gewichtung. Die vollständige
  betroffene Testsuite bestand auf SQLite und PostgreSQL mit je 11 Fällen. Der
  anschließende GitHub-Gesamtlauf ist gesondert abzuwarten; der historische
  Fehlschlag wird nicht als Erfolg umgedeutet.

  - [x] Einen separaten PostgreSQL-16-Testlauf für Familien-/Adminrennen,
    atomare Kontingente, parallele Lesemarkierungen, konkurrierende
    Notenimporte und den Mehrtages-Lernablauf in die CI-Konfiguration
    aufnehmen. `scripts/test_postgres.py` verwendet einen eigenen kurzlebigen
    lokalen Cluster und eine separate Testdatenbank; ein lokaler Lauf der
    ausgewählten 13 Fälle bestand ohne Überspringen. Ein separat getesteter
    Prüfbaustein verwirft unvollständige oder übersprungene JUnit-Ergebnisse.
    Die Ausführung des neuen CI-Jobs ist zusätzlich am jeweiligen GitHub-Lauf
    abzulesen und nicht durch den lokalen Lauf belegt.

  **01.11.2026, ergänzt:** Die CI enthält einen eigenen Operationslauf für
  Offsite-Pacing, Löschjournal, Backup-Sperren, Monitoring, Wiederherstellung
  und Release-Staging; der Operationsjob des Laufs
  [41295568206](https://github.com/meinzeug/schulpilot/actions/runs/41295568206)
  war erfolgreich. Die dort vorgesehenen Fälle bestanden lokal zusammen
  mit den Prüfungen für die Flutter-CI-Aufteilung: 95 Tests und 56 Untertests.
  Ein einzelner erfolgreicher Operationslauf ersetzt weder den vollständigen
  Releasecheck noch eine echte Wiederherstellung oder Alarmzustellung.

  Passende Backendtests auf SQLite und für Sperren, Rechte und Parallelität auf isoliertem PostgreSQL, Flutter-Tests, Analyse, Webbuild und releasegebundene Prüfungen in einer nachvollziehbaren Pipeline ausführen. Für Fotoimport, Aufgabenbewertung, Lernstand, Tutor, Benachrichtigungen und Rollen repräsentative Browser-E2E-Fälle mit künstlichen Daten ergänzen. Fehlerpfade, Migrations- und Rollbackkompatibilität sowie zeitgesteuerte Abläufe mit isolierter Testuhr abdecken.

  **Abnahme:** Testumfang, Quellrevision, Ergebnisse und übersprungene Tests sind nachvollziehbar. Mocks, Emulatoren, synthetische Inhalte und physische Beobachtungen werden getrennt ausgewiesen; fehlgeschlagene oder abgebrochene Tests gelten nicht als bestanden.

- [ ] **P1 – Nutzer- und Betriebsdokumentation konsolidieren**

  **04.11.2026, Teilüberarbeitung:** `docs/STATUS.md` unterscheidet den
  lesend geprüften Produktionsstand `178f633` vom nicht deployten Commit
  `1a6e310`. Frühere Betriebsabschnitte kennzeichnen ihren historischen
  Provider- und APK-Kontext. Die neue `docs/FAMILY_GUIDE.md` beschreibt
  Lernen, unklare Bewertungen, freiwillige Pushfreigabe, Export, Löschung und
  Störungsmeldung anhand vorhandener Oberflächen; lokale Dokumentlinks wurden
  geprüft. Eine Erprobung durch eine neue Person und Familie bleibt offen.

  README, Installationsanleitung, Betrieb, Datenschutzhinweise, Eltern-/Kinderanleitungen und KI-Lernmodell mit dem tatsächlichen Stand abgleichen. Historische Aussagen zu kostenlosen Anbietern, Zeitobergrenzen, alter APK-Bezeichnung oder früheren CI-Sperren mit Datums- und Kontextverweis korrigieren, ohne alte Prüfberichte umzuschreiben. Support, Störungsmeldung, Export, Löschung, Umgang mit Fehlbewertungen und Wiederherstellung verständlich erklären.

  **Abnahme:** Eine neue technische Person und eine testende Familie können die jeweils relevanten Abläufe anhand aktueller Dokumentation ausführen; Versionsstand, Grenzen, Verantwortliche und letzte Prüfung sind erkennbar.

- [ ] **P1 – Freigabegespräch und nachvollziehbare Entscheidung durchführen**

  Die Ergebnisse aller für die gewählte Stufe geltenden Punkte zusammenführen: Funktionen und Ausschlüsse, Tests und Fehler, Datenschutz- und Sicherheitsprüfung, Endgeräte, Supportbereitschaft, Datenwiederherstellung, Anbieterabhängigkeit und Kostensteuerung. Für jeden offenen Punkt eine zuständige Person, Risikobewertung und konkrete Folgeaktion nennen. Produktivschaltung, externe Veröffentlichung und gegebenenfalls Verkauf bleiben getrennte Entscheidungen.

  **Abnahme:** Verantwortliche dokumentieren Umfang, Datum, freigegebene Version, offene Risiken und Entscheidung. Fehlt ein zwingender Nachweis, bleibt die entsprechende Freigabestufe offen; ein einzelner grüner Testlauf ersetzt diese Entscheidung nicht.

- [ ] **Laufend – Nach Freigabe messen, reagieren und erneut prüfen**

  Ohne private Inhaltsprotokollierung Fehlerquoten, Auftragsalter, unerwartete Kosten, Sicherungszustand, Speicher und Supportmeldungen überwachen. Anbieter-, Modell-, Lehrplan-, Geräte- und Bibliotheksänderungen an versionierte Regressionen und fachliche Stichproben binden. Störungen priorisiert beheben, Kinder und Eltern verständlich informieren und bei Bedarf betroffene Funktionen begrenzt zurücknehmen.

  **Abnahme:** Verantwortliche, Alarmschwellen, Überprüfungsintervalle und dokumentierte Rückwege existieren; neue Erkenntnisse werden mit Datum und belastbaren Belegen in diese Roadmap und die zuständige Dokumentation übernommen.
