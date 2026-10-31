# Vorbereitung der Freigabe von SchuleSchlau

**Arbeitsstand: 31.10.2026.** Dieser Plan ergänzt die lokale [Roadmap](../ROADMAP.md). Er legt prüfbare Vorschläge für Testumfang und Freigabe fest; er ist weder eine Produktivfreigabe noch ein Nachweis für Datenschutzkonformität oder pädagogische Wirksamkeit. Tatsächliche Ergebnisse gehören mit Quellrevision und Datum in die zugehörigen Prüfberichte. Aktuelle Schutzregeln in `AGENTS.md` und ausdrücklich dokumentierte spätere Entscheidungen haben Vorrang vor älteren Beispielen.

## Freigabestufen und Einsatzbereich

1. **Lokale Entwicklung und synthetische Tests:** isolierte Datenbanken, künstliche Konten und eindeutig gekennzeichnete Bilder und Antworten; kein Schluss auf tatsächliche Geräte-, Anbieter- oder Lernqualität aus Mocks. Echtzeitdienste, Serverzeit und vorhandene Familien bleiben unberührt. Ein echter Anbieteraufruf ist nur mit den jeweils geltenden Freigaben, künstlichem Material und normaler Reservierung zulässig.
2. **Betreuter Pilot:** nur ausdrücklich definierte Familien, Geräte, Materialarten, Fächer und Klassen; verständliche Betreuung, erreichbarer Support sowie geklärte Datenschutz- und Sicherheitsvoraussetzungen. Bereits dokumentierte Betreiberfreigaben bleiben bestehen; sie ersetzen nicht die Prüfung der konkreten erforderlichen Verträge und Einsatzbedingungen. Ein Pilot ist kein öffentlicher Verkauf.
3. **Breite Freigabe:** erst nach dokumentierter Entscheidung zu den angebotenen Funktionen und erfolgreich nachgewiesenen Freigabekriterien. Der Startumfang darf kleiner sein als die langfristige Vision. Physische Android-/Push-Abnahme ist vor einer entsprechenden Geräte- beziehungsweise Zustellungszusage nötig; aktuell ist sie ausdrücklich zurückgestellt. Verkauf und Play-Veröffentlichung sind eigenständige Entscheidungen.

**Vorschlag für die erste begrenzte pädagogische Abnahme:** vorhandene Familienfunktionen, Smartphone-Web und bestätigte oder im freigegebenen automatischen Modus geprüfte Materialien mit Schwerpunkt Klasse 6 und ausgewählten Fächern. Bundesland, Schulform, konkrete Fächer und beteiligte Personen sind vor dem Piloteinsatz anhand überprüfter Abdeckung festzulegen; fehlende Lehrplanzuordnungen dürfen nicht ergänzt oder vorausgesetzt werden. Dieses Vorgehen verpflichtet niemanden auf einen öffentlichen Start und schließt spätere Klassen nicht grundsätzlich aus.

## Prüfkatalog für künstliche Materialien

Ein versioniertes Testset soll für die freigegebenen Bereiche jeweils mehrere unabhängige Fälle mit Referenzbild, wörtlicher Abschrift, Fach-/Themenbindung und erwarteten Unsicherheiten enthalten. Es unterscheidet die Prüfung der Erfassung von der sachlichen Korrektur. Die Auswahl ist vor Modelltests festzuhalten, einschließlich eindeutig lesbarer und absichtlich undeutlicher Stellen. Mindestens die folgenden Kategorien sind zu berücksichtigen, soweit sie im Startumfang angeboten werden:

- Druck und künstliche Handschrift, mehrere Absätze, kleine Schrift, Schatten, Drehung, Zuschnitt und Perspektive;
- Brüche, Rechenzeichen, Einheiten, Zahlenstrahl, Tabellen und nicht beschriftete Zeichnungen;
- falsche Schülerrechnung mit sichtbarer Korrektur, durchgestrichene Stellen und unlesbare Teile;
- Aufgaben in Mathematik, Deutsch und Englisch sowie exemplarisch ein naturwissenschaftliches und ein gesellschaftswissenschaftliches Fach;
- Materialarten Heft, Arbeitsblatt, Arbeitsheft und Tests; Bücher oder weitere Arten nur, wenn Inhalt und Nutzungsrechte für die Testvorlage geklärt sind;
- mehrere zusammengehörige Seiten, unterschiedliche Fächer, Duplikate, Revisionen und leere oder vollständig unlesbare Seiten.

Die fachkundige Sichtung bewertet Originaltreue, fehlende oder erfundene Angaben, kritische Zeichen, Quellbezug, Korrekturen, Grafik, Lösung und Verständlichkeit getrennt. Fehler und Unsicherheiten werden pro Fall dokumentiert. Eine plausible Antwort, drei Textanker, ein erfolgreicher Providerstatus oder ein zweiter KI-Durchgang beweisen keine vollständige Erkennung. Ein bewusstes Zurückstellen eines fehlerhaften Falls ist als solches auszuweisen, nicht als Erfolg.

