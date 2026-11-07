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

## Vor produktivem Wechsel

1. Im bestehenden Google-Projekt den vorhandenen OAuth-Webclient um `https://schuleschlau.dorfspy.de` und `https://schuleschlau.dorfspy.de/api/auth/google/callback` erweitern; alte Angaben für den Übergang erhalten. Den tatsächlich aktiven verschlüsselten oder dateibasierten Client entsprechend aktualisieren, ohne Geheimnisse auszugeben. Die vorhandene lokale Clientkopie enthielt bei der Prüfung nur den bisherigen Ursprung; allein eine lokale Änderung ist kein Nachweis einer Google-Freigabe.
2. Firebase-Webkonfiguration und tatsächliche API-Schlüsselrestriktionen für den neuen Ursprung prüfen und nur gezielt ergänzen. Opt-in und bestehende Rechte erhalten. Die eingeloggte Browseridentität hatte beim ersten Konsolenaufruf keine Projektberechtigung; die separat vorhandene Operator-CLI-Anmeldung wurde lediglich auf Nutzbarkeit geprüft.
3. Neue und alte TLS-Adressen sowie echte DNS-Auflösung prüfen. Vor dem Wechsel eine Sicherung der Betriebskonfiguration erstellen und den bestehenden Backup-/Restore-Guard mit den Zielquellen koordinieren.
4. Betreiberkonfiguration abgestimmt setzen: `PUBLIC_URL=https://schuleschlau.dorfspy.de`, `PUBLIC_URL_ALIASES=https://schulpilot.dorfspy.de`, `ANDROID_DOWNLOAD_FILENAME=schuleschlau-android.apk`. Wechsel und Rückweg müssen bei Fehlern mit der Releaseaktivierung zusammenpassen. Die bestehende Anmelde- und Updatefunktion darf nicht stillschweigend ausfallen.
5. Release sauber bauen, signieren und regulär deployen. In getrenntem künstlichem Konto neue Webanmeldung, Google-Flow, getrennte alte und neue Downloadmanifeste, neue Installation und Update einer alten signierten APK, Push-Registrierung/Anzeige sowie Weiterleitung fragmentgebundener Anmeldelinks tatsächlich prüfen. Zertifikate, Login und Push nicht anhand einzelner Unit-Tests als produktiv funktionsfähig ausgeben.
6. Erst nach den bestandenen Prüfungen die neue Adresse als aktiven Betriebsstand dokumentieren. Alte technische Kompatibilität nur nach eigenständiger Migrations- und Rückbauprüfung entfernen.
