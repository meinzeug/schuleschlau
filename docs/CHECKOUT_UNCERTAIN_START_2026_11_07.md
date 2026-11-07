# Frühstart bei unbestätigter Bestellung

Wenn eine Bestellung abgesendet wurde, ihr Ergebnis aber beispielsweise wegen
eines HTTP-503- oder Verbindungsfehlers unbekannt bleibt, bewahrt der Checkout
den ursprünglichen Auftrag samt Schlüssel und Frühstartentscheidung. Die
Frühstartauswahl bleibt dann gesperrt. Eine erneute ausdrückliche Übermittlung
verwendet denselben Auftrag mit denselben Werten; die Anzeige darf nicht eine
abweichende Entscheidung vortäuschen. Die Zahlungsart war bereits gesperrt.
Die Annahme der Vertragsbedingungen kann weiterhin zurückgenommen werden.
Solange der Auftrag unbestätigt ist, bleibt auch das erneute Laden des Tarifs
gesperrt. So wird kein neuer Preis oder Vertragstext neben einem alten,
unverändert zur Wiederholung vorgemerkten Auftrag angezeigt. Bereits zuvor
erhaltene veraltete Bediencallbacks prüfen diese Sperre erneut.

Bei einem tatsächlichen, vom Server beantworteten 409-Konflikt wird der
abgelehnte Bestellentwurf wie bisher verworfen. Die Frühstartauswahl kann
dann wieder geändert werden; ein neuer Auftrag wird dadurch nicht automatisch
ausgelöst. Die vorhandene Erklärung empfiehlt weiterhin, zuerst die
gespeicherten Bestellungen zu prüfen.

Die Widget-Regression verwendet ausschließlich künstliche Konten, Tarife und
HTTP-Antworten. Sie prüft getrennt die ungewisse Antwort 503 und den
abgewiesenen 409-Fall, den eingefrorenen Wert und die vollständig gleiche
erneute Anfrage einschließlich Schlüssel. Sie weist keinen echten
Zahlungseingang, keine E-Mail-Zustellung und keine Livebestellung nach.
