# Rückweg und bereits gestartete alte Release-Bereinigung

Stand: 5. November 2026. Dieser Bericht beschreibt ausschließlich isolierte
synthetische Dateisystemtests und einen möglichen Entwurf. **Es gibt hier keine
neue produktive Rollback-Implementierung und keine neue Rollbackfreigabe.**
Die alte Bereinigung ignoriert den heutigen Lease. Ihr Marker stoppt eine
Bereinigung, die ihre Dateiliste danach erstellt; er entwertet keine bereits
angelegte Liste. Ein Prozessscan oder bloßes Warten beweisen nicht, dass ein
bereits gestarteter oder verzögerter alter Prozess nichts mehr löscht.

Eine untersuchte Möglichkeit wäre, nach gesichertem Marker ein vollständig
geprüftes, neues Rollbackrelease unter einem bis dahin nicht existierenden
Namen zu veröffentlichen. Ein alter Löschplan aus dem vorherigen
Verzeichniszustand kann diesen neuen Namen nicht enthalten. Ein isolierter Test
verwendet die bytegenau referenzierte historische Bereinigung, erstellt ihren
Löschplan vor dem Marker, kopiert danach einen künstlichen Zustand und führt
die bereits geplante Löschung aus: Das Original verschwindet, der neue Name
bleibt erhalten. Das allein beweist weder Vollständigkeit noch Eignung zur
Aktivierung.

Ein zweiter Test zeigt eine entscheidende Lücke: Wird eine Quelldatei vor ihrer
Verzeichnisaufzählung gelöscht, kann `copytree` ohne Fehler und mit vorhandenem
`index.html` und `requirements.lock` enden, obwohl Anwendungsdateien fehlen.
Die synthetische Abnahme des vollständigen Baum-Digests erkennt die Abweichung.
Ein dritter Fall bestätigt, dass der vorhandene Digest-Walker symbolische Links
verwirft; ein künftiger Kopierer muss sie darüber hinaus bereits beim Lesen
vermeiden und vor Prüfung niemals aus privatem Staging veröffentlichen.

Für eine **zukünftige** Implementierung sind mindestens folgende Punkte offen:

1. Zielrelease, Lease und Marker revisionsgebunden erfassen; ausschließlich
   nach Markeranlage in ein privates, eindeutig neues, vor dem alten Löschplan
   nicht vorhandenes Verzeichnis kopieren. Alle Datei-/Verzeichniszugriffe
   müssen Links, Hardlinks, fremde Besitzer und fremde Mounts sicher behandeln.
   Verschwindende Dateien und Fehler bleiben fail-closed.
2. Die Kopie gegen ein tatsächlich vertrauenswürdiges, beim ursprünglichen
   Release signaturgeprüftes Attest prüfen. Der bestehende APK-Attestinhalt
   bindet Backend-/Deploy-/Worker- und Web-Bäume, aber der isolierte Digesttest
   ersetzt keine Prüfung des tatsächlich vertrauenswürdigen APK-Signierers.
   Auch APK, öffentliche Manifestdaten, Commitbindung und das separate
   Repair-Quellarchiv müssen ohne stillschweigende Abschwächung gebunden sein.
   Alte Releases ohne prüfbare Belege dürfen nicht als verifiziert gelten.
3. Den Umgang mit aktivierungsabhängiger virtueller Umgebung, Release-ID,
   Dateirechten und Repair-Diensten festlegen. Die Kopie darf keine auf den
   alten Pfad zeigenden Interpreter-/Skriptpfade übernehmen. Eine mögliche
   Neuerstellung der virtuellen Umgebung muss gepinnte Abhängigkeiten und
   Installationsfehler sicher behandeln.
4. Nur nach vollständiger Prüfung atomar veröffentlichen; konkurrierende
   Deployment-/Prune-Prozesse, Unterbrechung, Platzmangel, Timeout, teilweise
   Kopie und fehlendes Attest isoliert prüfen. Danach Datenbank-/JSON- und
   Betriebsrückweg getrennt prüfen. Ein bloß identisches SQL-Schema ist kein
   Nachweis für die Rückwärtskompatibilität gespeicherter Daten.

Ausführung: `python -m pytest -q scripts/tests/test_rollback_snapshot_feasibility.py`.
Die Tests verwenden keine Produktivdaten und führen keinen produktiven Wechsel,
keinen Restore und keinen Anbieteraufruf aus. Bis eine Lösung alle genannten
Prüfungen erfüllt, bleibt der Roadmap-Hauptpunkt offen; dokumentierte
Betriebsanweisungen zum sicheren Umgang mit alten Bereinigungsläufen bleiben
maßgeblich.
