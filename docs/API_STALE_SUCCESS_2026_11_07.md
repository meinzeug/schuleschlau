# Verspätete erfolgreiche Antworten nach Kontowechsel

Die gemeinsame Flutter-API bindet Antworten an den beim Start
erfassten lokalen Kontostand, Token und die Anmeldeabsicht. Ändert sich einer
dieser Werte vor der vollständigen Antwort, wird diese mit `stale_request`
verworfen. Dies gilt für JSON-Anfragen, Foto- und PDF-Uploads, einfache
Byteabrufe und die Profilbild-Endpunkte. Ein bereits gestarteter allgemeiner
Job wird nach einem Kontowechsel nicht mit dem neuen Konto weiter abgefragt.
Der lokale Fehler hat Transportstatus 0, keinen HTTP-Status 409: Ein echter
Versionskonflikt darf daraus nicht abgeleitet werden. Das gilt auch für
Transportfehler nach dem Kontowechsel. Bei einer ausstehenden Leseposition
unterbricht die Ansicht nach dem lokalen Fehler den automatischen Versand;
ein ausdrücklicher lesender Abgleich prüft den Serverstand. Stimmt die
Revision nicht mehr, erfolgt kein automatisches Überschreiben. Auch bei
unveränderter Revision sendet der Leseabgleich nichts erneut; erst eine neue
Bedienaktion kann eine Position speichern. Automatische Laborzustände beim
Wiederöffnen der App zählen nicht als neue Bedienung. Eine Antwort, die erst
nach einem Hintergrundwechsel eintrifft, behält die Ungewissheit für dieselbe
Konto- und Quellenidentität; eine bereits wartende Wiederaufnahme prüft den
Zustand nach dem Sperrwarten und nach dem Lesen erneut.

Ein Request kann auf dem Server bereits abgeschlossen sein; die lokale
Fehlermeldung weist darauf hin und fordert die Prüfung des gespeicherten
Stands. Es wird kein Request automatisch wiederholt. Nicht überholte
Fehlerantworten und ihre 401-Benachrichtigung bleiben erhalten; ein altes Logout
darf bei einem neueren Konto den neuen lokalen Zustand nicht entfernen.

Die Tests verwenden künstliche Konten und simulierte HTTP-Antworten. Sie halten
sechs Transportarten an und ändern Konto, Token oder Anmeldeabsicht vor einer
erfolgreichen Antwort. Der Jobtest prüft, dass kein GET im neuen Konto startet.
Der Bestelltest prüft die unveränderte Idempotenzkennung und die eingefrorene
Frühstartauswahl einer bereits abgesendeten Bestellung. Lesepositions- und
Labortests prüfen angehaltenen Folgeversand, Lebenszykluswechsel und
Revisionskonfliktbehandlung. 47 gezielte VM-Tests einschließlich der beiden
verzögerten Antworten vor und nach Resume bestanden auf dem letzten Stand.
Am 07.11.2026 bestanden 79 VM-Prüfungen einschließlich bestehender
Anmelde-, Abmelde- und Elternplan-Konkurrenzfälle; 68 Prüfungen derselben
Transport-/Anmeldeauswahl bestanden zusätzlich im Flutter-Chrome-Runner.
Die Chrome-Tests verwenden Mocktransporte und sind keine echten Cookie- oder
Mehrtabtests. Chromium benötigte beim Beenden SIGKILL nach SIGTERM.

Der Schutz ist kein serverseitiger Authentifizierungsmechanismus und heilt
insbesondere keinen verspätet vom Browser übernommenen `HttpOnly`-Cookie. Er
deckt nur die genannten gemeinsamen API-Methoden ab, keine direkt verwendeten
HTTP-Clients, Streams, externe Browser, alte Clients oder Daten, die nach
Rückgabe einer Antwort später noch asynchron verarbeitet werden. Aufträge
bleiben selbst für abgewiesene Antworten möglicherweise serverseitig
gespeichert. `WEB_LOGIN_COOKIE_RACE_2026_11_06.md` beschreibt den weiterhin
offenen grundlegenden Fehler.
