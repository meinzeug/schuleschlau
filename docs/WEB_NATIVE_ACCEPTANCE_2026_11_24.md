# Web- und Geräteprüfung vom 24.11.2026

## Web

Der vollständige [GitHub-CI-Lauf 45423097373](https://github.com/meinzeug/schuleschlau/actions/runs/45423097373)
bestand für Commit `041d6c823e18f094c433569114ea075ddd5cd3ff` einschließlich
Browsergate, Flutter, Backend, PostgreSQL und Operations.

Der Web-Releasebuild des Arbeitsstands wurde mit der fixierten Flutter-Version
und den CI-Optionen gebaut. Das isolierte Browsergate bestand mit 17 Fällen.
Der Fotoimport wurde mit demselben künstlichen Bild bei 390 × 844 und
1280 × 844 Pixeln über die tatsächliche Dateiauswahl und den Zuschnitt bis zur
lokalen Speicherung bedient. Beim bloßen Auswählen entstanden keine
KI-Aufträge. Auf breiten Ansichten begrenzt die Änderung die eigentliche
Fotoaktionskarte auf 640 logische Pixel; die mobile Aktion bleibt mindestens
260 Pixel breit. Beide Screenshots wurden betrachtet.

Der Testserver liefert die Anwendungs-CSP aus `deploy/Caddyfile.schulpilot`;
Chrome liest unter dieser Richtlinie zusätzlich eine eigene Blob-URL per XHR.
Dies prüft die Browserwirkung der konfigurierten Richtlinie, startet aber
keinen echten Caddy-Proxy. Bei beiden Fotoansichten wird das tatsächliche
Bild der primären Aktion ausgewertet: häufigste Hintergrundfarbe und ein
sichtbarer heller Vordergrund müssen mindestens 4,5:1 erreichen. Dies ist
keine vollständige Kontrast- oder WCAG-Abnahme aller Oberflächen.

Für Bestätigung, Passwortzurücksetzung und Einladung öffnet ein separater
Browserlauf künstliche Einmal-Links bei beiden Breiten, prüft Fokus und
übernommenen Fragmentcode nach Kaltstart, Neuladen und einem neuen Link und
sendet den jeweils neuen Code bewusst an das lokale Backend. Die Codes werden
nicht protokolliert. Vorher meldet sich das künstliche Kind über das Formular
an und wieder ab; danach ist die Sitzung nicht mehr gültig. Keine Mail und
kein Anbieteraufruf verlassen die Testumgebung.

32 Flutter-Fälle zu Links, Fotoansicht und Lernzeit liefen im echten
Chrome-Widgetrunner, darunter doppelte Schrift; ein weiterer Chrome-Fall
prüfte den Erhalt einer Eingabe bei simulierter Tastaturverkleinerung. 19
Kontrast-/Grafikfälle liefen auf der Flutter-VM. Ein früherer Versuch, diese
VM-Dateifixture im Chrome-Runner zu laden, scheiterte an `dart:io` und zählt
nicht als bestandener Webtest. 30 Konten-/Passwortfälle bestanden auf
isoliertem PostgreSQL.

## Android

Ein eigens angelegter Android-36-Emulator mit Google-APIs-Systembild,
1080 × 1920 Pixeln und 420 dpi wurde ohne Hardwaretastatur gestartet. Die
lokal gebaute Debug-APK `1.38.149+304` des geänderten Arbeitsstands wurde nur
in diesem Emulator installiert. Die App startete, das Anmeldefeld nahm
künstlichen Text an und die vollständige Android-Bildschirmtastatur war
sichtbar. Nach Schließen der Tastatur, Home und erneutem Öffnen blieb die
Eingabe erhalten. Es fand keine Anmeldung, kein Pushtest und kein KI-Aufruf
statt; der temporäre Emulator wurde danach gelöscht. Ein zuvor benutztes
Emulatorprofil zeigte lediglich eine schwebende Eingabeleiste; das neue Profil
wurde angelegt, um diese Einschränkung zu überprüfen.

Dies ist keine signierte Release-APK und kein Test eines physischen Geräts.
Der vollständige native Fotoimport und Lernweg wurden in diesem Lauf nicht
wiederholt; frühere Emulatorergebnisse stehen getrennt in
`ANDROID_EMULATOR_ACCEPTANCE_2026_11_04.md`. Android-Systempicker,
Screenreader, sämtliche Bildschirmgrößen, echte Zustellung und fachliche
KI-Qualität bleiben eigenständige Prüfungen. Die Gradle-Ausgabe weist auf die
bestehende zukünftige Kotlin-Plugin-Migration hin.
