# Sicherheitsprüfung der erweiterten Lieferkette · 01.11.2026

Dieser Bericht ergänzt die Python- und Pub-Abhängigkeitsprüfung aus
[DEPENDENCY_AUDIT_2026_11_01.md](DEPENDENCY_AUDIT_2026_11_01.md). Er erfasst
Container-Basisimages, Gradle- und Android-Abhängigkeiten, externe
JavaScript-Komponenten sowie die Kern-Systempakete der Produktionsumgebung
und bewertet deren Sicherheits- und Lizenzstatus.

## 1. Container-Basisimages

Der isolierte Codex-Lernworker verwendet ein festes, kryptografisch
gepinntes Container-Basisimage in `workers/codex/Containerfile`:

- **Image:** `python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`
- **Basisbetriebssystem:** Debian 12 (Bookworm) Slim
- **Laufzeitbenutzer:** Nicht-privilegierter Benutzer `worker` (UID 10001, GID 10001)
- **Härtung:** Rootless-Container, privater Unix-Socket, kein Host- oder Netzzugriff
  außerhalb des isolierten Provideradapters; keine Entwicklerschlüssel, kein SSH,
  kein Repositoryzugriff.
- **Sicherheitsstatus:** Das Image ist auf einen unveränderlichen SHA-256-Digest
  gebunden. Die installierten Python-Bibliotheken sind über
  `workers/codex/requirements.lock` festgeschrieben und wurden am 01.11.2026
  OSV-geprüft (`certifi` auf 2026.10.23 aktualisiert).
- **Lizenz:** Debian Free Software Guidelines (DFSG) / Python Software Foundation License.

## 2. Android- und Gradle-Lieferkette

Die native Android-Anwendung wird mit der in `toolchain.json` festgeschriebenen
Toolchain gebaut:

- **Build-System:** Gradle 9.3.1 (Wrapper), Android Gradle Plugin (AGP) 9.1.0,
  Kotlin 2.4.0.
- **SDKs:** Compile-SDK 36, Target-SDK 36, Min-SDK 24.
- **Direkte Android-Laufzeitbibliotheken (`app/android/app/build.gradle.kts`):**
  - `com.google.android.play:app-update:2.1.0`: Ausschließlich im `play`-Flavor
    enthalten; ermöglicht In-App-Updates über Google Play. Lizenz: Apache-2.0.
    Der direkte Distributionsflavor (`direct`) schließt diese Abhängigkeit aus
    und enthält keine APK-Installer-Berechtigungen.
  - `junit:junit:4.13.2`: Reines Testscope (`testImplementation`), nicht im
    Release-APK enthalten. Lizenz: EPL-1.0.
- **Flutter-Plugin-Transitive:**
  Die über Flutter eingebundenen nativen Bibliotheken (`firebase_core`,
  `firebase_messaging`, `flutter_tts`, `flutter_webrtc`) werden über
  die jeweiligen Pub-Locks (`pubspec.lock`) und die Plattformkonfiguration
  kontrolliert. Die Kotlin-Migrationsanforderungen (`android.builtInKotlin=false`)
  sind in `docs/DEPENDENCY_AUDIT_2026_11_01.md` als bekannte Toolchainbeobachtung
  dokumentiert.

## 3. Externe JavaScript-Ressourcen

Die Web-Anwendung liefert eigenen JavaScript-Code aus dem Flutter-Build aus.
Ausdrücklich externe JavaScript-Dateien beschränken sich auf die freiwillige
Firebase-Web-Push-Funktion:

- **Komponenten:**
  - `https://www.gstatic.com/firebasejs/12.19.0/firebase-app.js`
  - `https://www.gstatic.com/firebasejs/12.19.0/firebase-messaging.js`
- **Version:** 12.19.0 (festgelegt in `toolchain.json`).
- **Lizenz:** Apache-2.0.
- **Schutzmechanismus:**
  Die Module werden nicht beim Seitenaufruf geladen. Sie werden erst nach
  ausdrücklicher, dokumentierter Elternfreigabe und kindgebundenem Geräte-Opt-in
  über `app/web/push_bootstrap.js` dynamisch importiert.
- **Content Security Policy:**
  Die CSP im Webserver beschränkt Script- und Connect-Quellen strikt auf
  `https://www.gstatic.com` bzw. die autorisierten Google-FCM-Endpunkte.
  Es werden keine Tracker, Werbeskripte oder unautorisierten CDNs geladen.

## 4. Host-Systempakete (Produktionsserver)

Der Server `schulpilot.dorfspy.de` betreibt die Dienste unter Debian 12
Bookworm. Die relevanten Systempakete und Versionen:

- **Python:** 3.12.3 (unter `/opt/schulpilot/current/venv` und System)
- **PostgreSQL:** 16 (Debian Bookworm PostgreSQL-Paketlinie)
- **Webserver & TLS:** Caddy 2.8.4
- **Dienststeuerung:** systemd 252
- **Aktualisierungsstrategie:** Automatische Sicherheitsupdates über
  `unattended-upgrades` für Debian-Sicherheitsquellen.

## 5. Regelmäßiger Überprüfungsweg

1. **Intervall:** Mindestens quartalsweise (nächster Stichtag: 01.02.2027)
   sowie vor jedem Wechsel von Basisimages, Toolchain-Versionen oder neuen
   externen SDKs.
2. **Methode:**
   - Container-Digests gegen aktuelle Debian-Sicherheitsberichte abgleichen.
   - Gradle- und Maven-Koordinaten über OSV prüfen.
   - Host-Systempakete über das Debian Security Tracker System prüfen.
   - Vollständige CI und isolierte Regressionstests vor Auslieferung ausführen.
3. **Zuständigkeit:** Betreiber / Systemadministration.
