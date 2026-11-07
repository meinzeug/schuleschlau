# Vorbereitung: SchuleSchlau-Adresse

Stand: 07.11.2026. Das Repository wurde auf `meinzeug/schuleschlau` umbenannt. Release `20261107T211835Z-6325f66` läuft unter `https://schuleschlau.dorfspy.de`; die bisherige Webadresse leitet weiter. Die alte API, Push-Pfade und APK-Adresse bleiben für bestehende Installationen erreichbar.

## Vorbereitete Änderungen

- SchuleSchlau ist der sichtbare App-Name. Namen von Exporten und heruntergeladenen Belegen werden entsprechend angepasst.
- Die App wird für die neue HTTPS-Adresse gebaut. Anmeldungsrücksprünge akzeptieren ausschließlich die ausdrücklich freigegebenen alten und neuen Hosts.
- Zusätzliche Webursprünge werden ausschließlich über eine ausdrückliche, durch Kommas getrennte Operatorliste `PUBLIC_URL_ALIASES` zugelassen. Beliebige Host- oder Origin-Header bleiben unzulässig.
- Der Reverse Proxy bedient die neue Adresse und leitet alte Webaufrufe weiter. Bisherige API-, Download-, Push-Worker- und App-Link-Pfade bleiben erreichbar. Die neue APK-Adresse zeigt auf dasselbe signierte Artefakt; alte Versionen erhalten weiter ihre bisherige, streng geprüfte Updateadresse.
- Android-Anwendungskennung, Signaturschlüssel, Firebase-Projekt, vorhandene Installationen, Quellen-IDs und historische Daten bleiben aus Kompatibilitätsgründen unverändert. Eine geänderte Paketkennung wäre eine separate App und kein Update. Technische Identifikatoren sind nicht der angezeigte Produktname.

## Bereits geprüft

Die fachlich begrenzten Backendtests prüfen explizit erlaubte und fremde Origins sowie die Downloadauswahl für neue, alte und gefälschte Hosts. Fluttertests prüfen erlaubte Rücksprünge und Downloadadressen. Die Proxykonfiguration wurde auf dem Zielserver syntaktisch validiert und mit einem vollständig isolierten künstlichen HTTP-Upstream getestet: alte Webadresse leitet um, alte API und alter APK-Pfad bleiben erreichbar, und der neue APK-Pfad liefert dasselbe Testartefakt. Dies ist noch kein TLS- oder echter Android-Installationstest.

Zusätzlich bestanden 36 Backendtests für Noten, Elternplanung und die Downloadadressen des Domainübergangs. Die Tests verwenden keine echten Familien- oder Kinderdaten.

Nach dem Wechsel antworteten neuer HTTPS-Healthcheck und Google-Status erfolgreich. Im Browser öffnete sich die SchuleSchlau-Anmeldung; der Google-Knopf führte zur Kontoauswahl mit der neuen Rücksprungadresse. Ein vollständiger Google-Login wurde dabei nicht abgeschlossen. Die neue und die alte APK-Adresse lieferten jeweils HTTP 200 mit demselben ETag; die beiden öffentlichen Manifeste verwiesen auf die jeweils passende Adresse und Version. Beide erlaubten Web-Origins erreichten die Eingabevalidierung; ein fremder Origin wurde mit 403 abgewiesen. Eine echte Android-Updateinstallation und eine sichtbare Push-Zustellung auf dem neuen Ursprung sind damit nicht nachgewiesen.

Die Google-Konsole enthält den neuen Namen und die neuen Branding-Links. Die bei der Prüfung tatsächlich angezeigte Google-Kontoauswahl nannte noch den bisherigen Namen; das Google-Überprüfungscenter meldete, dass das konfigurierte Branding Nutzern noch nicht angezeigt wird. Die tatsächliche Veröffentlichung des neuen Google-Brandings bleibt deshalb offen.

## Betriebliche Schritte und offene Nachprüfungen

1. Der vorhandene OAuth-Webclient wurde im bestehenden Google-Projekt um `https://schuleschlau.dorfspy.de` und `https://schuleschlau.dorfspy.de/api/auth/google/callback` erweitert und nach dem Speichern erneut geöffnet. Die alte Adresse bleibt erhalten. Die aktive Serverkonfiguration verwendet die private Clientdatei; diese wurde mit Sicherung ebenfalls um die beiden Adressen ergänzt. Die Ausbreitung bei Google und der echte Anmeldeablauf sind noch zu prüfen.
2. Der bestehende Firebase-Browserschlüssel hat laut Google-Konsole derzeit keine Anwendungseinschränkung; die API-Auswahl besteht bereits. Es wurde keine zusätzliche Beschränkung entfernt. Firebase-Webkonfiguration und tatsächliche Zustellung auf dem neuen Ursprung weiter prüfen; Opt-in und bestehende Rechte erhalten. Die fehlende Website-Einschränkung ist gesondert zu prüfen, bevor sie ohne Kenntnis aller Verbraucher verändert wird.
3. DNS und TLS beider Adressen wurden geprüft. Vor Aktivierung wurden die Betriebskonfiguration gesichert, die Restore-Runtimes auf Server und Offsite-Rechner aus demselben Commit vorbereitet und künstlich geprüft sowie eine echte Serversicherung, ein Offsite-Pull und eine getrennte Wiederherstellungsprobe erfolgreich ausgeführt. Auch nach Aktivierung waren Serversicherung, getrennte Wiederherstellungsprobe und Offsite-Pull erfolgreich.
4. Die Betreiberkonfiguration verwendet `PUBLIC_URL=https://schuleschlau.dorfspy.de`, `PUBLIC_URL_ALIASES=https://schulpilot.dorfspy.de` und `ANDROID_DOWNLOAD_FILENAME=schuleschlau-android.apk`. Eine Sicherung der vorigen Konfiguration liegt auf dem Server. Die alte Adresse ist für API, Downloads, Push-Worker und App-Links weiterhin vorgesehen.
5. Release `1.38.107+262` wurde gebaut, signiert und aktiviert. Weiter offen: In getrenntem künstlichem Konto den vollständigen Google-Flow und die Webanmeldung, neue Installation und Update einer alten signierten APK, Push-Registrierung/Anzeige sowie Weiterleitung fragmentgebundener Anmeldelinks tatsächlich prüfen.
6. Alte technische Kompatibilität nur nach eigenständiger Migrations- und Rückbauprüfung entfernen. Das neue Google-Branding und die Einschränkung des Firebase-Browserschlüssels benötigen getrennte Nachprüfung.
