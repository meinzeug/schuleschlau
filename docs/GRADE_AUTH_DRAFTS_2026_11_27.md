# Notenentwurf und PDF-Vorschau beim Anmeldewechsel

Eine begonnene Anmeldung verbirgt den bisherigen Notenbereich unmittelbar.
Auch ein anschließend ausgewähltes anderes Kind darf während des laufenden
Anmeldevorgangs keine Notendaten laden. Eine bereits offene Notenbearbeitung
oder PDF-Vorschau bleibt im bisherigen Gerät nur im Arbeitsspeicher erhalten,
wird aber hinter einem neutralen Dialog verborgen. Andere Bestätigungen werden
geschlossen. Ein alter Knopf kann nach einem weiteren Anmeldeversuch keine
Bestätigung oder Speicherung auslösen.

Erst nach Abschluss oder Abbruch des Anmeldeversuchs kann der bisherige
Elternzugang die Wiederaufnahme ausdrücklich anfordern. Der Client prüft das
Konto, die vorhandene Sitzung und das serverseitige Schreibrecht für das
betroffene Kind erneut. Eine PDF-Vorschau wird vor dem Wiederöffnen zusätzlich
mit dem gespeicherten Importstand abgeglichen. Ein anderer Kontozugang erhält
keinen Zugriff auf den alten Entwurf. Beim gesperrten Entwurf fragen Schließen und die System-Zurücktaste
vor dem Verwerfen eines ungespeicherten Entwurfs nach.

Ein bereits abgesandter Noten-Speicherauftrag kann trotzdem angenommen worden
sein. Bei unklarem Ergebnis bleiben Entwurf, ursprünglicher Schlüssel und
Fingerprint erhalten; es wird nicht automatisch erneut gesendet. Für einen
PDF-Import serialisiert das Backend die Bestätigung unter Kind- und
Notensperren und akzeptiert eine Wiederholung desselben Inhalts idempotent;
eine abweichende bereits bestätigte Auswahl wird abgewiesen. Die neue
Vorschauprüfung startet weder eine Übernahme noch einen KI-Auftrag.

Der lokale Anmeldestatus unterscheidet ausstehende und beendete Absichten.
Fehlgeschlagene Anmeldungen, Abmeldungen und abgebrochene Demo-/Google-Starts
beenden nur ihre eigene Absicht; ein neuerer Versuch bleibt erhalten. Ein
abgeschlossener erfolgreicher Login wird durch das anschließende Schließen des
Dialogs nicht nachträglich invalidiert. Verdeckte Arbeitsflächen können keine
Tastaturmenüs mehr öffnen, und ein neues Anmeldevorhaben schließt einen bereits
geöffneten Bereichsdialog.

## Grenzen

Die Prüfung verwendet ausschließlich künstliche Konten, Noten und PDF-Daten.
Sie ersetzt keine Prüfung realer Browser-Cookies, geräteübergreifender
Kontowechsel oder eines echten Datei-Auswahldialogs. Der getrennte Cookie-Race
und die allgemeine Transport- und Datenschutzabnahme bleiben offen. Eine
nachträgliche lokale Sperre kann keine bereits auf dem Server angenommene
Änderung rückgängig machen. Die Elternberechtigung wird unverändert vom
Backend durchgesetzt; der Client stellt keine Berechtigung selbst her.

Der isolierte lokale Testlauf bestand mit 170 künstlichen Fällen. Im
Chrome-Runner bestanden 50 Fälle für Anmeldung, Noten, PDF-Vorschau,
Dateiantworten und Tastaturmenüs. Die PDF-Testdatei liefert dort künstliche
Bytes ohne echten Browser-Dateiauswahldialog. Die statische Dart-Analyse des
betroffenen Codes und der neuen Tests meldete keine Fehler.

Der identische Stand bestand anschließend auch in der Git-Arbeitskopie den
gezielten lokalen Lauf mit 170 Fällen. Der vollständige lokale Flutterlauf
auf Commit `438436d` endete mit 5162 bestandenen und 19 übersprungenen Fällen.
Spätere Commits sind damit nicht als gesamter Stand abgenommen.