## Verbindliche Prüfkriterien für eine vorgeschlagene Freigabe

Die folgenden Kriterien sind arbeitsfähige Mindestvorschläge und ersetzen keine fachliche oder rechtliche Prüfung. Verantwortliche müssen vor der betreffenden Freigabestufe bestätigen, welche Nachweise und Zielwerte für ihren Einsatzbereich ausreichen.

| Bereich | Messung und Mindestkriterium für die Freigabeprüfung |
| --- | --- |
| Rechte und Isolation | Alle definierten Negativfälle für fremde Familien, Geschwister, Adminzugriff auf private Inhalte, widerrufene Sitzungen und private Dateien müssen den Zugriff verweigern; kein offener kritischer Befund. |
| Antwort und Lernstand | In allen definierten Regressionen bleiben Originalantworten und Hilfen erhalten. Aufgaben und Versuche zählen getrennt; nicht nachgewiesene oder unklare Leistungen werden nicht als sicher beherrscht dargestellt. |
| Quellen und fachliche Sicherheit | Jeder kritische Fehler im festgelegten Prüfkatalog wird korrigiert und im betroffenen Fall erneut getestet oder der betroffene Anwendungsfall bleibt ausdrücklich außerhalb der Freigabe. Unleserliches wird nicht erfunden. |
| Aufträge und Kosten | Die definierten Fehler- und Konkurrenzfälle zeigen keine doppelten Aufträge durch GET/Reload, keine unkontrollierten Wiederholungen und keine stillschweigende Grenzänderung. Unbekannte Kosten bleiben unbekannt und konservativ reserviert. |
| Rollout und Rückweg | Releaseartefakte sind an den geprüften Quellstand gebunden; Migration und separat geübte Wiederherstellung samt Löschjournal und Sitzungswiderruf sind belegt. Kein ungetesteter blinder Rollback. |
| Kinderbedienung | Repräsentative Kinderwege sind auf den freigegebenen Bildschirmgrößen praktisch bedient, Hindernisse dokumentiert und freigabekritische Mängel behoben. Ein einzelner Durchlauf ist keine allgemeine Usability- oder Wirksamkeitsstudie. |
| Android und Push | Nur bei tatsächlichem Freigabeumfang: Testgerät, Version, beobachtete Anzeige im nachgewiesenen Hintergrundzustand und korrekter Zielaufruf dokumentiert. FCM-Annahme ist kein Zustellungsbeleg. |
| Datenschutz und Kinderschutz | Zuständige Fachpersonen prüfen Datenflüsse, Anbieter- und Vertragsgrundlagen, erforderliche Risikoanalysen und das Schutz-/Eskalationskonzept. Offene kritische Punkte werden vor Freigabe behandelt. |

## Betriebsziele vor Last- und Wiederherstellungstest festlegen

Für den jeweiligen Einsatzbereich dokumentieren Verantwortliche vor dem Lasttest die geplante Zahl gleichzeitig aktiver Familien, typische und Spitzenlast, Uploadgrößen, Anbieterabhängigkeiten und die vorgesehenen Grenzwerte für Fehlerrate, Antwortzeit, Warteschlangenalter, freien Speicher sowie geschätzte Kosten. Tests verwenden isolierte produktionsähnliche Datenbanken und künstliche Daten. Der bestehende begrenzte Smoke-Test ist keine Kapazitätsabnahme; die prozesslokale Signalisierung der Familienanrufe muss vor Mehrprozessbetrieb gesondert gelöst und getestet werden.

Vor einer Wiederherstellungsübung werden maximal akzeptabler Datenverlust und Wiederanlaufzeit festgelegt. Die Probe läuft in einer separaten Datenbank, mit authentifiziertem Löschjournal, widerrufenen Sitzungen, gesperrter KI und ohne Überschreiben des Produktivbestands. Tatsächlich gemessene Zeiten, Datenlücken und das Alter der Offsite-Kopie werden anschließend gegen die vorher festgelegten Ziele ausgewertet. Die bislang dokumentierte ungefähr tägliche Sicherung ist keine zugesicherte Null-Datenverlust-Lösung.

## Beleg und Entscheidung

Für jeden ausgeführten Test mindestens Datum, Quellstand, Konfiguration beziehungsweise Testmodus, künstliche Datenbasis, Geräte-/Browserstand, Methode, Ergebnis und Grenzen festhalten. Private Inhalte, Zugangsdaten und Schlüssel gehören nicht in Berichte oder Git. Fehler werden mit reproduzierbarem Fall, Korrektur und erneutem Ergebnis dokumentiert. Ein abschließendes Freigabeprotokoll führt Umfang, ausgeschlossene Funktionen, zuständige Personen, offene Risiken und Entscheidung je Stufe auf. Die [Roadmap](../ROADMAP.md) darf nur abgehakt werden, wenn deren vollständige Kriterien erfüllt und die Belege verlinkt sind.
