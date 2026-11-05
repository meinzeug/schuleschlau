# Heftquellen: zusätzliche künstliche Backendprüfung vom 05.11.2026

Prüfgrundlage ist Quellcommit `b3e5ba585f8db58d53b74d5ddb08dde38df9be23` mit den zugehörigen Teständerungen. Es wurden ausschließlich isolierte Datenbanken und künstliche Inhalte verwendet; kein Produktionsserver und kein externer Anbieter wurden aufgerufen.

## Quellenwahl und Auftragsrechte

In `backend/tests/test_notebook_practice.py` enthalten die beiden ausgewählten Seiten unterschiedliche künstliche Textmarker. Beide Marker müssen im tatsächlich an den simulierten Worker-Anbieter übergebenen Material vorkommen; ein dritter, nicht ausgewählter Seitenmarker darf dort nicht vorkommen. Die veröffentlichte Einheit muss exakt die beiden Quellenkennungen und Revisionen speichern; eine ältere Antwort bleibt unverändert.

Die neue Matrix ändert an einer ausgewählten Seite Inhalt, Lesewarnung, Fachzuordnung oder Bestätigung, ohne die Revisionsnummer zu ändern, beziehungsweise löscht die Seite. Dies geschieht jeweils vor dem Modelltransport oder während des simulierten Anbieteraufrufs. Außerdem entziehen getrennte Fälle der absendenden Kindersitzung oder dem absendenden Elternkonto die Schreibberechtigung. In allen Fällen darf keine Einheit, Antwort oder Quellenzuordnung veröffentlicht werden; alle vorhandenen Zeilen dieser drei Tabellen werden vollständig vor und nach dem Auftrag verglichen. Vor dem Transport fallen keine Modellkosten an; nach dem Transport bleiben die künstlich gemeldeten Kosten als `failed_billed` erhalten.

## Fünf verschiedene Materialansichten und lesende GETs

`backend/tests/test_notebook_distinct_materials_acceptance.py` zeichnet fünf verschiedene beschriftete JPEG-Testseiten mit den Rollen Arbeitsblatt, Hefter, Arbeitsheft, Buchseite und Testseite. Sie enthalten künstliche Texte, Wasserzeichen und einfache Kästchen beziehungsweise Linien. Die Bilder werden über den regulären Uploadendpunkt einer isolierten Familie gespeichert. Der Test weist sie anschließend für die reine Backendprüfung in der Testdatenbank einem Fach und Titel zu: Dies ist weder Bilderkennung noch eine in der App erfolgte Seitenbestätigung.

Ein berechtigtes Kind ruft Sortierung, Suche, Detail, Quellversionsliste und private Bilddatei ab; die fünf gespeicherten Bilder sind unterschiedlich, und die Fotoantworten tragen `Cache-Control: no-store`. Gast, Geschwisterkind und synthetischer Betriebsadmin erhalten keinen Zugriff auf die privaten Bilder, Details oder Quellversionslisten. Vorhandene vollständige Zeilen für Material, Runden, Quellenbindungen, Antworten, Aktivitäten, Kompetenzstand, Aufträge und Kosten werden vor und nach den GETs verglichen; dieser Test beansprucht nicht, dass auch technische Sitzungszugriffszeiten unverändert bleiben.

## Ergebnisse und Grenzen

Die beiden vollständigen Testdateien bestanden auf SQLite und einem isolierten PostgreSQL-16-Cluster mit je **54 Fällen**. Die später ergänzten zwei Löschzeitpunkte und die erweiterten Gast-/Geschwister-/Adminprüfungen wurden anschließend getrennt auf beiden Datenbanken geprüft. Nach Erweiterung um vollständige Zeilenvergleiche bestanden die 14 Fehler- und Rechtefälle sowie die Bild- und GET-Prüfung jeweils nochmals auf beiden Datenbanken. Eine Starlette-/HTTPX-DeprecationWarning bleibt bestehen. Ruff und `git diff --check` waren erfolgreich.

Die Prüfungen belegen keinen Browser- oder Android-Bedienablauf, keine fotografische Qualität, keine OCR, keinen echten Anbietertransport und keine allgemeine fachliche Eignung der erzeugten Aufgaben. Die große Hefte-Abnahme bleibt offen; insbesondere sind reale Oberflächenwege mit den fünf erkennbaren künstlichen Materialarten sowie die durchgängige UI-Abnahme von Einzel- und Mehrseitenstart gesondert zu beobachten.
