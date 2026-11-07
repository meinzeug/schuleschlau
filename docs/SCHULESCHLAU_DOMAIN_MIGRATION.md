# Vorbereitung: SchuleSchlau-Adresse

Stand: 07.11.2026. Das Repository wurde auf `meinzeug/schuleschlau` umbenannt. Die öffentliche Anwendung läuft zum Prüfzeitpunkt weiterhin unter der bisherigen Adresse; die neue Adresse ist noch nicht für den regulären Betrieb freigegeben. Die ursprüngliche DNS-Antwort für die neue Adresse zeigte bei der Prüfung auf denselben Server. Ein erfolgreicher HTTPS-Aufruf auf der neuen Adresse war vor der Umstellung noch nicht möglich.

## Vorbereitete Änderungen

- SchuleSchlau ist der sichtbare App-Name. Namen von Exporten und heruntergeladenen Belegen werden entsprechend angepasst.
- Die App wird für die neue HTTPS-Adresse gebaut. Anmeldungsrücksprünge akzeptieren ausschließlich die ausdrücklich freigegebenen alten und neuen Hosts.
- Zusätzliche Webursprünge werden ausschließlich über eine ausdrückliche, durch Kommas getrennte Operatorliste `PUBLIC_URL_ALIASES` zugelassen. Beliebige Host- oder Origin-Header bleiben unzulässig.
- Der Reverse Proxy bedient die neue Adresse und leitet alte Webaufrufe weiter. Bisherige API-, Download-, Push-Worker- und App-Link-Pfade bleiben erreichbar. Die neue APK-Adresse zeigt auf dasselbe signierte Artefakt; alte Versionen erhalten weiter ihre bisherige, streng geprüfte Updateadresse.
- Android-Anwendungskennung, Signaturschlüssel, Firebase-Projekt, vorhandene Installationen, Quellen-IDs und historische Daten bleiben aus Kompatibilitätsgründen unverändert. Eine geänderte Paketkennung wäre eine separate App und kein Update. Technische Identifikatoren sind nicht der angezeigte Produktname.

## Bereits geprüft

Die fachlich begrenzten Backendtests prüfen explizit erlaubte und fremde Origins sowie die Downloadauswahl für neue, alte und gefälschte Hosts. Fluttertests prüfen erlaubte Rücksprünge und Downloadadressen. Die Proxykonfiguration wurde auf dem Zielserver syntaktisch validiert und mit einem vollständig isolierten künstlichen HTTP-Upstream getestet: alte Webadresse leitet um, alte API und alter APK-Pfad bleiben erreichbar, und der neue APK-Pfad liefert dasselbe Testartefakt. Dies ist noch kein TLS- oder echter Android-Installationstest.

Zusätzlich bestanden 36 Backendtests für Noten, Elternplanung und die Downloadadressen des Domainübergangs. Die Tests verwenden keine echten Familien- oder Kinderdaten.

## Vor produktivem Wechsel

1. Der vorhandene OAuth-Webclient wurde im bestehenden Google-Projekt um `https://schuleschlau.dorfspy.de` und `https://schuleschlau.dorfspy.de/api/auth/google/callback` erweitert und nach dem Speichern erneut geöffnet. Die alte Adresse bleibt erhalten. Die aktive Serverkonfiguration verwendet die private Clientdatei; diese wurde mit Sicherung ebenfalls um die beiden Adressen ergänzt. Die Ausbreitung bei Google und der echte Anmeldeablauf sind noch zu prüfen.
2. Der bestehende Firebase-Browserschlüssel hat laut Google-Konsole derzeit keine Anwendungseinschränkung; die API-Auswahl besteht bereits. Es wurde keine zusätzliche Beschränkung entfernt. Firebase-Webkonfiguration und tatsächliche Zustellung auf dem neuen Ursprung weiter prüfen; Opt-in und bestehende Rechte erhalten. Die fehlende Website-Einschränkung ist gesondert zu prüfen, bevor sie ohne Kenntnis aller Verbraucher verändert wird.
3. Neue und alte TLS-Adressen sowie echte DNS-Auflösung prüfen. Vor dem Wechsel eine Sicherung der Betriebskonfiguration erstellen und den bestehenden Backup-/Restore-Guard mit den Zielquellen koordinieren.
4. Betreiberkonfiguration abgestimmt setzen: `PUBLIC_URL=https://schuleschlau.dorfspy.de`, `PUBLIC_URL_ALIASES=https://schulpilot.dorfspy.de`, `ANDROID_DOWNLOAD_FILENAME=schuleschlau-android.apk`. Wechsel und Rückweg müssen bei Fehlern mit der Releaseaktivierung zusammenpassen. Die bestehende Anmelde- und Updatefunktion darf nicht stillschweigend ausfallen.
5. Release sauber bauen, signieren und regulär deployen. In getrenntem künstlichem Konto neue Webanmeldung, Google-Flow, getrennte alte und neue Downloadmanifeste, neue Installation und Update einer alten signierten APK, Push-Registrierung/Anzeige sowie Weiterleitung fragmentgebundener Anmeldelinks tatsächlich prüfen. Zertifikate, Login und Push nicht anhand einzelner Unit-Tests als produktiv funktionsfähig ausgeben.
6. Erst nach den bestandenen Prüfungen die neue Adresse als aktiven Betriebsstand dokumentieren. Alte technische Kompatibilität nur nach eigenständiger Migrations- und Rückbauprüfung entfernen.
