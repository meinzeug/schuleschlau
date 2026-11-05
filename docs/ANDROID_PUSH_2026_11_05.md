# Android-Push: Emulatorprüfung vom 05.11.2026

Auf dem eigenen Android-Emulator wurde die signierte Direct-APK 1.38.86+241
mit einem eigens angelegten künstlichen Kinderkonto und zeitlich befristeter
Testfreigabe geprüft. Die Elternfreigabe und die Aktivierung auf dem Gerät
wurden geprüft; für dieses Testgerät wurden die Ruhezeiten über die Oberfläche
auf 00:00–00:00 gestellt. Andere Konten und die globale Push-Freigabe wurden
nicht verändert.

- Vor der ersten Testnachricht waren der Android-Aktivitätszustand STOPPED und
  das Fehlen des App-Prozesses beobachtet. Die reguläre Testnachricht wurde von
  FCM angenommen und im Android-Benachrichtigungsbereich sichtbar. Ihr Antippen
  öffnete die App mit dem richtigen künstlichen Kind.
- Eine zweite Nachricht wurde bei geöffneter App von FCM angenommen. Der
  Android-Aktivitätszustand war im Vordergrund und die neutrale In-App-Meldung
  war sichtbar. Die automatische Prüfung konnte die zusätzliche native
  Android-Benachrichtigung im Vordergrund nicht bestätigen. Ein Prüflauf
  schließt daher mit einem Fehler; die Anzeige darf nicht als belegt gelten.
- Die Testgeräteregistrierung wurde entfernt und das künstliche Konto über den
  regulären Kontolöschweg gelöscht. Temporäre Zugangsdaten wurden entfernt.

Das Testskript wartet künftig nach dem Öffnen des Benachrichtigungsbereichs
auf dessen Aktualisierung, weil die In-App-Meldung vor dem Abschluss der
nativen Anzeige erscheinen kann. Diese Anpassung ist noch nicht durch eine
weitere Nachricht auf dem Emulator belegt; die Sendemarkierungen für den
einmaligen Tageslauf wurden nicht zurückgesetzt. Auch der direkte Aufruf einer
geschützten Lernrunde per echter Fertigmeldung bleibt gesondert zu prüfen. Ein
Emulator belegt kein herstellerspezifisches Verhalten physischer Geräte.
