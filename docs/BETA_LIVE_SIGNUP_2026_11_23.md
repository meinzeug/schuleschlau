# Beta-Bewerbung: Zielserver-Stichprobe vom 23.11.2026

Eine eigens erzeugte, ausschließlich dem eingerichteten Betreiber-Testpostfach
zugeordnete Gmail-Plusadresse durchlief auf `schuleschlau.dorfspy.de` die
reguläre Beta-Registrierung. Die tatsächliche E-Mail kam im eigenen Postfach
an; der einmalige Bestätigungslink wurde über die reguläre API eingelöst.
Das künstliche Elternkonto meldete sich an und sah seinen Antrag als `pending`.
Anschließend wurde ein künstliches Kind angelegt und mit eigenem Zugang
angemeldet. Das Elternkonto löschte abschließend die eigene Testfamilie über
den vorgesehenen authentifizierten Kontolöschungsweg; der private lokale
Wiederherstellungsbeleg wurde danach entfernt.

Dieser Lauf nutzte echte HTTPS-API-Aufrufe und echte Mailzustellung; er war kein
Browserlauf. Er verwendete keine Kinderdaten, keine KI-Aufträge und verursachte
keine KI-Kosten. Er enthält insbesondere **keine Adminentscheidung**, keine
Beta-Freigabe und keinen echten Foto-/Lernweg. Der lokal isolierte UI-Lauf in
[BETA_BROWSER_2026_11_23.md](BETA_BROWSER_2026_11_23.md) ergänzt, ersetzt aber
nicht diese fehlende Produktionsprüfung.

## Ergänzung: tatsächliche Beta-Freigabe und Fotoverarbeitung

Eine weitere neu angelegte künstliche Familie wurde nach der tatsächlichen
Mailbestätigung über die reguläre, revisionsgebundene Adminentscheidung für
die Beta freigegeben. Im mobilen Browser wurden zwei künstliche Seiten über
den Dateidialog abgegeben. Die echte Erkennung und Gegenprüfung lasen beide
Seiten; danach wurden sie automatisch bestätigt. Die nachfolgende
Paketerstellung scheiterte jedoch. Der verfügbare Testbeleg erfasst fünf
Anbieteraufrufe mit insgesamt 0,037528 USD gemeldeten Kosten und keinen
unbekannten Kosten für diesen Lauf. Die genaue Ursache des Paketfehlers konnte
aus dem nach der Kontobereinigung verbleibenden Beleg nicht mehr bestimmt
werden. Ein späterer unabhängiger Lauf mit derselben Art künstlicher Seiten
zeigte ebenfalls einen fehlgeschlagenen Paketauftrag: Luna verbrauchte das
konfigurierte Limit von 8.000 nativen Ausgabetokens, davon laut späterem
OpenRouter-Beleg 7.877 Reasoning-Tokens; die Antwort wurde verworfen.
Dieser zweite Lauf erfasste fünf Aufrufe mit 0,035643 USD gemeldeten Kosten.
Der anschließend im mobilen Browser ausdrücklich gestartete Wiederholungsweg
wählte anhand dieses gespeicherten Fehlers wie vorgesehen Sol. Dessen Antwort
war vollständig, fiel aber durch die Aufgabenprüfung: Eine freie Bruchaufgabe
war ohne einen eindeutig angegebenen Faktor oder Teiler mehrdeutig. Das Paket
wurde nicht veröffentlicht. Für den gesamten Lauf einschließlich des einen
Wiederholungsversuchs zeigte die Verbrauchsansicht zunächst sechs Aufrufe und
0,088373 USD an; sämtliche Kosten waren zu diesem Zeitpunkt bekannt. Der
fachliche Fehler ist damit nicht als behoben nachgewiesen. Beide künstlichen
Familien wurden regulär gelöscht. Die jeweils nur für die Prüfung über das
lokale CLI angelegten, auditierten Testadministratoren wurden entfernt; deren
Löschung wurde über das Löschjournal abgesichert.

Ein weiterer automatisierter Versuch scheiterte an der bestehenden
Registrierungsrate; ein Konto wurde dabei nicht angelegt. Der Test wartet bei
künftigen Läufen auf den Abschluss der Gegenprüfung und unterscheidet Fehler
der Paketerstellung von Fehlern beim Lesen der Fotos. Dieser Teilnachweis
ersetzt weiterhin keinen erfolgreich durchgehenden Foto- und Lernablauf.

Das eng begrenzte Prüfwerkzeug `scripts/beta_live_signup_smoke.py` verwendet
nur eine zufällige Plusadresse des konfigurierten eigenen Testpostfachs und
schreibt vor der Registrierung ein privates Wiederherstellungsjournal. Bei
Fehlern bleibt es für `--cleanup` erhalten. Bestätigungscodes, Passwörter und
Adressen werden nicht ausgegeben oder ins Repository geschrieben. Ein später
verifiziertes Konto kann auch bei vorübergehend nicht erreichbarem Testpostfach
gelöscht werden. Das Werkzeug darf niemals auf bereits vorhandene Familien
oder beliebige Postfächer erweitert werden.

Der Browserprüfer `qa/school_day.mjs` unterstützt kostenpflichtige künstliche
Beta-Durchläufe nur mit dem ausdrücklichen Schalter
`--paid-synthetic-approved` und dem privaten Journal genau der erzeugten
Testfamilie. Die beiden abgebildeten Seiten müssen weiterhin die festgelegten
künstlichen Dateien sein. Kostenlose Testläufe behalten ihren bisherigen
Vertrag; unbekannte Kosten werden nicht als null ausgegeben. Der Schalter
genehmigt keine realen Kinderdaten und keine pauschale Änderung bestehender
Kontingente.
