# Schulprofil und Lehrplanorientierung

Die Elternansicht speichert Bundesland, eine angebotene Schulform und Klasse1–13
pro Kind. Das ist eine ausdrückliche Zuordnung: Alte freie Schulangaben werden
nicht still einer amtlichen Schulform zugeordnet. Nach einer Änderung außerhalb
dieses Profils bleibt die frühere Zuordnung sichtbar als erneut zu prüfen.

`curriculum.py` liefert den öffentlichen Katalog und die getrennten privaten
Kinderprofile. Schreibzugriff erfordert die aktuelle berechtigte Elternsitzung,
Familienmitgliedschaft, Kontobindung, Profilrevision und Idempotenzschlüssel.
Kinder können ihr eigenes Profil lesen; Betriebsadministratoren erhalten dadurch
keinen Zugriff auf private Lerninhalte. Profiländerungen werden auditiert und
exportiert; die neuen kindgebundenen Tabellen folgen der bestehenden Löschung.

## Daten und tatsächliche Abdeckung

### DACH-Quellen und wachsende Bildungswege

`GET /api/curriculum/dach-scope` liefert ein öffentliches, authentifiziert
lesbares Quellenverzeichnis für die 16 deutschen Länder, neun österreichischen
Bundesländer und 26 Schweizer Kantone. Es beschreibt zunächst nur Regionen und
offizielle Einstiegsquellen. Insbesondere sind österreichische und Schweizer
Kinderprofile, regionale Bildungswege, Themen und Hochschulprofile damit noch
nicht integriert. Ein GET erzeugt keine Auswahl, kein Lernen und keinen
KI-Auftrag. Die Elternansicht zeigt diese Grenze ausdrücklich an.

In der Schweiz unterscheiden sich die sprachregionalen Lehrpläne und die
kantonalen Fassungen; mehrsprachige Kantone dürfen nicht pauschal einer Sprache
zugeordnet werden. Das EDK beschreibt Lehrplan 21, Plan d’études romand und
Piano di studio sowie getrennte kantonale Regelungen für weiterführende Schulen:
https://www.edk.ch/de/bildungssystem/beschreibung/lehrplaene. Österreichische
Lehrpläne und ihre zeitlich gestaffelte Einführung werden schulformbezogen vom
Ministerium veröffentlicht: https://www.bmb.gv.at/Themen/schule/schulpraxis/lp.html.
Studiengänge benötigen zusätzlich Hochschule, Studiengang, Abschluss und
gültige Fassung; weder das deutsche Klassenfeld noch ein Schulfach ist dafür
ein ausreichender Ersatz.

Im vorhandenen deutschen Schulprofil können Eltern einen Klassenwechsel als
Vorschlag mit einem Knopfdruck einstellen und erst nach Prüfung bewusst
speichern. Der Wechsel wird nicht nach Datum oder Alter erraten. Bereits
gespeicherte Antworten und Lernnachweise werden dabei nicht umgeschrieben.
Die Unterstützung weiterer Länder, ihrer Jahrgangssysteme und eigenständiger
Hochschulprofile ist weiterhin offen.

Die versionierten Dateien `reference/curriculum-sources-v1.json`,
`reference/curriculum-topics-v1.json` und die sieben ergänzenden Pakete für
die Sekundarschule Sachsen-Anhalt enthalten 68 Dokumente und 940 Zuordnungen
mit23Fachschlüsseln aus16Bundesländern. Dokumente behalten amtlichen Verweis,
Fassung, Status und Digest; Themen behalten Abschnitt, gegebenenfalls Seite,
Klassenband oder Originalphase. Ein Band wird nicht als amtlich festgelegte
Einzelklasse ausgegeben. Vorgeschlagene kanonische Themenkennungen sind noch
keine geprüften Kompetenzzuordnungen.

Der Bestand ist ausdrücklich unvollständig: 30 Dokumente/483 Zuordnungen sind als
aktuell geprüft markiert, 38 Dokumente/457 Zuordnungen als Fassung ungeprüft.
Enthalten sind auch amtliche Indizes, Handreichungen und historische Dokumente.
48schulformübergreifende Zuordnungen besitzen derzeit keine konkret nutzbare
Schulformbeziehung. Für Klasse12 fehlen Zuordnungen; Klasse11 und13 haben
nur fünf beziehungsweise vier. Dies ist weder ein vollständiger deutscher
Lehrplanbestand noch eine Sammlung von 908 Grafiken oder Animationen.

