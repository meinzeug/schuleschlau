# Übergabe an die nächste Coding-KI

Stand: 1. November 2026. Diese Datei ist eine Arbeitsübergabe, kein Ersatz für die aktuellen Nutzeraufträge oder `AGENTS.md`. Prüfe alle Zustände erneut; insbesondere Server, Git, laufende Jobs und Roadmap können sich inzwischen geändert haben. Keine Zugangsdaten, Tokens, privaten Schülerdaten oder Bildinhalte in diese Datei, Logs oder Git schreiben.

## Auftrag und Arbeitsweise

Der Nutzer möchte die offene `ROADMAP.md` vollständig und nachweisbar abarbeiten, Probleme selbstständig lösen und erledigte Punkte erst nach Erfüllung ihrer gesamten Abnahmekriterien abhaken. Ein physischer Android-Gerätetest ist nach Nutzerwunsch optional; fehlende native Nachweise trotzdem als Grenze benennen. Die Kinderoberfläche soll auf kleinen Bildschirmen klar, verständlich und textarm sein. Ergebnisse wahrheitsgemäß berichten; Teilfortschritte nicht als vollständige Abnahme ausgeben. Den zwischenzeitlich abgebrochenen Auftrag für 100 Lernrunden nicht wieder aufnehmen.

1. `AGENTS.md`, `ROADMAP.md` und für das jeweilige Thema die verlinkten Dokumente vollständig lesen. Nutzerwünsche und geltende Freigaben im Gespräch beachten.
2. Git- und Serverzustand sowie laufende Jobs prüfen, bevor Änderungen erfolgen. Die bestehenden fremden Änderungen erhalten. Keine pauschalen Resets, kein Force-Push und keine geheimen Daten ausgeben.
3. Den nächsten sicher und vollständig bearbeitbaren Roadmap-Punkt auswählen, seine tatsächlichen Abhängigkeiten untersuchen, beheben und angemessen testen. Die Roadmap nur bei vollständig belegter Erfüllung abhaken; ansonsten präzise Teilfortschritte und offene Abnahmeschritte dokumentieren.
4. Änderungen prüfen, gezielt committen und zum vorhandenen Remote pushen. Bei nötigem Deployment Quellenstand, Konfiguration, Sicherung, Migration und Rückweg prüfen; nach dem Deployment tatsächliche Funktionen und Dienste verifizieren. Keine Zustellung, Providerqualität oder Produktionsreife ohne Nachweis behaupten.
5. Kontinuierlich weiterarbeiten, statt nach einem isolierten Teilpunkt stehenzubleiben. Notwendige externe Freigaben oder nicht verfügbare Nachweise klar als solche benennen und unabhängige Arbeit fortsetzen.

## Git und Arbeitsverzeichnis

Das Hauptverzeichnis ist `/home/dennis/schulpilot`, Branch `main`, Remote `origin`. Bei der jüngsten Aktualisierung war `main` auf `534009f`; spätere Commits und den tatsächlichen Stand zuerst prüfen. Im Hauptverzeichnis liegen zwei bereits vorhandene, nicht zu dieser Arbeit gehörende Änderungen:

- `app/pubspec.yaml`, SHA-256 bei Übergabe: `0f1581c5f623adac6a49c7837e7c080fb4c98b82065587db7124c7c3772a0d30`
- `backend/schulpilot/__init__.py`, SHA-256 bei Übergabe: `313b5053897d6953cf386f4157d66d3527e6e161ba497053f9927762482e45e0`

Diese Dateien nicht überschreiben oder ungeprüft committen. Für unabhängige Arbeiten existiert ein separater Worktree unter `/home/dennis/.codex/worktrees/roadmap-recall-verification/schulpilot`. Seinen Branch- und Dateistatus prüfen, bevor er weiterverwendet wird. Einen Fast-forward des Hauptverzeichnisses nur durchführen, wenn die eingehenden Änderungen die beiden lokalen Dateien nicht gefährden; anschließend ihren Inhalt prüfen.

Zu Beginn mindestens `git status --short --branch`, `git log -5 --oneline`, den Status des Worktrees und die aktuellen CI-Ergebnisse prüfen. Nutzeränderungen und gegebenenfalls von anderer Arbeit stammende Dateien erhalten.

## Aktuell laufende Arbeit: Backup-Aufbewahrung

Die letzte Bestandsaufnahme ergab ein serverseitiges Archiv älter als 14 Tage, weil die bisherige Bereinigung nur nach der täglichen Sicherung stattfindet. Die Offsite-Seite wurde in Commit `6f1ef41` verbessert und lokal installiert: Sie überträgt nur noch innerhalb der Frist liegende Archive, prüft Inventar und Prüfsummen und löscht abgelaufene lokale Kopien erst nach erfolgreichem Journal-Transfer und Remote-Bestätigung. Das schließt die serverseitige Aufbewahrungslücke noch nicht.

