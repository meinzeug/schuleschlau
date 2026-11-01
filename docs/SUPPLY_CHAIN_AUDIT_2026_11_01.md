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

1. Tatsächliche Gradle-Abhängigkeitsbäume beider Release-Flavors inklusive
   transitiver Maven-Koordinaten und Lizenzen reproduzierbar erfassen. Der
   Pub-Lock allein legt diese nativen Transitiven nicht vollständig fest.
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
