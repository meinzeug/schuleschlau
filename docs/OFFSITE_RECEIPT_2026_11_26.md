# Offsite-Quittung für einen bestimmten Journalstand

Beim bisherigen Transfer konnte nach dem Export und vor der Bestätigung ein
weiterer Löschbeleg im Journal erscheinen. Der Server bestätigte dann die
Sicherung, obwohl der unabhängige Host den älteren Journalstand gespeichert
hatte. Der vorhandene Vergleich der Datenbank-Outbox schließt diese zeitliche
Lücke nicht allein.

Der Export berechnet unter der bestehenden Journalsperre einen HMAC-Beleg aus
dem Journalinhalt und den tatsächlich ausgegebenen verschlüsselten Bytes. Der
Schlüssel bleibt auf dem Server; der Beleg enthält weder Klartext noch einen
unverschlüsselten Journalhash. Der Offsite-Client prüft Format und Hash der
empfangenen Datei und sendet diesen Hash mit dem Beleg beim ACK zurück. Vor
dem Erfolgsmarker prüft der Server Backupidentität, Outbox und den Beleg erneut
unter der Journalsperre. Bei geändertem Journal oder ausgetauschten Bytes wird
das ACK ausdrücklich abgelehnt; der Client stellt die bisherige Kopie und
Erfolgsmarkierung wieder her. Ein nicht eindeutig zuordenbarer SSH-Abbruch
bleibt dagegen zur Betreiberprüfung markiert. Das verschlüsselte SPB1-Format
und die Entschlüsselung bleiben unverändert.

Das Protokoll ist absichtlich nicht rückwärtskompatibel: Ein alter Client
kann beim neuen Server ohne Beleg kein ACK auslösen; ein neuer Client
akzeptiert keinen alten Server ohne Beleg. Vor einem späteren produktiven
Wechsel müssen unabhängiger Pull-Timer und aktive Transfers angehalten und
Server und Offsite-Client koordiniert aktualisiert werden. Anschließend sind
ein echter Abgleich und eine isolierte Wiederherstellung zu prüfen; bei
Abbruch sind vorhandene Transaktionsmarker erst abzugleichen. Keine dieser
Produktivaktionen wurde durch diesen lokalen Test ausgeführt.

Der Test mit künstlichen Dateien führt Serverexport und Clienttransport
zusammen aus, ändert das Journal vor dem ACK und prüft den Erhalt der alten
Kopie; ein erneuter Lauf bestätigt den aktuellen Stand und entschlüsselt ihn
mit AES-GCM. Weitere Regressionen prüfen unvollständige Ausgaben, falsche
Belege, ältere Protokolle und mehrdeutige Abbrüche.

Die Quittung beweist weder eine vollständige historische Löschkette noch
eine serverübergreifende Schreibsperre. Insbesondere kann eine neue
Datenbanktransaktion nach der Outboxabfrage beginnen; externe oder alte
Schreiber müssen separat berücksichtigt werden. Sie ist keine Bestätigung
einer tatsächlich gelungenen Wiederherstellung.
