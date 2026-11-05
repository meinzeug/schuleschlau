# Begrenzter Demo-Pfad für Lernrunden-Benachrichtigungen

Eine reguläre Lernrunden-Fertigmeldung setzt eine gespeicherte, noch nicht
begonnene Einheit mit gültigen Quellen, Erklärgrafik und gebundener Sitzung
voraus. Bisher schloss sie synthetische Einheiten vollständig aus. Ein
Push-Testknopf sendet dagegen nur eine neutrale Testnachricht mit allgemeinem
Ziel. Damit konnte die echte `/unit/...`-Navigation im ausdrücklich
freigegebenen synthetischen Emulator-Konto nicht durchgängig geprüft werden.

Für die individuell angeforderte **lokal erzeugte** Demo-Ersteinheit gibt es
jetzt eine eng begrenzte Ausnahme: die Familie, das Kind, die Quelle und die
Runde sind synthetisch; die Runde ist die eigene feste Bruch-Demo, hat genau
eine bestätigte unveränderte Demoquelle ohne Foto und gehört zum
abgeschlossenen Einzelauftrag über genau diese Quelle. Für den Auftraggeber
und das Kind muss jeweils eine noch gültige, auf die synthetische Familie
begrenzte Push-Testfreigabe bestehen. Aktive Sitzung, Quellrevision,
Rundenstatus und vollständige Grafik werden wie bisher bei der Belegerstellung
und beim späteren Abruf erneut geprüft. Die Ausnahme gilt nicht für reguläre
Familien, Anbieterinhalte, Wiederholungen, Tagespakete, Elternaufträge oder
abweichende Quellen. Der reguläre Produktions-Push benötigt weiterhin seine
unabhängige Betriebsfreigabe; eine Demo-Testfreigabe schaltet sie nicht ein.

Die feste Demo erhält eine echte quellengebundene Bruchgrafik: Sie zeigt das
im bestätigten Demoheft belegte Beispiel 2/4. Der Text nennt es ausdrücklich
„Beispiel aus dem Demoheft“. Grafiken in Aufgabenerklärungen werden erst beim
Lösungsstand gezeigt. Bestehende Grafik-, Quellen- und Sichtbarkeitsprüfungen
entscheiden, ob die Darstellung tatsächlich bereit ist; fehlen Referenz oder
Beleg, bleibt sie unvollständig und es wird keine Fertigmeldung erfunden.
Die Darstellung verändert keine Aufgabenlösungen oder Lernnachweise.

Dieser Code und seine isolierten Tests beweisen noch **keine** sichtbare
Zustellung oder Navigation im Emulator. Nach Review und Deployment ist dazu ein
neues synthetisches Konto mit explizitem Geräte-Opt-in notwendig; der reale
Abschluss, FCM-Annahme, sichtbare Meldung und das Öffnen genau dieser eigenen
Runde sind einzeln zu beobachten. Keine echte KI wird für diese Demorunde
aufgerufen; eine nachgewiesene Anbietererzeugung ist ein gesonderter Test.
