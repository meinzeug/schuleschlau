# Entwurf: vorab geplante Bruchaufgaben in Paketpartitionen

Stand: 6. November 2026. Dies beschreibt einen offenen Implementierungsschritt;
es ist keine Freigabe, kein neuer Lernnachweis und keine Behauptung, dass ein
Paket bereits vorab geplante Bruchaufgaben verwendet.

Die bestehende Erweiterungsdarstellung in `study_fraction_expansions.py`
verlangt eine wörtlich belegte allgemeine Erweiterungsregel und bindet Aufgabe,
Antwort, Faktor, Quell- und Referenzdigest an geprüfte, lokal gerenderte
Bruchgrafiken. Die ursprünglichen Aufrufe bleiben auf Quellen ohne `group_id`
beschränkt. Die internen Beweishelfer können zusätzlich eine ausdrücklich
benannte Gruppe verarbeiten: Eine Grafik darf nur eigene Originalquellen dieser
Gruppe verwenden; kuratierte Quellen und gleichnamige fremde Gruppen bleiben
getrennt. Das aktiviert noch keine Paketplanung.

Für die eigentliche Paketimplementierung müssen die folgenden Schritte
zusammen abgeschlossen werden:

1. Unter den bestehenden Kind-/Quellensperren aus genau einer ausgewählten
   Mathematikgruppe, ihren bestätigten Quellenrevisionen und zugeordneten
   Lernstartplätzen eine versionierte private Planfassung erstellen. Nur
   ausdrücklich belegte Regeln für Erweitern bzw. Kürzen wählen; bei gemischten
   oder unsicheren Regeln keine Methode aus Titel oder Klassenstufe raten.
   Feste Vorwissensfragen und ihre Grafiken unverändert übernehmen, offene
   Einstiegsslots beibehalten und ausschließlich freie Übungsplätze belegen.
   Frage-ID, Typ, Aufgabe, Faktorangabe/Teiler, Antwort, zugelassene Varianten
   und die zugehörige Lösungsgrafik zusammen binden. Die identitätsbildenden
   Quell-, Referenz- und Plandigests persistieren; vorhandene Receipts und
   begonnene Einheiten nicht nachträglich verändern.
2. Vor dem Modellaufruf gesamte eigene relevante Übungshistorie und bestätigte
   Ausgangsbeispiele berücksichtigen, einschließlich veröffentlichter und
   noch unveröffentlichter validierter Teilrunden sowie konkurrierender
   Aufträge. Gleichwertige oder unklar interpretierbare alte Brüche nicht als
   neue unabhängige Aufgabe ausgeben. Die begrenzte Auswahl ausdrücklich auf
   Erschöpfung prüfen und gegebenenfalls vor einem Modellaufruf sicher stoppen.
   Keine fremden Kinderantworten in den Prompt übertragen.
3. Den gebundenen Plan im bestehenden Paket-Ausgabeschema bei
   `package_part_output.bind_schema` verwenden. Der Adapter darf nur geprüfte
   Grafik-IDs für ihre jeweilige Frage anbieten; Modelländerungen an Fragen,
   Lösungen, Quellen, Aufdeckstufen oder Grafiken müssen als Fehler verworfen
   werden. Das bestehende grafische Offenlegungs- und Schema-Regelwerk bleibt
   maßgeblich. Die KI darf nur zulässige Erklärungen und Hinweise ergänzen.
4. Nach dem Anbieteraufruf vor `store_validated_part` unter den bestehenden
   Sperren Rechte, Quellen-, Referenz- und Planrevision erneut prüfen. Bei
   `package_publication` die private persistierte Planfassung und die aktuelle
   Historie einschließlich anderer wartender Receipts erneut validieren;
   Wiederholung darf weder bestehende Antworten noch gültige Teilpakete
   überschreiben. Ein Status-GET erzeugt keinen erneuten Auftrag.
5. SQLite und isoliertes PostgreSQL für keine, eine und zwei freie Aufgaben,
   feste und offene Einstiegsfragen, richtige und unklare Quellen, Kürzen und
   Erweitern, manipulierte Fragen/Grafiken, fremde Quellen, Versionen,
   Altgeschichte, private Teilreceipts, konkurrierende Aufträge und
   Erschöpfung testen. Danach über den regulären freigegebenen Anbieterweg mit
   ausschließlich künstlichen Mehrseitenmaterialien die konkrete Ausgabe,
   Zeit und tatsächlichen oder weiterhin unbekannten Kosten getrennt prüfen.

Die Gruppierungshilfen sind vorbereitende Bausteine. Sie ersetzen weder die
persistierte Gesamtplanung noch das Schema, die parallele Veröffentlichung,
die Fehlermatrix oder den echten künstlichen Anbieterpfad.

Die beiden künstlichen Gruppentests bestanden auf SQLite und isoliertem
PostgreSQL. Ein weiterer SQLite-Lauf mit 137 Fällen prüfte die bestehende
Erweiterung für Lernweg-, Heft- und Materialrunden sowie die neuen
Gruppenhelfer. Der Test verwendet keinen echten Anbieter und führt keine
Paketgenerierung aus.
