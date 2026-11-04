# Erweiterte Lieferkette: Bestandsaufnahme und offene Sicherheitsprüfung

**Korrektur vom 01.11.2026.** Die erste Fassung enthielt falsche Angaben zum
Server und zum Direct-Android-Flavor und bezeichnete eine unvollständige
Bestandsaufnahme als Sicherheitsprüfung. Die folgenden Werte wurden lesend
an der laufenden Installation beziehungsweise im Quellstand `bba83df` geprüft.
Sie belegen keine allgemeine Schwachstellenfreiheit. Der frühere Stand bleibt
in der Git-Historie nachvollziehbar.

## Verifizierte Bestandsangaben

- Der Produktionshost meldet Ubuntu 24.04.5 LTS, System-Python 3.12.3,
  PostgreSQL-Client 16.15, systemd 255 und `/usr/bin/caddy` 2.6.2. Der
  SCHULPILOT-API-Dienst verwendet Python 3.12.3 aus seinem Release-Venv;
  der Caddy-Dienst startet `/usr/bin/caddy`. Das ist keine vollständige
  Bestandsaufnahme aller installierten oder verwendeten Pakete.
- `unattended-upgrades` ist installiert und aktiviert; die gelesene
  APT-Konfiguration aktiviert tägliche Listen- und Upgrade-Läufe und nennt
  unter anderem die Ubuntu-Sicherheitsquellen. Daraus folgt weder, dass jeder
  Lauf erfolgreich war, noch dass alle Komponenten aktuell sind.
- Das Containerfile des Codex-Workers nennt das Basisimage
  `python:3.12-slim-bookworm` mit SHA-256-Digest
  `34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`
  und Benutzer `10001:10001`. Der Digest belegt die Identität des angegebenen
  Basisimages, nicht dessen Sicherheits- oder Lizenzstatus. Das Backend und
  der Worker verwenden eigene Python-Lockdateien; die bereits dokumentierte
  PyPI-/Pub-Prüfung steht in [DEPENDENCY_AUDIT_2026_11_01.md](DEPENDENCY_AUDIT_2026_11_01.md).
- `toolchain.json` nennt Flutter 3.47.7, Gradle 9.3.1, Android Gradle Plugin
  9.1.0, Kotlin 2.4.0 und Firebase JS 12.19.0. Im Gradle-Quelltext ist
  `com.google.android.play:app-update:2.1.0` für den Play-Flavor eingetragen.
  Der Direct-Manifestquelltext enthält ausdrücklich
  `android.permission.REQUEST_INSTALL_PACKAGES` für den direkten Updateweg;
  der Play-Flavor darf diese Berechtigung laut Projektvertrag nicht enthalten.
  Hieraus folgt keine Prüfung des vollständigen tatsächlich gebauten Bundles.
- Der Web-Bootstrap importiert nach dem vorgesehenen Opt-in Firebase-App- und
  Messaging-Module 12.19.0. Der Push-Serviceworker referenziert zusätzlich
  die entsprechenden Compat-Skripte. Die projektbezogene Caddy-Konfiguration
  begrenzt die erlaubten Quellen; Checkout-Seiten besitzen eigene Richtlinien.
  Eine vollständige Analyse transitiv geladener externer Ressourcen und ihrer
  tatsächlich ausgelieferten Bytes ist damit nicht belegt.

## Noch offen für die Abnahme

1. Für die unten erfassten tatsächlichen Gradle-Abhängigkeitsbäume beider
   Release-Flavors die Lizenzen und gegebenenfalls weitere Sicherheitsquellen
   prüfen. Der Pub-Lock allein legt die nativen Transitiven nicht vollständig fest.
2. Basisimage **und** gebautes Workerimage einschließlich OS-Paketen sowie
   die produktiv verwendeten Hostpakete versioniert inventarisieren. Für
   Ubuntu den Ubuntu-Sicherheitsstatus einschließlich zurückportierter Fixes
   und relevanter Paketquellen auswerten; ein reiner Versionsvergleich mit
   Debian oder einer ungeprüften CVE-Liste genügt nicht.
3. Die tatsächlich geladenen Firebase-Ressourcen und mögliche weitere externe
   Laufzeitdateien einschließlich Unterabhängigkeiten, Versionen und Lizenzen
   erfassen; Opt-in und CSP anhand des ausgelieferten Stands prüfen.
4. Gefundene Meldungen mit Quelle, betroffener Version, Laufzeitpfad,
   Bewertung, Maßnahmen und Nachprüftermin festhalten. Eine wiederholbare
   Kontrolle und verantwortliche Betriebsrolle dokumentieren.

Bis zu diesen Nachweisen bleibt der entsprechende Roadmap-Punkt offen.

## Gradle-Laufzeitbäume und Maven-OSV-Abfrage

Am 01.11.2026 wurden im sauberen Release-Worktree auf Git-Stand `96e32a2`
`directReleaseRuntimeClasspath` und `playReleaseRuntimeClasspath` mit dem
lokal vorhandenen Gradle 9.3.1, Java 17 und der gepinnten Flutter-Toolchain
**offline** erfolgreich aufgelöst. Die Releasekonfiguration benötigt beim
Projektsetup die extern hinterlegte Signierungskonfiguration; diese wurde weder
ausgegeben noch in den Bericht übernommen. Es wurde dabei keine APK gebaut.

