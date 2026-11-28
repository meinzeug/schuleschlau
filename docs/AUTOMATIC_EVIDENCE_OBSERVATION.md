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
