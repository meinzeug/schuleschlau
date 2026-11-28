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
Marker-Metadaten werden in einer einzelnen SQL-Anweisung gelesen; bei
PostgreSQL `READ COMMITTED` sieht diese Anweisung einen konsistenten
Statement-Snapshot. Das ersetzt weder eine transaktionsübergreifende Version
noch eine Sperre bis zur Veröffentlichung. Der Marker ist weder ein
Beherrschungsurteil noch ein sicherer Hinweis beim späteren Start. Dafür ist ein einheitlicher, atomar aktualisierter
kind-/fachgebundener Evidenzversionszähler über sämtliche Antwort-, Hilfe- und
Korrekturpfade nötig. Dieser muss auch Revisionen, Löschungen, Migrationen und
parallele Transaktionen abdecken. Bewusst keine Sperre aller historischen
Units und keine Änderung oder Überschreibung vorhandener Antworten.

## Inventar der Evidenz- und Sperrpfade (Stand 28.11.2026)

| Pfad | Veränderung und Sperrung | Konsequenz für einen künftigen Zähler |
|---|---|---|
| `learning.answer`, `get_unit` | Antwort und Aktivitäten unter Unit-Sperre; reguläre Sachantworten benötigen nicht durchgängig eine Child-Sperre. Sprachantworten sperren zusätzlich Child. Wiederholungen mit passendem Antwortschlüssel sind idempotent. | Antwort, ggf. Hilfen und Version in derselben Transaktion; Unit vor Child/Zähler. Keine Erhöhung beim Replay oder Rollback. |
| `learning.hint`, `learning.explanation`, `learning_tips` | Hilfe-/Erklärungsaktivitäten für konkrete Unit; Hinweise nutzen einen optionalen idempotenten Schlüssel. | Auch relevante Hilfen und geänderte Unterstützungssemantik erfassen; einen ungelesenen Hinweis nicht als Antwort zählen. |
| `assessments.recheck` über `learning.recheck_answer` | Unit zuerst, anschließend Child; neuer revisionsgebundener `AttemptAssessment` und aktualisierter Ausgangsversuch in derselben Transaktion. | Genau einmal pro neuer Nachbewertung erhöhen; vorhandene Nachprüfung ist Replay. |
| `schulbuddy.process` / `record_help` | Betroffene laufende Units sortiert vor Child sperren; Erklärung als Hilfsaktivität, keine alten Antworten umschreiben. | Alle betroffenen Fachschlüssel sortiert behandeln; bisheriger Marker erfasst nur `hint`, nicht die Tutor-Aktivität `explanation`. |
| `learning_entry.remember_generated` / `QuestionCompetence` | Zuordnung von Aufgaben zu versionierten Kompetenzen beim Erzeugen der Unit. | Änderungen oder Löschung vorhandener Bindungen für bereits beantwortete Aufgaben beachten; neue unbeantwortete Units sind kein Leistungsnachweis. |
| `materials.confirm`, `lock_material_units`, `delete_material` | Beteiligte Units in ID-Reihenfolge vor Child; Seitenrevision und -bestätigung bzw. Löschen beeinflussen referenzierte Quellen. | Alte und neue Fachschlüssel bei Fachwechsel berücksichtigen; Quellen-/Planungsrevision zusätzlich prüfen, Zähler nicht als Ersatz. |
| `worker` Aufbewahrung / Löschung und `unit_erasure` | Löschung alter Units samt abhängigen Antworten bzw. separater Aktivitäten; bestehendes Löschjournal wird fortgeführt. | Dieselbe deterministische Sperrordnung, atomare Zähleränderung und Restore-/Journalbehandlung nachweisen; nicht nur die normalen API-Pfade instrumentieren. |
| `grades.priorities`, `learning_progress.read_ledger`, `learning_guidance.strategies` | Strategie nutzt aktuelle Notenprioritäten und die jüngsten zwei belegten Runden je Fach; Lesepfade erzeugen keine Nachweise. | Notenrevision und sämtliche dort genutzten Zustände gesondert bewachen. Marker/Zähler allein belegen keine vollständige strategische Aktualität. |
| `study_path.process` | Erst Payload/Beobachtung, Anbieteraufruf ohne DB-Sperre; nachher Child-Sperre, erneute Prüfungen, Marker-Vergleich und neue Unit in einer Transaktion. | Solange Antwortpfade nicht alle dieselbe Sperre nehmen, kann ein anderer Unit-Writer nach dem Vergleich committen. Die neue Einzellesung schließt diese Lücke nicht. |