Die vollständigen, um Buildpfade bereinigten Bäume stehen unter
[Direct](dependency-inventory/gradle-direct-runtime-20261101.txt) und
[Play](dependency-inventory/gradle-play-runtime-20261101.txt): 504
beziehungsweise 508 Baumzeilen einschließlich Wiederholungs- und
Constraint-Markierungen. Die Play-Updatebibliothek erscheint nur im Play-Baum.
Der lokale Abhängigkeitsgraph ist nicht die Analyse des tatsächlich
ausgelieferten APK- oder AAB-Inhalts.

`scripts/extract_gradle_runtime.py` verwirft fehlgeschlagene Gradle-Ausgaben,
unaufgelöste Abhängigkeiten, fehlende Bäume und unerwartete Einträge.
`scripts/audit_maven_osv.py` berücksichtigt aufgelöste Versionen nach
Gradle-Konfliktauflösung, lässt bloße Constraints und lokale Projekte aus und
fragt die 106 unterschiedlichen Maven-Koordinaten beider Bäume über die
[OSV-Batch-API](https://google.github.io/osv.dev/post-v1-querybatch/) ab.
Antwortanzahl und Pagination werden geprüft. Die versionierte
[Einzelabfrage](dependency-inventory/maven-osv-20261101.json) enthält die
Tree-Hashes, den Gerätezeitpunkt, sämtliche abgefragten Koordinaten und die
Ergebnis-IDs: OSV meldete bei dieser Abfrage **keine Treffer**. Das gilt nur
für diesen Datenbestand und diese Datenquelle; es ist weder ein Nachweis der
Sicherheit noch eine Lizenzprüfung. Android-Artefakte, Systempakete,
Container und externe Web-Ressourcen bleiben gesondert zu bewerten.

Zur Wiederholung beide Gradle-`dependencies`-Berichte für die genannten
Konfigurationen erzeugen, mit `extract_gradle_runtime.py` extrahieren und
beide Dateien `audit_maven_osv.py --output <Bericht.json>` übergeben.
Die Tests `scripts/tests/test_extract_gradle_runtime.py` und
`scripts/tests/test_audit_maven_osv.py` prüfen unter anderem fehlgeschlagene
Auflösung, Versionsersetzung, Constraints und unvollständige oder paginierte
OSV-Antworten ohne Netzaufruf.

## Ubuntu-Sicherheits- und Neustartstatus des Zielservers

Eine zusätzliche **lesende** Abfrage von `pro security-status --format json`
am 01.11.2026 meldete 841 installierte Pakete, keine aus den vorhandenen
Paketlisten ermittelten regulären Sicherheitsupdates und 18 ausstehende
`esm-apps`-Updates mit Status `pending_attach`; Ubuntu Pro war laut Ausgabe
nicht verbunden. Unter diesen Paketen sind `caddy` und `podman`: installiert
waren `caddy 2.6.2-6ubuntu0.24.04.3` und
`podman 4.9.3+ds1-1ubuntu0.2`. Ob und wie die ausstehenden
Paketaktualisierungen für diesen Betrieb bezogen und eingespielt werden,
ist noch zu klären. Die Abfrage ersetzt keine Analyse einzelner
Sicherheitsmeldungen, keine vollständige Lizenzprüfung und keine Aktualisierung
der Paketlisten.

Der Server meldete außerdem einen erforderlichen Neustart. Aktiv war Kernel
`6.8.0-138-generic`, während `linux-image-6.8.0-147-generic` bereits installiert
war; auch `libc6` stand in der lokalen Neustartliste. Diese Beobachtung
beweist die Notwendigkeit, den Neustart und betroffene Dienste zu koordinieren,
belegt aber nicht für sich allein, welche konkreten Sicherheitslücken dadurch
betroffen sind. Es wurde weder ein Neustart durchgeführt noch ein Dienst oder
Ubuntu-Pro-Vertrag geändert. Vor einem Neustart Verfügbarkeit und Zuständigkeit
für alle Dienste auf dem gemeinsam genutzten Server sowie Wiederanlauf und
Sicherungen prüfen; anschließend Kernel, Dienste und Gesundheit erneut prüfen.

Der Status `pending_attach` bezeichnet laut [Canonical-Dokumentation](https://ubuntu.com/pro-client/docs/en/v30/explanations/how_to_interpret_the_security_status_command/) ein Paket, dessen angebotenes Update eine verbundene Ubuntu-Pro-Subskription benötigt. [Canonical beschreibt `esm-apps`](https://documentation.ubuntu.com/security/security-updates/esm/) als gesonderte Wartungsquelle für Universe-Pakete. Ob eine konkrete Subskription für diesen Server zulässig, vorhanden oder kostenpflichtig ist, wurde nicht geprüft; weder eine Registrierung noch eine Anbindung oder Änderung der Paketquellen wurde vorgenommen.

## Ergänzende Teilprüfung 04.11.2026

Die tatsächlich veröffentlichte Version des Firebase-Web-Bootstraps und die
zwei fest eingebundenen CDN-Module wurden einschließlich npm-Paketmetadaten,
gezielter OSV-Abfragen und wiederholbarem Prüfskript teilweise geprüft. Umfang,
Hashwerte, Ergebnisse und ausdrücklich ungeprüfte Lieferkettenbestandteile:
[Externe Web-Skripte](EXTERNAL_WEB_SCRIPTS_2026_11_04.md). Die vollständige
Lieferkettenabnahme bleibt offen.
