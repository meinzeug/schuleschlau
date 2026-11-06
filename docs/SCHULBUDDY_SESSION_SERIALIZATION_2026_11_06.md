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
Dieser Stand schützt nur die genannten Provider- und Sessionzeilen bis zum
Commit; ein paralleler Widerruf der Installationsfreigabe ist damit nicht
serialisiert. Auch ein bereits gestarteter externer Aufruf bleibt unverändert.
Eine weitergehende Absicherung benötigt eine eigene Prüfung der bestehenden
Reihenfolge und tatsächlicher Widerrufspfade.

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
