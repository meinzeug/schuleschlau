# Kinderwege: Browser- und Wiederaufnahmeprüfung vom 24.11.2026

Ein künstliches Konto, ein lokaler FastAPI-Prozess und eine isolierte
SQLite-Datenbank wurden im Chrome-Browser bei 320 × 844, 390 × 844 und
1280 × 844 Pixeln verwendet. Der Browser durfte nur den lokalen Testserver
ansprechen. Eine Testuhr versetzte ausschließlich die künstliche Umgebung über
sechs Lerntage; die Uhr des Rechners oder Servers wurde nicht verändert.
Anbieterantworten und Schulmaterial waren künstlich. Es gab keinen externen
KI-Aufruf und keine echten Kinderantworten.

Die Prüfung bedient die Fachübersicht, die Mathematik-Themenkarte, die
Vorbereitung, die Aufgaben und den anschließenden Rückblick. Die Runden werden
jeweils bewusst gestartet und die Fragen über die Oberfläche beantwortet.
Die Themenkarte und „Freiwillig weiterlernen“ werden jeweils auf allen drei
Breiten zum Start verwendet. Für den freiwilligen Pfad legt die isolierte
Teststeuerung zuvor einen künstlichen gespeicherten Zeitnachweis von 20 Minuten
an; sie misst dafür keine tatsächlich verstrichenen 20 Minuten. Die mobile
Lernwegansicht wird geöffnet und geschlossen, auf breiter Ansicht wird die
aktuelle Position in der Seitenleiste geprüft.
Die eingeklappte Desktop-Navigationsleiste ließ sich im Test nicht über eine
Playwright-Rollenabfrage lokalisieren; ihr sichtbares Symbol wurde an der
festen Testviewport-Position angeklickt. Dies belegt keine vollständige
Tastatur- oder Screenreader-Bedienung dieser Leiste.
Nach der ersten Antwort jedes der ersten drei Tage wird die Seite neu geladen:
Die Rückmeldung bleibt sichtbar und der gespeicherte Versuch bleibt einmalig.
Am ersten Tag öffnet ein zweiter separat angemeldeter Browser dieselbe offene
Rückmeldung. Der spätere künstliche Elternauftrag bleibt unverändert; der
serverseitige Lernstand wird über die simulierten Prüftage nachvollzogen.

Die vormals abgeschnittene Aufgabenangabe im schmalen Lernkopf steht bei
weniger als 360 Pixeln unter den Kopfaktionen. Die Aktionen behalten ihre
48-Pixel-Trefferflächen. Folgende Bilder zeigen ausschließlich Testdaten:

- [Aufgabe bei 320 Pixeln](images/recall-20261124/aufgabe-320.png)
- [Rückmeldung bei 390 Pixeln](images/recall-20261124/rueckmeldung-390.png)
- [Aufgabe bei 1280 Pixeln](images/recall-20261124/aufgabe-1280.png)

38 Flutter-Fälle zum Lernraum und Layout und 72 Fälle zu Fachnavigation,
Rückmeldung und Lernzeit bestanden. Der breitere Browserlauf verwendet den
regulären lokalen Webbuild; 17 Fälle des isolierten Browsergates bestanden.
Der anschließende zusätzliche Klick auf die sichtbare Hauptnavigation wurde
im erweiterten Mehrtagesfall separat erfolgreich wiederholt. Das Testsetup
verweigert eine vorgegebene externe Datenbank. Die Screenshots zeigen einen
früheren Durchlauf desselben Webstands.

Bei einem vorherigen Gate-Lauf schlug der PDF-Browsertest fehl, weil Chrome
einen Antwortkörper nach Navigation nicht mehr bereitstellte. Der Test liest
die Antwort nun im bestehenden lokalen Netzschutz vor der Weitergabe an den
Browser. Der PDF-Fall und danach das gesamte Browsergate bestanden erneut;
separate Netzschutzprüfungen kontrollierten auch fremde Ziele, Umleitungen,
Beobachterfehler und das Ende laufender Anfragen.

Die Prüfung ist keine fachliche Abnahme echter KI-Ergebnisse, kein realer
30-Tage-Alltagstest und kein Test mit Kindern oder einem physischen Gerät. Sie
belegt weder sämtliche möglichen Aufgaben, Unterbrechungen, Bildschirmgrößen
noch einen umfassenden Barrierefreiheitstest. Die Abnahme der Alters- und
Situationsgerechtigkeit, Geräte und Grafikqualität bleibt gesondert offen.