Der [Physik-Fachlehrplan Sekundarschule Sachsen-Anhalt, Fassung 01.08.2019](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_physik_01_08_2019.pdf)
ist über den [amtlichen Lehrplanindex](https://www.bildung-lsa.de/informationsportal/unterricht/sekundarschule/schulformbezogene_informationen/lehrplan.html)
verlinkt. Drei Schwerpunkte gelten für Klasse 6 und vier für das gemeinsame
Band 7/8. Die unterschiedlichen Abschlusswege ab Klasse 9 bleiben ausdrücklich
als Realschul- beziehungsweise Hauptschulphase ohne automatisch zugewiesene
Einzelklasse gespeichert. Die beiden experimentellen Realschulthemen sind
Wahlalternativen; die schulische Entscheidung ist unbekannt. Bei einer
Klassenfilterung ohne bekannten Abschlussweg werden die Phaseneinträge deshalb
nicht als passend behauptet. Der Bestand ersetzt weder Schulplanung noch
bestätigten Unterrichtsstoff.

Die amtlichen Fachlehrpläne [Chemie](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_chemie_01_08_2019.pdf)
und [Geographie](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_geo_01_08_2019.pdf)
ergänzen je elf Kompetenzschwerpunkte der Sekundarschule. Die in den
Übersichten ausdrücklich für Jahrgang 9 festgelegten Schwerpunkte sind separat
markiert; die übrigen Doppeljahrgänge werden nicht auf ein bestimmtes Jahr
verteilt. Reihenfolge und tatsächliche Behandlung an der Schule bleiben offen.

Der [Fachlehrplan Ethikunterricht der Sekundarschule](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_ethik_01_08_2019.pdf)
war am 26.11.2026 im amtlichen Landesindex verlinkt. Seine Übersicht auf
gedruckter Seite 8 nennt sieben Schwerpunkte für jedes der Bänder 5/6, 7/8
und 9/10. Das Paket enthält 21 eigene Kurzbezeichnungen mit dieser Fundstelle
und dem SHA-256 des geprüften PDFs. Einzelkompetenzen mit Stern für Jahrgang 9
sind darin nicht einzeln erfasst; aus dem Doppeljahrgang wird deshalb keine
konkrete Klassenreihenfolge abgeleitet. Die Übersicht belegt keine tatsächliche
Teilnahme, keine fachliche Bewertung und keine vollständigen Materialien.

Der [Erprobungslehrplan Informatik der Sekundarschule](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/LP_SKS_Informatik_SpE_01082026n.pdf)
ist laut amtlichem Landesindex die Fassung zur schulpraktischen Erprobung ab
01.08.2026. Die Übersicht auf gedruckter Seite 9 nennt drei Schwerpunkte für
5/6, vier für 7/8 und je zwei für 9 beziehungsweise 10. Die elf erfassten
Kurzbezeichnungen behalten diese Bänder und Einzeljahrgänge sowie Quelle und
Prüfsumme. `current_verified` bedeutet hier, dass die aktuell verlinkte
Fassung geprüft wurde; die Edition enthält ausdrücklich „Erprobungsfassung“
und behauptet keinen endgültigen Lehrplan. Die Reihenfolge und tatsächliche
Behandlung an einer Schule bleiben unbekannt.

Der Import prüft erlaubte amtliche Hosts, Schema, eindeutige Kennungen,
Fachstamm und echte Geltungsbereiche. Wiederholtes Einspielen desselben
Bestands ist idempotent. Neue geprüfte Dokumente und Zuordnungen können über
den bestehenden administrativen Import ergänzt werden; keine externe Suche
oder KI läuft bei einem Katalog-GET.

## Verwendung bei der Vorbereitung

Ein bestehender Einheiten- oder Paketauftrag bekommt höchstens acht lokale
Lehrplanmetadaten zu ausdrücklich konfiguriertem Bundesland, Schulform,
Klassenbezug und ausgewählten Fächern. Das ist Planungsorientierung; bestätigter
Heftstoff, Elternziele und Quellenbelege bleiben maßgeblich. Lehrplanüberschriften
sind keine Antwortquelle, kein zusätzlicher Lernstoff und kein Leistungsbeleg.
Die bestehende Reservierung und Anbieterzahl ändern sich nicht. Quellen und
Profilbindung werden nach der Vorbereitung erneut geprüft. Ist ein amtliches
Inkrafttretensdatum angegeben, verwendet die Planung den Eintrag erst ab diesem
Tag in der Berliner Zeitzone; unlesbare Datumsangaben werden ausgeschlossen.
Der Katalog selbst zeigt die Quellenmetadaten weiterhin lesend an.

Migration0041 ergänzt vier Tabellen nach0040, ohne bestehende Quellen,
Antworten, Erinnerungen oder gemeinsame Grafikbausteine umzuschreiben.
Migration0042 ergänzt anschließend die zwei Tabellen der Benutzerverwaltung.
Die tatsächliche additive Kette wurde in isoliertem PostgreSQL16 und SQLite
mit erhaltenen Altantworten, Unicode, Lernzeit und gemeinsamen Bausteinen
geprüft. Das ersetzt keine fachliche Abnahme der fehlenden Lehrplanbereiche.
Migration 0056 ergänzt ausschließlich das versionierte Ethikpaket; bestehende
Antworten und Lernzeiten bleiben erhalten. Ein Downgrade veröffentlichten
Quellenmaterials erfolgt nicht automatisch, sondern als Vorwärtskorrektur.
Katalog-, Rechte-, Filter- und Migrationstests bestanden auf isoliertem
SQLite (34 bestanden, zwei PostgreSQL-Fälle übersprungen) und PostgreSQL
(36 bestanden). Die Ergänzung ist noch nicht produktiv ausgerollt.
Migration 0057 ergänzt entsprechend die Informatik-Erprobungsübersicht und
erhält vorhandene Lernnachweise. Die zugehörigen Katalog-, Datums-, Profil-
und Migrationstests bestanden auf SQLite (36 bestanden, zwei übersprungen)
und isoliertem PostgreSQL (38 bestanden). Die Ergänzung ist noch nicht
produktiv ausgerollt.
