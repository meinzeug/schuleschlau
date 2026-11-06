# Schulbuddy-Aufträge und Sitzungswiderruf

Stand 6. November 2026; ausschließlich künstliche Konten und ein simulierter
Anbieter, keine Produktivdaten oder echte KI-Abfrage.

Vor der Änderung wurden die Sitzung und ihre Familienrechte bei der
Anfrageerstellung und nach dem Anbieteraufruf erneut gelesen, aber nicht bis
zum jeweiligen Commit gegen einen gleichzeitigen Sitzungswiderruf gesperrt.
Ein isolierter PostgreSQL-Test mit angehaltener Widerrufstransaktion zeigte,
dass trotzdem ein Auftrag mit Reservierung bzw. eine Antwort veröffentlicht
werden konnte. Die Tests verwenden die tatsächliche Route, den Worker und
getrennte Datenbanktransaktionen.

Nach der bestehenden Sperre der betroffenen Lernrunde und des Kindes sperrt
der Schulbuddy-Guard den Nutzer zunächst mit `FOR SHARE NOWAIT` und verwendet
danach `lock_session_after_child` für die Sitzung bis zum Commit. Der Nutzerlock
ist nötig, weil eine Turn-Einfügung einen impliziten User-Fremdschlüssellock
braucht, während die Admin-Kontosperre zuerst User und danach Session sperrt.
Eine echte PostgreSQL-Gegenprobe mit dem Admin-Kontosperrendpunkt belegt die
Reihenfolge; ein früherer Aufbau ohne Userlock konnte in einen Deadlock laufen.
Unter PostgreSQL wartet der Guard bei
belegter Sitzung bewusst nicht (`NOWAIT`); der gesamte Schreibvorgang scheitert
kontrolliert. Das ist erforderlich, weil die Annahme eines Familienanrufs die
Session vor dem Kind sperrt. SQLite serialisiert die Schreibtransaktion durch
den bestehenden Update auf dem Kind. Rollen, Familienrechte, Quelle und
Anbieterbindung werden danach weiterhin geprüft.

Ein echter Gerätewiderruf kann während einer bereits abgeschlossenen
Sitzungssperre erst nach deren Commit wirksam werden. Wurde ein Auftrag zuerst
reserviert und vor der Anbieterprüfung widerrufen, verhindert diese Prüfung
die Ausführung; der nicht gesendete Auftrag wird mit null Kosten
abgerechnet. Ein Konflikt nach dem Anbieteraufruf verwirft die Antwort und die
Hilfe; unbekannte Kosten und Reservierung bleiben als `failed_unknown` bestehen.
Es wird keine neue Anfrage automatisch gestartet. Die acht getrennten
PostgreSQL-Fälle prüfen die beiden Konflikt- und beide Commitreihenfolgen sowie
die umgekehrte Sperrreihenfolge bei einem echten Familienanruf. Sie prüfen
außerdem bekannte und unbekannte Kosten, Fehlerstatus und dass keine weiteren
Lernantworten oder Hilfen erzeugt werden.

Dies ist keine Garantie, dass ein zwischen der Prüfung und dem tatsächlichen
Versand eintretender Widerruf eine bereits laufende externe Anfrage nachträglich
zurückholen kann. Der Abschluss prüft die Rechte erneut. Der Test belegt weder
eine allgemeine Modellqualität noch sämtliche möglichen Familien- oder
Provideränderungen und ersetzt keine unabhängige Sicherheitsabnahme.

## Providerrevision und Notstopp vor dem Commit

Eine zusätzliche künstliche PostgreSQL-Gegenprobe zeigte eine eigenständige
Lücke: Zwischen dem letzten Lesen der Anbieterrevision und dem Commit konnte
ein Notstopp aktiviert und trotzdem eine Tutorantwort veröffentlicht werden.
Die Providerzeilen werden jetzt *nach* der Reservierung beziehungsweise
Abrechnung in fester ID-Reihenfolge mit `FOR UPDATE NOWAIT` gesichert;
anschließend wird die bereits kataloggeprüfte Bindung ohne weiteren Katalog-
oder Anbieteraufruf frisch geprüft. Bei Konflikt oder geänderter Einstellung
wird die Transaktion verworfen. Bei Abschluss bleibt ein bereits angefallener
Kostenbeleg über die bestehende Fehlerabrechnung erhalten. Die Reihenfolge
Usage-Buckets vor Providerzeilen ist wesentlich: andere Abrechnungspfade
können bei Kostenüberschreitung ebenfalls nach den Buckets den Notstopp setzen.

Vier PostgreSQL-Fälle prüfen einen zwischenzeitlich bestätigten Notstopp,
belegte Providerzeilen bei Reservierung und Abschluss sowie den wirklichen
Admin-Notstopp, der nur auf die kurze Abschluss-Commitphase wartet. Die
Zeilensperre wird nie über einen externen Modellaufruf gehalten; ein bereits
gestarteter Modellaufruf lässt sich durch den Notstopp nicht zurückholen.
Andere Workerpfade und ein nur durch Prozessabbruch unterbrochener Commit
wurden hier nicht allgemein untersucht.

