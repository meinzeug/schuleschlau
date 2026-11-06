# Betriebsentwürfe mit Versionsprüfung speichern

Der Admin-Endpunkt für Betriebseinstellungen erfordert die `site_revision`
des zuletzt bewusst geprüften Stands als `expected_revision`. Die Aktualisierung
prüft und erhöht diese Versionsnummer atomar. Zwei gleichzeitige Änderungen
mit demselben Stand ergeben genau eine erfolgreiche Änderung; die andere
erhält HTTP 409. Auch ein ausdrücklich mitgesendeter veralteter Freigabewert
kann dadurch einen späteren Widerruf nicht ohne erneute bewusste Prüfung
überschreiben. Einstellungen und Revision stammen aus demselben geladenen
Datensatz. Die revisionsgebundene Seitenprüfung teilt die vorhandene Revision.

Alte Clients ohne Versionsnummer erhalten HTTP 409 und können keine Admin-
Betriebseinstellungen speichern; sie müssen aktualisiert werden. Ein neues
Frontend verweigert das Speichern gegen einen alten Server ohne Revisionswert,
statt die fehlende Prüfung still zu umgehen. Der eigene Ersteinrichtungsweg
und das lokale Betriebs-CLI bleiben über ihre bereits getrennte Serialisierung
bedienbar. Der separate KI-Notfallstopp verlangt keine Site-Revision und bleibt
auch nach einem solchen Konflikt erreichbar.

Die Oberfläche hält einen geöffneten Betriebsentwurf an seiner ursprünglichen
Revision fest. Nach einem 409 bleiben Eingaben erhalten; der Nutzer kann den
aktuellen Stand laden, mit dem Entwurf vergleichen und ausdrücklich als neue
Basis bestätigen. Erst ein späterer eigener Speicherklick sendet die Änderung.
Automatische Aktualisierungen und Abschnittswechsel übernehmen keinen neuen
Stand für einen weiterhin abweichenden Entwurf. Eine weitere Zwischenänderung
führt erneut zu 409. Das Entfernen eines gespeicherten Geheimnisses nutzt
dieselbe Versionsprüfung und löscht keine anderen lokalen Entwürfe.

Tests verwenden ausschließlich künstliche Daten: alte und fehlerhafte
Versionen, Widerruf gegen veraltetes Formular, gleichzeitige Änderungen,
GET-Snapshot, Notstopp, Setup- und vorhandene Admin-/Flutterfälle. Der
PostgreSQL-Concurrency-Job verlangt die neuen Einzelfälle im JUnit-Checker.
Echte Server- oder Anbieteraufrufe sind daraus nicht abgeleitet.

Ein zusätzlicher, ausdrücklich gestarteter Chrome-Test nutzte einen getrennt
erstellten älteren Flutter-Webbuild aus dem Stand vor dem Site-CAS und eine
frische lokale SQLite-Installation mit künstlichem Admin. Nach Anmeldung wurde
der alte `main.dart.js` tatsächlich über einen eigenen Service-Worker-Cache
ausgeliefert. Das alte Formular sendete ohne Versionsfeld und erhielt 409;
gespeicherter Name und Revision blieben unverändert. Die gleiche echte
Browsersitzung konnte danach den separaten Notstopp-Endpunkt aufrufen; die
sichtbare Notstopp-Schaltfläche prüft zusätzlich ein Widgettest. Keine
Produktionsdaten, keine externe KI und kein physisches Gerät waren beteiligt.
Der optionale Test akzeptiert nur eine ausdrücklich markierte Kopie des alten
Webbuilds unter `/dev/shm` und verweigert eine externe Testdatenbank.

**Verbleibende Grenze:** Die bestehende Installationsansicht und ihr
Konfliktdialog prüfen die Identität des angemeldeten Nutzers, aber nicht
durchgängig eine zwischenzeitlich begonnene und noch nicht abgeschlossene
Anmeldeabsicht. Der Site-CAS behebt kein solches UI-/Kontowechselrennen. Auch
die übrige Adminabnahme und eine externe Sicherheitsprüfung sind damit nicht
abgeschlossen.