Der Bereinigungsdienst und sein Fünf-Minuten-Timer sind mit Release `534009f` produktiv. Eine zuvor laufende Offsite-Übertragung wurde regulär beendet; anschließend entfernte die neue, geschützte Prüfung 18 abgelaufene Serverarchive. Nach Aktivierung erstellte der neue Stand eine Sicherung und stellte sie isoliert wieder her. Das Ergebnis enthielt ein authentifiziertes Archiv, das vorhandene Löschjournal und 393 geprüfte Löschjournal-Einträge; Sitzungen waren widerrufen, der KI-Notstopp aktiviert und die Produktionsdatenbank blieb unangetastet. Ein lesender Serverabgleich fand anschließend 366 Archive, keines älter als 14 Tage; der Serverwächter meldete im Trockenlauf keine Fehler. Der Dienst lief manuell mit Status `success`, der Timer war aktiv. Die Frist ist bei Stromausfall, langen Sperren oder fehlenden Nachweisen keine harte Garantie; das System alarmiert bei überfälligen Archiven. Siehe `docs/STORAGE_AND_ALERTS.md`.

Der abschließende Offsite-Abgleich endete erfolgreich: drei neue Archive wurden kopiert, 366 Kopien und ein verschlüsseltes Journal gemeldet. Beide lokalen Timer waren anschließend wieder aktiv; `.erasure-ledger.pending` und `.previous` lagen nicht vor. Der Inhalt der verschlüsselten Journalkopie wurde dabei nicht geprüft. Den tatsächlichen Zustand vor weiteren Eingriffen trotzdem erneut prüfen; keine laufende Übertragung unterbrechen und unklare Transaktionsdateien nicht löschen.

Im Worktree liegt darüber hinaus eine **noch nicht ausgelieferte** Verbesserung von `scripts/watch_public.py`: Liegengebliebene Journal-Transaktionsmarker sollen nach Freigabe der Offsite-Sperre sofort als `offsite_transaction_incomplete` gemeldet werden; ein laufender regulärer Abgleich soll keinen Fehlalarm erzeugen. 62 passende Tests und 28 Untertests bestanden lokal. Änderungen prüfen, vorhandenen Watchdog sichern und nur atomar und koordiniert nach Ende des laufenden Abgleichs installieren; die Konfiguration und privaten Daten nicht ausgeben. Danach einen lesenden Trockenlauf und den Timerzustand prüfen und die Roadmap nur mit vollständigen Nachweisen aktualisieren.

## Nachgewiesener Stand und weitere Prioritäten

- Bei der letzten Zählung waren 19 von 63 übergeordneten Roadmap-Punkten erledigt. Erneut zählen; Unterpunkte nicht mit vollständigen Hauptpunkten verwechseln.
- Der zuletzt geprüfte produktive Stand war Release `534009f` unter `/opt/schulpilot/releases/20261101T193953Z-534009f`; API, Worker und Sicherungs-/Wiederherstellungstimer waren aktiv. Das ist eine historische Beobachtung, keine Garantie für den aktuellen Zustand.
- Der lokale Offsite-Client enthält `6f1ef41`; sein vorheriger Stand wurde unter `/home/dennis/.local/share/schulpilot-operations/backups/pre-6f1ef41/` gesichert. Den tatsächlichen Installationsstand und laufende Timer erneut prüfen.
- Eine isolierte Wiederherstellungsprobe mit Löschjournal und Sitzungswiderruf war erfolgreich. Die belastbare Einhaltung der Aufbewahrungsfrist bei Ausfällen, historische Löschfälle und Spitzenlastmessungen des Speichers sind weiterhin offen. Details: `docs/STORAGE_AND_ALERTS.md` und `ROADMAP.md`.
- Die Android-Laufzeitabhängigkeiten wurden in `c0f096b` für beide Varianten inventarisiert und gegen OSV geprüft. Das ist weder eine vollständige Lieferketten- noch eine Lizenz- oder APK-Inhaltsprüfung. Siehe `docs/SUPPLY_CHAIN_AUDIT_2026_11_01.md` und `docs/dependency-inventory/`.
- Zuvor fälschlich abgehakte Punkte zu Serverbetriebssystem, Android-Installerberechtigung, Aufbewahrung und historischen Notenlöschungen wurden wieder geöffnet. Diese nur anhand neuer, vollständiger Belege schließen.
- Anschließend die übrigen offenen P0-/Sicherheits- und Datenintegritätsarbeiten sowie die pädagogischen, funktionalen und mobilen Abnahmekriterien der Roadmap in sinnvoller Reihenfolge bearbeiten. Bei KI- und Kinderdaten die besonderen Regeln in `AGENTS.md` einhalten; synthetische Tests und echte Nutzerdaten nicht vermischen. Keine Grenzen stillschweigend lockern und keine automatischen Providerwechsel einbauen.

## Nützliche Prüfungen

- CI: `gh run list --limit 5` und `gh run view <ID>`; ein laufender oder abgebrochener Workflow ist kein grüner Gesamtnachweis.
- Lokale Offsite-Timer: `systemctl --user is-active schulpilot-offsite.timer schulpilot-watch-public.timer`.
- Tests aus einem geeigneten Worktree mit der vorhandenen Projektumgebung ausführen; temporäre Testdaten außerhalb von Git halten. Für relevante Änderungen neben gezielten Tests die dokumentierten Integrations- und PostgreSQL-Tests nutzen.
- Serverzugriff erfolgt über den vorhandenen SSH-Alias `dorfspy`; nur erforderliche, datensparsame Statusinformationen ausgeben. Konfigurationen und Sicherungsbestände vor Änderungen prüfen.

Nach jeder abgeschlossenen Arbeitseinheit diese Übergabe aktualisieren, falls sich aktive Arbeiten, Commitstände, produktive Versionen, Risiken oder notwendige nächste Schritte geändert haben.
