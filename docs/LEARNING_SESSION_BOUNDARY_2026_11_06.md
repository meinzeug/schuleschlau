# Lernnavigation bei Sitzungswechsel

`openPlanItem` bindet die Auswahl an Benutzerobjekt, Familie und den beim
Start gespeicherten Client-Sitzungstoken. Nach einem asynchronen Quellenabruf
wird diese Bindung vor der Auftragserstellung erneut geprüft; Antworten und
Fehler eines danach abgeschlossenen Starts dürfen nicht in eine andere Sitzung
oder eine verdeckte Route navigieren beziehungsweise dort angezeigt werden.
Die Vorschau des nächsten Lernschritts blendet geladene oder noch eintreffende
Daten nach einem gemeldeten Tokenwechsel aus. Es wird kein zusätzlicher
Auftrag und kein automatischer Wiederholungsversuch ausgelöst.

Künstliche Flutter-Widgettests simulieren einen Tokenwechsel bei gleicher
Benutzer- und Familienidentität während Quellenabfrage und laufendem POST
für Lernrunde, Lernweg und Material. Sie prüfen, dass vor dem POST keine
neue Reservierung erfolgt und nach bereits abgeschicktem POST keine veraltete
Navigation erscheint. Fehler werden bei unveränderter Sitzung weitergegeben,
nach Wechsel nicht in der neuen Sitzung angezeigt. Zudem wird eine bereits
geladene und eine verzögerte Übersicht geprüft. Ein bereits abgesendeter POST
kann durch den Clientwechsel nicht rückwirkend ungesendet werden; die
serverseitige Sitzungs- und Familienprüfung bleibt maßgeblich.

28 künstliche VM-Fälle zur Lernfortsetzung und zum Start aus der Vorbereitung
bestanden; sechs gezielte Fälle zu Sitzungswechseln bestanden ebenfalls im
Chrome-Webrunner. Die Tests simulieren die API und sind kein Nachweis für
einen tatsächlichen Serverwiderruf.

Bei Austausch des gesamten `AppState` löst sich die Lernvorschau nun vom
alten Listener und bindet Konto, Familie und Sitzung neu. Ein alter laufender
Start bleibt an seine ursprüngliche Ansicht gebunden. Der neue Nutzer kann
bereits eine eigene Runde öffnen; ein verspäteter alter Abschluss darf weder
navigieren noch den Ladezustand der neuen Aktion beenden. Zwei künstliche
Widgettests reproduzierten zuvor die leere Vorschau und prüfen nun auch die
beiden überlappenden Startantworten. Die Serverrechte werden weiterhin bei
jeder Anfrage durchgesetzt. Beide gezielten Fälle bestanden auf der VM und im
Chrome-Webrunner; mit der Vorbereitungssuite bestanden 30 VM-Fälle. Der
Test-Chromium wurde nach dem erfolgreichen Lauf beim Beenden durch SIGKILL
gestoppt, nachdem SIGTERM nicht ausreichte.

Ein zusätzlicher VM-Fall prüft, dass die bloße erneute Abfrage der Übersicht
nach Rückkehr eine bereits gestartete Runde bei unverändertem Konto und
unveränderter angezeigter Datenbasis nicht an der Navigation hindert.

Dies erkennt eine Änderung des Client-Tokens. Ein vom Client nicht bemerkter
Wechsel des HttpOnly-Webcookies bei unverändertem Token `null` ist damit nicht
nachgewiesen; separate sitzungsgebundene Browser-/Cookieprüfungen und die
umfassende Geräteabnahme bleiben erforderlich.

Auch eine neue Anmeldeabsicht innerhalb desselben AppState besitzt eine neue
Anmelderevision, selbst wenn das alte Benutzerobjekt und der Webtoken zunächst
gleich bleiben. Lernfortsetzung, Zufallsthema und vorbereitete Runde verwerfen
Ergebnisse laufender Anfragen nach dieser Änderung, bevor sie eine Folgeaktion
auslösen, navigieren oder alte Fehler anzeigen. Ein bereits abgesendeter POST
kann nicht zurückgerufen werden. Ungültig gewordene Status- und Vorschauabrufe
bieten ein bewusstes Neuladen an, statt eine alte Antwort zu zeigen oder von
selbst einen neuen Auftrag auszulösen. Die Tests verwenden künstliche Konten
und simulierten Transport; ein Wechsel des Cookies durch einen anderen Tab
ohne gemeldete Anmeldeabsicht wird davon nicht erfasst.

Die beiden gezielten Tests zu Quellenabfrage und vorbereitetem Rundenstart
schlugen mit dem vorherigen Code fehl: Die Quellenabfrage löste noch einen
POST aus und die fertige Runde wurde noch geöffnet. Mit der Änderung bestanden
beide. Insgesamt bestanden 47 einschlägige Flutter-VM-Fälle und die fünf neuen
Fälle im Chrome-Webrunner. Die fünf Chrome-Fälle simulieren API-Antworten;
sie sind kein Test eines realen Cookie-Wechsels oder Provideraufrufs.
