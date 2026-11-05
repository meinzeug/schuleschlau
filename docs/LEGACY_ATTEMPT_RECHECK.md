# Nachprüfung historischer Antworten

Die ausdrückliche Nachprüfung wählt bei mehreren Antworten dieselbe eindeutig
gespeicherte positive Versuchsnummer für alte und neue Clients. Fehlt eine
Nummer oder ist sie ungültig beziehungsweise doppelt, wird die Nachprüfung mit
HTTP 409 abgelehnt; Antworten, Bewertungen und Anbieteraufträge bleiben dabei
unverändert. Auch historische Antworten mit unterschiedlichen Zeitstempeln
ohne eindeutige Nummern sind davon betroffen. Ihre Reihenfolge ist damit nicht
geklärt. Ein einzelner Versuch bleibt ohne Nummer nachprüfbar.

Der nach einer Nachprüfung neu berechnete Lernstand lässt reine Reflexionsrunden
wie der reguläre Abschluss aus. Bereits bestehende Fehlzählungen werden damit
nicht automatisch rückwirkend repariert.

Weitere Verbraucher historischer zeitgleicher Antworten, etwa
Lernstandsprojektionen, aktive Aufgabenwahl, Hinweise und die Wiederaufnahme
gespeicherter Rückmeldungen, benötigen eine eigene Analyse und Abnahme. Diese
Änderung beansprucht nicht, deren Reihenfolge oder Navigation zu reparieren.
