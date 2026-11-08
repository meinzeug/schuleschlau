# Physisches Android-Gerät: erster Abnahmebaustein am 08.11.2026

## Gerät und Stand

Das vom Betreiber angeschlossene Redmi 14C (Modell `2409BRN2CY`) verwendete
Android 14 (API 34), 720 × 1640 physische Pixel und eine Dichte von 320 dpi.
Auf dem Gerät war die bestehende Direct-App `de.dorfspy.schulpilot`, Version
`1.38.110` (Versionscode `265`), installiert. Der SHA-256 der installierten
`base.apk` stimmte mit dem am selben Tag öffentlich abgerufenen Stable-Manifest
von `https://schuleschlau.dorfspy.de/api/app-release` überein:
`89e5dec97a48ce1168bec6b27a643cbe1935e88a2bb98b585138bf88bdebf926`.
Das aktive Serverrelease meldete den Quellstand `089d0a3`; Versionsnummer und
Code entsprechen dem dortigen `app/pubspec.yaml`. Der Hashvergleich belegt
Dateigleichheit zum Manifest, nicht selbständig die Echtheit des Signierschlüssels.

## Beobachteter Ablauf

Die native App wurde auf dem physischen Gerät geöffnet; Startgrafik und
Kinder-Startseite erschienen sichtbar. Ein Android-Aktivitätswechsel zeigte
anschließend den Geräte-Startbildschirm als aktive Oberfläche und danach wieder
die App. Der App-Prozess blieb während dieses Wechsels bestehen. Im zunächst
leeren Schulbuddy-Eingabefeld öffnete sich Gboard und blieb geöffnet. Ein kurzer
synthetischer Text war sichtbar und blieb nach erneutem Wechsel zum
Startbildschirm und Rückkehr im geöffneten Chat erhalten. Die Tastatur war nach
der Rückkehr geschlossen; der Text konnte gelöscht werden. Es wurde nichts
abgesendet. Bei geöffneter Tastatur war die Schaltfläche „Frage senden“ nicht
sichtbar; eine Prüfung des Sendens mit geöffneter Tastatur steht aus.

Im Fotoeinstieg öffneten sich die native Kamera und der Android-Fotoauswähler
jeweils über ihre Schaltfläche. Nach Abbruch mit „Zurück“ erschien wieder die
App. Es wurde kein Foto aufgenommen oder im Auswähler markiert; Zuschnitt und
Upload sind dadurch nicht geprüft.

Die App war bereits im vorhandenen Kinderkonto angemeldet. Es wurden keine
Antworten eingetragen, Nachrichten verschickt, KI-Aufträge gestartet oder
Fotos hochgeladen. Temporäre Screenshots mit sichtbarem Kontokontext blieben
außerhalb des Repositorys und wurden nach der Prüfung gelöscht.

## Grenzen

Dies ist eine enge Einzelgeräteprüfung, keine vollständige Android-Abnahme.
Insbesondere sind Fotoaufnahme und Zuschnitt, weitere Tastaturabläufe, Ausfall des
Netzes und Speicherknappheit, App-Neustart, ein tatsächliches Update sowie
TalkBack und große Schrift durch diese Beobachtung nicht belegt. Auch ein
sichtbarer Firebase-Push oder seine Zielnavigation wurden nicht geprüft.
Der übergeordnete Roadmap-Punkt bleibt offen.

## Nacharbeit zur verdeckten Sendeschaltfläche

Der auf dem Gerät beobachtete Fehler wurde in einem Android-Widgettest mit
360 × 820 logischen Pixeln und eingeblendeter Tastatur reproduziert. Im Code
bleibt der Eingabebereich nun bei ausreichend Platz oberhalb der Tastatur
sichtbar; bei sehr wenig Platz oder großer Schrift bleibt der gesamte Dialog
scrollbar. Der neue Test prüft die erreichbare Sendeschaltfläche; weitere
Tests prüfen kleine Ansichten, großen Text, gleichbleibenden Eingabefokus und
bestehende Schulbuddy-Abläufe. Dies ist noch kein Test der geänderten APK auf
dem Redmi und belegt kein reales Absenden.

Für eine spätere Geräteprüfung wurde ein separater Offline-Testeinstieg unter
`app/qa/schulbuddy_device_main.dart` gebaut. Sein künstlicher Benutzer und
seine API-Antworten liegen ausschließlich im Speicher; es gibt keine echte
Anmeldung. Die Debug-APK wurde mit `syntheticUpdateProbe` und dem separaten
Paketnamen `de.dorfspy.schulpilot.updateprobe` gebaut. Der APK-Build und der
Widgettest des Testeinstiegs waren erfolgreich; die Installation auf dem
Redmi wurde von Android mit `INSTALL_FAILED_USER_RESTRICTED` abgelehnt. Die
Test-App war damit nicht installiert, und die Änderung ist noch nicht auf dem
physischen Gerät nachgewiesen.