Dieses Inventar ist eine Arbeitsgrundlage und kein Nachweis, dass bereits alle
administrativen, Migrations-, Import- und Wiederherstellungspfade erfasst sind.

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

## Vorsichtiger Hinweis vor einer Runde

Nur im Kinderzugang einer noch nicht begonnenen, unbeantworteten automatischen
Etappe mit eindeutig zuordenbarem abgeschlossenem Auftrag zeigt ein erkannter
Markerunterschied einen vorsichtigen Hinweis. Er blockiert den Start nicht;
der private Marker wird nicht ausgegeben. Ein fehlender, alter oder
mehrdeutiger Marker bedeutet unbekannt, nicht „aktuell“. Der Job kann nach
Ablauf der Aufbewahrung fehlen. Die Anzeige ist deshalb keine Garantie für
Aktualität und beantwortete oder bereits begonnene Runden bleiben unverändert.

Beim ausdrücklichen Start wird der private Marker für eine noch nicht
begonnene Runde direkt vor deren Aktivierung erneut beobachtet. Wenn erst nach
dem Öffnen der Rundenansicht eine Änderung erkennbar wurde, meldet die App sie
kurz und lässt das Kind fortfahren. Der Start löst keine neue KI-Erzeugung aus.
Eine PostgreSQL-Prüfung lässt zwischen Ansicht und Startbeobachtung eine andere
Transaktion eine Antwort speichern. Dies belegt diesen konkreten Fall, keine
Atomarität: Eine spätere Änderung nach der Beobachtung kann weiterhin
unbemerkt bleiben; eine verlorene Startantwort übermittelt den Hinweis nicht
nachträglich an ein anderes Gerät. Nicht interpretierbare historische
Marker-Payloads und ausdrücklich erkannte ungültige Evidenzmetadaten ergeben
für diesen Hinweis „unbekannt“ und blockieren die Runde nicht. Datenbank-,
Berechtigungs- und unerwartete Programmfehler werden nicht verschluckt.
Separat offen: Eine ungültige historische `attempt_number` kann beim Lesen
des Lernstands in `learning_progress.read_ledger` PostgreSQL-`DataError`
auslösen. Isoliert auf PostgreSQL reproduziert: Der Start wird zunächst
committet, anschließend scheitert die Erstellung der Antwort mit HTTP 500;
die Runde bleibt aktiv. Ein nicht endlicher Zeitstempel kann andere
Antwortpfade ebenfalls mit einem `ValueError` unterbrechen. Diese unabhängigen
Pfade sind durch die fehlertolerante Beratungsbeobachtung nicht repariert.

Eine ausdrückliche Neuvorbereitung derselben bereits gespeicherten Etappe ist
noch nicht verfügbar. Der bestehende Generator lehnt eine belegte `unit_id`
ab. Eine neue Version benötigt einen eigenen idempotenten POST, Unit→Child-
Sperrung, unveränderte alte Unit samt Antworten, eine eindeutige und bei
Parallelstarts geprüfte Lernwegverknüpfung, erneute Quellen-/Familien-/Tarif-
und Anbieterprüfung sowie getrennte Kostenreservierung. Das Öffnen der Runde
oder der Hinweis dürfen keine KI starten. Erst nach diesen Prüfungen und
Mehrgeräte-/Fehler-/Erhaltstests darf eine solche Aktion angeboten werden.