Ein weiterer Test hält die Providerzeile belegt, während der künstliche
Anbieter einen bekannten Betrag oberhalb der Reservierung meldet. Ein zweiter
prüft einen allein durch belegte Gebühren entstehenden Kinderkostenüberhang.
Beide erreichen den NOWAIT-Guard trotz geänderter Stoppeinstellung, weil der
Worker den Job vor Usage flusht und bis zum Providerlock keinen impliziten
Autoflush zulässt. Nach Freigabe der Zeile verbucht der Fehlerpfad die Kosten
jeweils genau einmal als `failed_billed` und setzt den Notstopp; die Antwort
bleibt verworfen. Die Fehlerabrechnung kann kurz auf eine bereits gehaltene
Providerzeile warten, sie gibt einen tatsächlich bekannten Beleg nicht frei.

`external_allowed` liest zusätzlich die Installations-/Datenschutzfreigabe.
Der zunächst implementierte Stand schützte nur die genannten Provider- und
Sessionzeilen bis zum Commit; die zusätzliche, später geprüfte Serialisierung
der Installationsfreigabe ist im Nachtrag unten beschrieben. Ein bereits
gestarteter externer Aufruf bleibt unverändert.

Die künstliche Gegenprüfung mit dokumentierter Gebühr, bekanntem Preis und
anfangs fehlender Kostenbalance entdeckte einen weiteren Fehler durch den
absichtlich unterdrückten Autoflush: `sync_balance` konnte dieselbe noch nicht
gespeicherte Balance zweimal zum Einfügen vormerken. Die Funktion verwendet
nun eine passende ausstehende Zeile derselben Datenbanksitzung erneut. Ein
normaler Tutor-Erfolg mit Preis und Gebühr wird auf SQLite und PostgreSQL mit
genau einer Abrechnung und einer Balance geprüft. Die Betrags- und
Kontingentregeln bleiben unverändert.

Die vollständige bestehende PostgreSQL-CI-Auswahl wurde um alle 15 neuen
Einzelfälle erweitert. Lokal bestanden die 46 konkret verlangten Fälle ohne
Skip; der JUnit-Prüfer verlangt die Identitäten und lehnt fehlende, doppelte,
fehlgeschlagene und übersprungene Fälle ab. Die Auswahlprüfung bestand mit 34
künstlichen Unterfällen. Darüber hinaus bestanden getrennte PostgreSQL-Läufe
für Tutor und Kostenkontrollen sowie 65 SQLite-Tutor- und 31 SQLite-Kostenfälle.
Ein GitHub-Lauf und ein Deployment sind daraus noch nicht abzuleiten.

## Nachtrag: Widerruf der Installationsfreigabe

Bei zwei künstlichen PostgreSQL-Abläufen wurde nach der bis dahin letzten
Freigabeprüfung der tatsächliche Admin-Widerruf gespeichert, bevor der
Tutorauftrag beziehungsweise die Antwort committen konnte. Vor der Ergänzung
wurde der veraltete Auftrag beziehungsweise die Antwort dennoch übernommen.

Die beiden betroffenen kurzen Datenbanktransaktionen nehmen jetzt nach den
Usage- und Providerzeilen einen `FOR SHARE NOWAIT`-Lock auf Installation und
prüfen die dort hinterlegte Freigabe anschließend erneut. Die Freigabe ist
bis zum Commit gegen paralleles Speichern serialisiert. Bei Konflikt scheitert
die Aktion kontrolliert; es gibt weder eine automatische Wiederholung noch
verlorene Providerkosten. Eine fehlende Installationszeile wird nicht als
Freigabe interpretiert. SQLite verwendet weiterhin die schon durch den
Child-Update gehaltene Schreibtransaktion. Der Inferenzaufruf selbst hält
keine Installationssperre, sodass der Betreiber währenddessen widerrufen kann.

Die PostgreSQL-Gegenproben verwenden den echten Admin-Speicherweg: Widerruf
vor dem Guard, umgekehrte Commitreihenfolge, Widerruf während künstlich
angehaltener Inferenz und Konflikt mit gehaltener Installationszeile. Ein
separater umgekehrter Installation→Provider-Akteur bestätigt den
kontrollierten NOWAIT-Konflikt. Für bekannte und unbekannte Kosten und für
Überhänge durch Anbieterpreis beziehungsweise belegte Gebühren bleiben
Abrechnung und Notstopp erhalten; keine Antwort oder Hilfe wird bei Konflikt
übernommen. Die Bild-, Lernpaket- und sonstigen anderen Workerpfade werden
hierdurch nicht pauschal abgesichert.

Nach Erwerb der Provider- und Installationssperren kann der Kinderpfad noch
Hilfeereignisse und Controllerzustände für laufende Einheiten speichern. Die
Adminänderung kann deshalb länger als eine einzelne SQL-Operation auf den
Abschluss warten; eine feste obere Dauer wurde nicht gemessen. Eine bereits
versandte externe Anfrage lässt sich nicht zurückholen. Ein zwischen zwei
Prüfungen vollständig widerrufener und erneut freigegebener Zustand ist nicht
als eigene historische Freigaberevision an den Auftrag gebunden. Diese Tests
beweisen keine globale Deadlockfreiheit oder fachliche KI-Qualität.

Die elf neuen Prüfungen sind in der verbindlichen PostgreSQL-CI-Auswahl und
ihrem JUnit-Identitätsprüfer enthalten. Die vollständige Auswahl bestand lokal
mit 57 Fällen ohne Skip; der Gate-Selbsttest bestand mit 45 Unterfällen. Im
SQLite-Tutorlauf bestanden 67 Fälle, neun PostgreSQL-Sperrtests wurden dort
absichtlich übersprungen. Ein GitHub-Lauf oder produktive Installation ist aus
lokalen Ergebnissen nicht abzuleiten.
