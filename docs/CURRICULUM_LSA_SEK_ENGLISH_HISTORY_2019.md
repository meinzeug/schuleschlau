# Sachsen-Anhalt: Englisch und Geschichte in der Sekundarschule

Das separat versionierte, ausdrücklich importierbare Paket
`backend/schulpilot/reference/curriculum-de-st-sek-englisch-geschichte-2019-v1.json`
fügt **zwei Dokumente und 46 eigene kurze Themen- und Phasenlabels** hinzu.
Es ist eine lückenhafte Lehrplanorientierung und keine vollständige Stoffliste,
kein Schuljahresplan und kein Beleg über den Lernstand eines Kindes.

## Amtliche Quellen und überprüfte Fassung

Der [Bildungsserver Sachsen-Anhalt](https://www.bildung-lsa.de/informationsportal/unterricht/sekundarschule/schulformbezogene_informationen/lehrplan.html)
verlinkte bei Prüfung am 22.11.2026 die folgenden Fachlehrpläne für die
Sekundarschule. Beide tragen den Stand 01.08.2019 und nennen „in Kraft seit
2012, Anpassung 2019“. Die gedruckten Seitenzahlen, nicht die Positionen des
PDF-Viewers, sind in den Einträgen angegeben.

- [Englisch](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_engl_01_08_2019.pdf),
  SHA-256 `dac1563a6b22da366e742b40d566dec5f234357fa6dcaacabf567ddc0e5a6897`:
  5/6 Abschnitt 3.1 ab Seite 10; Realschulunterricht 7/8 ab Seite 15 und 9/10
  ab Seite 20; Hauptschulunterricht 7/8 ab Seite 25 und 9 ab Seite 29. Der Realschulabschnitt 9/10 und der Hauptschulabschnitt 9 tragen im
  Original beide die Abschnittsnummer 3.3.2. Die übergeordnete Zuordnung
  und die Seitenzahlen bleiben deshalb ausdrücklich erhalten.
- [Geschichte](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_gesch_01_08_2019.pdf),
  SHA-256 `a734089a5bb9aaff7d1a4c3ed572077fa504aa3b171796afb3078bc6c5a92120`:
  Übersicht und Fußnoten auf Seiten 10–11, 5/6 ab Seite 12, 7/8 ab Seite 17,
  9/10 ab Seite 23.

Die amtlichen PDFs nennen als Quelle das Landesportal Sachsen-Anhalt und
CC BY-SA 3.0. Die jeweils einwortigen Belege wurden auf der angegebenen
Seite kontrolliert; bei gemeinsamen Englisch-Oberbegriffen wurde derselbe
Kompetenzbereich außerdem auf den Seiten beider Abschlusswege kontrolliert.
Die Themenlabels sind eigene Zusammenfassungen und keine übernommenen Aufgaben.

## Was die Daten aussagen – und was nicht

Englisch 5/6 ist ein Doppeljahrgang. Für 7/8 sind nur ausdrücklich in beiden
abschlussbezogenen Abschnitten vorhandene **grobe Kompetenzbereiche** wie
Lesen oder Schreiben als gemeinsames Band erfasst. Die Anforderungen der
beiden Bildungsgänge unterscheiden sich; das Band stellt weder gleiches Niveau
noch einen bestimmten Lernfortschritt fest. Da das vorhandene Profil keinen
Abschlussweg bestätigt, sind konkrete abschlussbezogene Abschnitte 9 bzw.
9/10 als Phasen **ohne** Klassenangabe gespeichert und erscheinen nicht durch
Klassenfilter oder automatisch in der Lernplanung. Aus Klassenstufe oder Fach
werden weder Sprachvariante, Spracherfahrung noch Grammatikkenntnisse abgeleitet;
die Regeln aus `docs/LANGUAGE_LEARNING.md` gelten unverändert.

In Geschichte verlangt die Übersicht bei den drei Bereichen Ägypten,
Griechenland und römische Kaiserzeit mindestens zwei. Die konkrete Auswahl
jeder Schule ist unbekannt. Diese drei Bereiche bleiben deshalb in einer
Wahlgruppenphase ohne Klassenfilter; das Paket erfindet keine Auswahl. Die
übrigen 5/6- und 7/8-Schwerpunkte bleiben als Doppeljahrgänge erhalten. Drei
auf Seite 11 ausdrücklich für Klasse 9 markierte Geschichtsschwerpunkte
werden als 9 gespeichert. Die Methoden zu digitalen Medien und Ausstellung
sind entsprechend Seite 10 den Jahren 9 beziehungsweise 10 zugeordnet. Die
weiteren Vertiefungen 1945, Systemkonfrontation und 1990 bleiben das amtliche
Band 9/10: Daraus folgt keine Behauptung, dass jede Schule ein Thema bereits
in Klasse 9 behandelt.

## Import und Tests

Das vorhandene `CatalogueInput`-Schema und der authentifizierte, auditierte
`/api/admin/curriculum/import`-Endpunkt können dieses Paket nach Betreiberprüfung
idempotent übernehmen. Das bloße Vorhandensein der Datei importiert sie nicht.
Ein späterer Seed oder eine Migration muss getrennt kontrollieren, ob dieselbe
Fassung bereits vorhanden ist. Erzeugung von Aufgaben und KI-Aufrufen wird
dadurch nicht ausgelöst. Originale, einmal importierte Dokumentkennungen und
Themenfassungen bleiben unveränderlich; neue Fassungen erhalten neue IDs.

`backend/tests/test_curriculum_de_st_sek_en_history_2019.py` prüft das Schema,
die getrennten Pflicht-/Wahl- und Abschlussbereiche sowie den wiederholten
Import und die vorhandenen Klassen-/Phasenfilter in einer isolierten Datenbank.
Diese Prüfung ist keine pädagogische Gesamtabnahme und kein Nachweis eines
Imports auf einer produktiven Installation.
