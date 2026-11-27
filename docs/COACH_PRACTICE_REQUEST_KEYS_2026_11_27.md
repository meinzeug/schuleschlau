# Bewusste Wiederholung einer Anschlussübung

Bei einer ausdrücklich angeforderten Anschlussübung kann die Serverantwort
ausfallen, nachdem der Auftrag angenommen wurde. In diesem Fall soll ein
bewusster erneuter Klick denselben `Idempotency-Key` verwenden. Der Client
behält den Schlüssel nur im Arbeitsspeicher, getrennt von Anzeigeeinstellungen,
und bindet ihn lokal an Kontobjekt, Token, Familie, Kind, Runde und den zuletzt
angezeigten Auftrag. Ein neu angezeigter fehlgeschlagener Auftrag erhält bei
einer weiteren ausdrücklichen Anforderung einen neuen Schlüssel. Alte
Bedienelemente behalten ihre ursprüngliche Bindung. Während ein neuer
Anmeldeversuch läuft, wird kein Anschlussauftrag gestartet.

Das Backend prüft Sitzung, Familie, Quellen und Wiederholungsgrenze weiterhin
selbst. Es bindet eine Wiederholung mit gleichem Schlüssel an den ursprünglichen
Auftrag und übernimmt dessen ursprüngliche Autorisierung; der Client führt
keine automatische Wiederholung aus. Überholte Aktionen bleiben wirkungslos.

## Grenzen

Der Speicher ist nicht geräteübergreifend und überlebt keinen kompletten
App-Neustart. Ein älteres Backend ohne das Feld `practice_job_id` behält sein
bisheriges Verhalten; aus fehlender Auftragsidentität kann kein sicherer
Generationswechsel abgeleitet werden. Die gesonderte Cookie-Race-Untersuchung
bleibt offen. Die Tests verwenden künstliche Aufgaben und HTTP-Antworten;
es wurden keine Lernantworten oder KI-Aufträge erzeugt.

Die Prüfung umfasste 25 lokale Flutterfälle und vier künstliche Fälle im
Chrome-Webrunner. Sie prüft keine reale Anbieterabfrage oder Wiederaufnahme
nach Neustart.
