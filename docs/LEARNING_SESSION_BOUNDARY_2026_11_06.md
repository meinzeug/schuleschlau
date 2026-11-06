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

Dies erkennt eine Änderung des Client-Tokens. Ein vom Client nicht bemerkter
Wechsel des HttpOnly-Webcookies bei unverändertem Token `null` ist damit nicht
nachgewiesen; separate sitzungsgebundene Browser-/Cookieprüfungen und die
umfassende Geräteabnahme bleiben erforderlich.
