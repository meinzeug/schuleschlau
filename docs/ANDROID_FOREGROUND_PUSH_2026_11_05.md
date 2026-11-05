# Android: sichtbare Vordergrund-Testnachricht

Am 05.11.2026 wurde ausschließlich das eigene künstliche Demo-Kinderkonto auf
dem dedizierten Android-16-Emulator `emulator-5580` verwendet. Die vorher
installierte APK war Build 241 und die sichtbare Oberfläche zeigte die
Anmeldeseite. Der Prüflauf aktualisierte sie zunächst auf die öffentlich
bereitgestellte Direct-APK `1.38.88+243`: Dateigröße und SHA-256 wurden gegen
das HTTPS-Release-Manifest geprüft, Paket und Zertifikat gegen die lokale
Release-Policy. Die Installation durch Android war erfolgreich.

Für den neu erzeugten synthetischen Haushalt wurde die bereits vorhandene,
auditierte und zeitlich befristete Firebase-Testfreigabe einschließlich der
Elternzustimmung verwendet; die allgemeine Produktionsfreigabe wurde nicht
verändert. Das Kind meldete sich im Emulator an und aktivierte die freiwillige
Geräteregistrierung selbst. Die angezeigte Demo-Markierung, das passende
Kinderkonto, die neu entstandene Android-Geräteregistrierung und deren
zugehörige gültige Sitzung wurden getrennt geprüft.

Bei nachgewiesenem Vordergrundzustand wurde **einmal** der reguläre Knopf „Test
an dieses Gerät senden“ gedrückt. Eine atomare lokale Markierung wurde vor
dem Drücken angelegt und verhindert eine erneute Sendung bei Abbruch. Für die
neue Geräteregistrierung gab es genau einen zuordenbaren Test-Zustellbeleg; die
ausgelesene Zustellkennung blieb über die Statusprüfungen gleich, und FCM nahm
die Sendung an. Der neutrale Hinweis erschien in der App; zusätzlich wurde die
neutrale Nachricht in der Android-Benachrichtigungsansicht tatsächlich gesehen
und als [Screenshot](images/android-foreground-push-2026-11-05.png)
festgehalten. Vor dem Drücken und nach dem Empfang war die App als aktive
Activity erkennbar. Das Gerät wurde deregistriert, die App abgemeldet, der
Haushalt über den regulären Konto-Löschendpunkt entfernt und die privaten
Testzugangsdaten gelöscht. Kein automatisches Retry wurde ausgeführt.

Der Test beweist eine sichtbare neutrale **Testnachricht im Vordergrund auf
diesem Emulator**. Er beweist weder die Nachricht für eine fertige Lernrunde
noch deren direkte Zielnavigation oder herstellerspezifisches Verhalten
physischer Android-Geräte. FCM-Annahme allein wäre kein Sichtbarkeitsnachweis.

Bei einem vorherigen Anlageversuch wurde durch eine fehlerhafte lokale Prüfung
des Demo-Antwortformats ein weiteres Demo-Konto angelegt, bevor dessen
Zugangsdaten gesichert waren. Es erhielt keine zusätzliche Push-Freigabe und
keine Testsendung. Ohne eindeutige Zugangsdaten wurde keine pauschale Löschung
vorgenommen; die synthetische Demo-Berechtigung läuft laut Servercode nach
24 Stunden ab. Der Ablauf ist **kein Nachweis einer vollständigen Löschung**.
Die Fixtureanlage wurde für den erfolgreichen Versuch so korrigiert, dass die
Zugangsdaten vor weiteren Prüfungen mit Dateimodus 0600 gespeichert werden.

Wiederholbare Prüfschranken stehen in `qa/android_push_foreground.py`; der
reguläre Versandmechanismus, der bestehende Sitzungs- und Einwilligungsschutz
sowie die Providerkonfiguration wurden dafür nicht umgangen. Der zugehörige
Guardtest prüft unter anderem die einmalsichere Reservierung und die Ablehnung
mehrdeutiger oder wechselnder Zustellbelege. Er ersetzt keine Endgeräteprüfung.

Für spätere eigene Einzelprüfungen wird die künstliche Familie mit
`qa/prepare_android_push_foreground.py` eingerichtet und mit demselben Programm
und `--cleanup` regulär gelöscht. Der 0600-Fixturepfad lässt sich über
`SCHULPILOT_QA_PUSH_CREDENTIALS` setzen. Eine bestehende Datei verhindert die
Anlage einer weiteren Familie. Nach einer unklaren Antwort auf `/demo` wird
nicht automatisch neu angelegt; ein Abbruch zwischen Servererfolg und Empfang
der Zugangsdaten kann eine anschließende eindeutige Löschung weiterhin
unmöglich machen. `qa/android_push_foreground.py --expected-code <Code>` sendet
den Einzeltest; die permanente Tages-/Build-Sendemarkierung darf nach einem
unklaren Ausgang nicht entfernt werden, um erneut zu senden.
