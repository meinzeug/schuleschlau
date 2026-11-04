# Android-Emulator: Teilprüfung vom 4. November 2026

Die sichtbare Prüfung nutzte einen neu angelegten Android-16-/API-36-Emulator (x86_64, KVM) und die zu diesem Zeitpunkt produktive Direct-APK 1.38.78, Versionscode 233. Android Studio Rabbit 2 wurde von Google geladen und das Archiv gegen die dort veröffentlichte SHA-256-Prüfsumme geprüft. Der Test nutzt ausschließlich neu erzeugte, gekennzeichnete Demo-Familien; keine echten Kinderdaten und keine externen KI-Aufrufe.

Beim ersten vollständigen Android-Start erschien unter erheblicher I/O-Last ein „System UI isn't responding“-Dialog. Nach Neustart des Emulators war dieser Dialog verschwunden und die Anmeldeseite sichtbar. Das belegt weder einen Fehler der SchuleSchlau-App noch eine zuverlässige Startzeit auf realen Geräten.

Beobachteter Ablauf: APK installieren und starten; künstliches Elternkonto anmelden; Prozess neu starten und Familienansicht wiedererlangen; abmelden und künstliches Kind anmelden; Bruchrunde öffnen; „Erst selbst probieren“ wählen; Hilfe aufrufen; Antwort absenden. Die sichtbare Rückmeldung blieb bis „Weiter“ stehen. Der Server zeigte für den Testversuch `correct`, `assisted=true` und einen verwendeten Hinweis. „Weiter“ öffnete die zweite Aufgabe; deren Hilfe ließ sich aufrufen. Nach dem Aufruf lag die Aufgabenzeile durch den Scrollstand teilweise unter dem oberen Rand. Ein Wisch nach unten stellte auf der nächsten Aufgabe die vollständige Frage wieder her. Zwei eigens erzeugte Demo-Familien wurden über den regulären Kontolöschpfad mit HTTP 200 gelöscht; die App-Daten auf dem Emulator wurden gelöscht.

Grenzen: Dies ist ein manueller Teiltest auf einem Emulator, keine vollständige APK-Abnahme. Kamera, Gerätewechsel, Hardware, Hersteller-Energiesparen und physische Geräte wurden hierbei nicht geprüft. Die bestehende automatische Smoke-Prüfung musste wegen geänderter Texte und einer unter Last einmal unzuverlässigen Tastatureingabe angepasst werden; sie wurde nicht komplett erfolgreich erneut durchlaufen. Das Demobeispiel kennzeichnet seine grafische Erklärung als noch nicht vollständig verfügbar und demonstriert keine erfolgreiche KI-Grafikerzeugung.

## Benachrichtigung nach beendetem App-Prozess

Ein weiterer Test auf demselben API-36-Emulator nutzte die produktive Direct-APK 1.38.80, Versionscode 235, und eine neue künstliche Demo-Familie mit zeitlich begrenzter Testfreigabe und Elternzustimmung. Vor dem regulären Testversand wurden das neu registrierte Android-Gerät und die dazugehörige Sitzung dem künstlichen Kinderkonto zugeordnet. Die angezeigte Ruhezeit 20:00–08:00 blieb unverändert; die Prüfung erfolgte außerhalb dieser Ruhezeit.

Vor dem Versand wurden der Activity-Zustand `STOPPED` und das Fehlen des App-Prozesses beobachtet. Genau eine neutrale Testnachricht wurde über den regulären Handler angefordert und von FCM angenommen. Sie war anschließend tatsächlich in der Android-Benachrichtigungsansicht sichtbar; ihr Antippen öffnete die Neuigkeitenansicht und danach die Demo-Kinderstartseite. Das Testgerät wurde im Anschluss deregistriert und die App abgemeldet. Der kontogebundene Gerätenachweis und der zuvor geprüfte künstliche Login ergänzen die sichtbare Demo-Kennzeichnung und den Anzeigenamen; der Anzeigename allein ist kein eindeutiger Identitätsnachweis.

Der Test beweist die beobachtete Hintergrundzustellung einer neutralen **Testnachricht auf diesem Emulator**. Er prüft weder eine Vordergrundzustellung noch die Benachrichtigung für eine tatsächlich fertiggestellte Lernrunde oder deren direkte Zielnavigation. Er ersetzt keinen Nachweis für Gerätemodelle, Hersteller-Energiesparregeln oder physische Android-Geräte.

## Fotoimport auf dem Emulator

Für den Fotoimport wurde ein neu angelegtes reguläres Konto mit ausschließlich künstlichen Testdaten genutzt. Zwei gekennzeichnete Mathe-Testseiten wurden im Android-Systempicker ausgewählt, einzeln zugeschnitten und im eigenen Konto serverseitig gespeichert. Nach ausdrücklichem „Fotos abgeben“ zeigte die App, dass die Fotos gespeichert sind, aber die Erkennung durch das fehlende Aufruf- beziehungsweise Kostenkontingent unterbrochen wurde. Die anschließend ausgelesene Familiennutzung zeigte null Aufrufe; eine Fotoerkennung ist damit nicht belegt.

Die beiden gespeicherten Zuschnitte wurden visuell als künstliche, gekennzeichnete Testseiten geprüft. Ein lokaler Patch ergänzt ausschließlich ihr festes vollständiges Hashpaar für die bereits vorhandene begrenzte Operator-Testfreigabe; gemischte und abweichende Bildsätze bleiben gesperrt. Eine zurückgerollte Vorprüfung mit der bisher produktiven Allowlist lehnte das Paar ab. Ob weitere Bedingungen – insbesondere das Fehlen früherer Aufträge – für dieses bereits verwendete Testkonto erfüllt sind, muss nach Deployment regulär geprüft werden. Bis dahin erfolgen keine weiteren Live-Aktionen.

### Erneuter Lauf auf Version 1.38.81

Nach Deployment von Commit `7aad038` wurden mit einer neuen künstlichen
Testfamilie über den Android-Systempicker zwei Seiten ausgewählt und
zugeschnitten. Die serverseitig gespeicherten Prüfsummen entsprachen dem fest
geprüften Paar. Der begrenzte Operatorzugang wurde vor dem ausdrücklichen
Abgeben erteilt. Die signierte APK 1.38.81 wurde über der vorigen Version
installiert; die Sitzung und der vorbereitete Tag blieben erhalten.

Beide Seiten wurden erkannt und fachlich den Bruchthemen zugeordnet. Die
eingestellte automatische Seitenprüfung übernahm die Ergebnisse nach dem
Gegencheck. Der anschließende Paketauftrag scheiterte jedoch an der
Ausgabelänge. Eine einzige ausdrücklich in der App gestartete reguläre
Wiederholung scheiterte unabhängig davon bei der Schema-Prüfung der zweiten
Aufgabe. Es entstand keine Lernrunde; der Ablauf gilt daher nicht als
bestanden. Sechs Aufrufe kosteten zusammen 0,103482 USD, ohne unbekannte
Kosten. [Technische Diagnose](PACKAGE_VALIDATION_DIAGNOSIS_2026_11_04.md).

Die eigene künstliche Testfamilie wurde regulär gelöscht; private
Zugangsdateien, Appdaten und Testfotos auf dem Emulator wurden entfernt.
Eine Lernrunden-Benachrichtigung und deren Zielnavigation wurden in diesem
erfolglosen Lauf nicht nachgewiesen.
