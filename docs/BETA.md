# Beta-Anmeldung und Kostenbelege

Diese Dokumentation beschreibt den implementierten Vertrag; sie belegt weder
ein Deployment noch die Freigabe einer konkreten Installation. Neue
Installationen starten mit geschlossener Beta. Der Betreiber aktiviert
`beta_enabled` revisionsgebunden in den Store-Einstellungen; bestehende alte
Clients, die das Feld nicht senden, bewahren den gespeicherten Wert. Ohne
konfigurierten Bestätigungs-Mailversand lässt sich die Beta nicht öffnen.
`GET /api/store/catalog` zeigt den Beta-Einstieg nur bei aktivierter Beta und
konfiguriertem Mailversand. Verkauf und 30-Tage-Test sind davon unabhängig.

Neue Eltern können sich ausdrücklich mit `beta_requested=true` über die
E-Mail-Registrierung bewerben. Die Antwort verrät nicht, ob eine Adresse schon
registriert ist; für ein vorhandenes Konto entsteht dabei kein weiterer Antrag.
Vorhandene Eltern melden sich an und beantragen die Beta als Familienowner
über `POST /api/families/{id}/beta-application`. Dieselbe Aktion ist bei einem
offenen Antrag wiederholbar, und eine abgelehnte oder widerrufene Bewerbung
kann ausdrücklich erneut eingereicht werden. `GET` auf derselben Route zeigt
den Eigentümern den gespeicherten Status. Google-Neuregistrierung darf eine
Beta-Bewerbung nicht stillschweigend vortäuschen.

Administratoren sehen unter `/api/admin/beta-applications` ausschließlich
Kontometadaten und aggregierte Kosten, keine Aufgaben, Fotos oder Antworten.
Die Liste ist nach Status filterbar und in Seiten von höchstens 50 Bewerbungen
begrenzt. Eine Entscheidung über `POST /api/admin/beta-applications/{id}/decision`
trägt die gesehene Revision; widersprüchliche oder parallele Entscheidungen
werden mit 409 abgewiesen. Freigabe setzt einen aktiven, verifizierten
Eltern-Owner und eine nichtsynthetische Familie voraus. Freigabe, Ablehnung,
Widerruf und ausdrückliche Neuanmeldung sind auditierbar. Die Eltern können
den Status im Elternbereich nachsehen; eine gesonderte Push- oder
E-Mail-Benachrichtigung über die Entscheidung ist derzeit nicht implementiert.

Nur während einer gültigen, bestätigten Freigabe gelten für diese Familie
keine persönlichen KI-Aufruf-/Tages-/Monats-Kostenbudgets; eingestellte
Kindergrenzen bleiben gespeichert und gelten nach Widerruf wieder. Beta-Kosten
laufen über `beta-global:YYYY-MM` und den normalen Familien-/Kindbeleg, ohne
das getrennte globale Limit anderer Familien zu verbrauchen. Jede Reservierung
trägt eine unveränderliche Beta-Markierung; bekannte Anbieterbeträge und
unbekannte Kosten werden getrennt erhalten, später eingetroffene
OpenRouter-Abrechnungsbelege regulär abgeglichen. Die Admin-Betaliste summiert
tatsächlich gemeldete/abgeglichene USD-Beträge, unbekannte Kosten, Token und
Aufrufe je Familie und Modell; Modellauswahl ist auf 50 Gruppen begrenzt und
die Gesamtsumme bleibt vollständig. Eine EUR-Umrechnung ohne belegten Kurs
wird nicht erfunden. Diese Angaben sind keine Rechnung und beweisen keine
pädagogische Wirksamkeit.

Auch in der Beta bleiben ausdrückliche Datenschutz-/Anbieterfreigaben,
Notfallstopp, Sitzungs- und Familienrechte, erlaubte Modellroute, einmalige
Reservierung und technische Schutzmaßnahmen wirksam. Dazu zählen insbesondere
ein aktiver Auftrag pro Kind, begrenzte Wiederholungen und kurze
Überlastschutz-Raten (beispielsweise Schulbuddy 8/min und Heft-Tutor 12/min).
Die längerfristigen KI-Stundenquoten für öffentliche Lernbausteine,
Bildaufträge, Sprachprojekte und Klassenarbeit-Nacharbeit greifen für
freigegebene Beta-Familien nicht. Daher bedeutet „unbegrenzt“ hier keine
unbegrenzte technische Parallelität oder Übergehung von Sicherheitsprüfungen.

Migration `0050` hängt von der Bildmigration `0049` ab und ist additiv. Vor
einer produktiven Aktivierung müssen vorhandene Daten und Konfiguration
gesichert, die Restore-Laufzeit migrations- und releasekompatibel gemacht und
ein Rückweg ohne Verlust von Bewerbungen, Entscheidungen oder Kostenbelegen
geprüft werden. Die Migration verweigert ein automatisches Downgrade; ein
Rollback auf älteren Code nach dem Upgrade benötigt eine ausdrücklich geprüfte
Vorwärtskorrektur bzw. Wiederherstellung unter Beachtung des Löschjournals.
Familienexport enthält den eigenen Bewerbungsstatus; Familien-/Elternlöschung
entfernt den Antrag per Fremdschlüssel. Nur kontrollierte künstliche Konten
für technische End-to-End-Tests verwenden.
