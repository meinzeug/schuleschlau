# Private Evidenzbeobachtung bei automatisch vorbereiteten Etappen

Bei neuen automatischen `study_block`-Aufträgen wird der datensparsame,
fach- und kindgebundene Marker unmittelbar vor und nach dem Anbieteraufruf
verglichen. Eine festgestellte Änderung verwirft die erzeugte Etappe; der
reguläre Kostenbeleg bleibt erhalten. Es folgt kein automatischer Wiederholungsaufruf.
Manuell angeforderte Etappen und ältere Aufträge ohne Kennzeichen behalten ihren
bisherigen Ablauf. Der Marker enthält weder Antwort- noch Aufgabentexte und
wird nur als interne Job-Payload gespeichert, nicht an den Anbieter oder an
API-Clients ausgegeben. Der Aufbewahrungszeitraum entspricht dem des Jobs.

**Grenze:** Der Vergleich ist eine Best-Effort-Beobachtung, keine atomare
Vollständigkeits- oder Aktualitätsgarantie. Nicht alle Antwortpfade sperren das
Kind; eine Antwort kann deshalb zwischen Vergleich und Commit entstehen. Die
mehrteilige Abfrage des Markers kann außerdem eine parallele Änderung nur zum
Teil sehen. Der Marker ist weder ein Beherrschungsurteil noch ein sicherer
Hinweis beim späteren Start. Dafür ist ein einheitlicher, atomar aktualisierter
kind-/fachgebundener Evidenzversionszähler über sämtliche Antwort-, Hilfe- und
Korrekturpfade nötig. Dieser muss auch Revisionen, Löschungen, Migrationen und
parallele Transaktionen abdecken. Bewusst keine Sperre aller historischen
Units und keine Änderung oder Überschreibung vorhandener Antworten.

## Für einen belastbaren Versionszähler noch abzudecken

Die zwei Beobachtungen vor dem Anbieteraufruf umfassen nun auch die
Payload-Erstellung. Wird dort bereits eine Änderung erkannt, wird der Auftrag
vor Versand beendet und die nicht genutzte Reservierung freigegeben. Die
Best-Effort-Grenze nach dem Vergleich bleibt unverändert bestehen.

Die Implementierung eines atomaren Zählers benötigt einen zusammenhängenden
Umbau statt einzelner nachträglicher Updates:

1. **Schreibpfade inventarisieren und auf eine gemeinsame Konvention bringen.**
   Antwort und Hinweis werden in `learning.py` gespeichert, Neubewertungen in
   `assessments.recheck`; Schulbuddy hält Hilfen über `schulbuddy.record_help`
   fest. Die Kriterien von `learning_guidance.strategies` beruhen auf
   `learning_progress.read_ledger` und zusätzlichen Notenprioritäten, nicht
   nur auf dem Marker. Die Unit-Zuordnung in `learning_entry.py`, Änderungen
   von Materialrevisionen/-bestätigung, Quellen- und Unit-Löschungen sowie die
   Aktivitätsbereinigung im Worker müssen ebenfalls berücksichtigt werden.
   Auch ein Fachwechsel müsste das alte und das neue Fach erfassen. Für
   Noten und Quellen bleiben die bestehenden gesonderten Revisionsprüfungen
   notwendig. Bei vielen Quellen/Fächern beteiligte Schlüssel sortieren.
2. **Zähler atomar und privat speichern.** Eine Tabelle mit eindeutiger
   Kombination aus Kind und stabil normalisiertem Fach, Version und Schema-Epoche
   braucht eine Migration für SQLite und PostgreSQL, Lösch-/Exportkonzept und
   einen sicheren einmaligen Rücksetzpunkt für Backups und alte Jobs. Sie darf
   keine Texte enthalten oder als Beherrschungsurteil dienen. Jede relevante
   Änderung und der Zähleranstieg müssen in derselben Transaktion erfolgen;
   Rollbacks und doppelte Idempotenzanfragen dürfen nichts doppelt buchen.
3. **Sperrreihenfolge vorab beweisen.** Bestehende Antworten sperren die Unit,
   andere Pfade zusätzlich das Kind; Quellenlöschung sperrt mehrere Units in
   fester Reihenfolge vor dem Kind. Ein Zähler darf nicht in einem Pfad vor,
   im anderen nach dem Kind gesperrt werden. Vor der Implementierung ist die
   Reihenfolge aller Schreib-, Bereinigungs-, Lösch- und Restorepfade zu
   vereinheitlichen. Datenbanktrigger allein beweisen diese Ordnung nicht und
   können bestehende Child→Zähler-/Zähler→Child-Zyklen erzeugen. Keine Sperre
   darf während des externen Anbieteraufrufs gehalten werden.
4. **Veröffentlichung atomar absichern.** Einen transaktional konsistenten
   Ausgangswert mit dem tatsächlich zusammengestellten Payload verknüpfen;
   nach dem Anbieteraufruf die Rechte, Quellen, Planung und Anbietereinstellung
   erneut prüfen und unter der festgelegten Sperrordnung die unveränderte
   Fachversion bis zum Commit der neuen Unit absichern. Änderungen verwerfen
   nur die neue Generierung, erhalten Kostenbeleg und alle Antworten und
   starten keinen stillen Folgeauftrag. Alte Jobs ohne Versionsbeleg bleiben
   ausdrücklich unbekannt; sie werden nicht rückwirkend als aktuell erklärt.
5. **Mehrgeräte und Betrieb nachweisen.** Auf PostgreSQL parallele Antworten,
   Hinweise, Nachprüfungen, Löschungen und Fachwechsel mit Barrieren vor und
   nach dem Vergleich testen; dieselbe Transaktion zurückrollen, tote Sperren
   und Sperrdauer messen, Fehlversuche/Abrechnung prüfen. Migration,
   Wiederherstellung, Familienisolierung, Legacy-Aufträge, Idempotenz und
   SQLite-Entwicklungstests ergänzen. Erst danach darf ein Start-Hinweis die
   Version als verlässlich verwenden; begonnene/beantwortete Units bleiben
   unverändert.
