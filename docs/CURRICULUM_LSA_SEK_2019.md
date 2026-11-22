# Sachsen-Anhalt: Sekundarschule Mathematik und Deutsch

Diese geprüfte **Teilerfassung** ist ein separat importierbares Paket:
`backend/schulpilot/reference/curriculum-de-st-sek-math-deutsch-2019-v1.json`.
Sie enthält zwei Dokumentfassungen und 49 eigene, knappe Themenbezeichnungen;
sie ist kein vollständiges Curriculum und keine Sammlung von Aufgaben oder
Grafiken. Das Fach, die dokumentierte Ausgabe und der tatsächliche
Geltungsbereich bleiben an jedem Datensatz erhalten.

## Amtliche Quellen

Der [Bildungsserver Sachsen-Anhalt: Lehrplan Sekundarschule](https://www.bildung-lsa.de/informationsportal/unterricht/sekundarschule/schulformbezogene_informationen/lehrplan.html)
führte bei der Sichtprüfung am **22.11.2026** beide unten genannten Fachlehrpläne
als Fachlehrpläne auf. Beide PDF-Dateien nennen **Stand 01.08.2019**, „in Kraft
seit 2012, Anpassung 2019“. Das Datum 01.08.2019 ist hier der Fassungsstand;
daraus wird kein gesondertes Inkrafttretensdatum erfunden.

- [Mathematik, Sekundarschule](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_mathe_01_08_2019.pdf),
  PDF-SHA256 `88e5b643f654715e3a107ae51d4ec0e17702e66e0886f1e3f443dcd20446ace9`.
  Gemeinsam 5/6: Abschnitt 3.2, gedruckte Seiten 21–30; abschlussbezogen 7/8:
  3.3.1 und 3.4.1. Für 9 nennt die Fußnote auf Seite 40 bestimmte Inhalte
  des realschulabschlussbezogenen Unterrichts; diese wurden nur dann als
  gemeinsame Jahrgangs-9-Oberbegriffe aufgenommen, wenn sie auch im
  hauptschulabschlussbezogenen Abschnitt 3.4.2 aufgeführt sind. Die dortigen
  Anforderungen und der fachliche Umfang sind nicht als identisch behauptet.
- [Deutsch, Sekundarschule](https://www.bildung-lsa.de/files/164f3f97e3adf65ff6f44685dd9e1ced/lp_sks_deutsch_01_08_2019_k2.pdf),
  PDF-SHA256 `2d84d1750e43ee956e0520719f205773b16582692ebaf03269d70303ae4e8a44`.
  Gemeinsam 5/6: Abschnitt 3.1, Seiten 10–16; abschlussbezogen 7/8:
  3.2.1 und 3.3.1. Die gemeinsamen Labels benennen nur jeweils in beiden
  Abschnitten sichtbare grobe Kompetenzbereiche; sie setzen Unterschiede im
  erwarteten Niveau und den konkreten Inhalten nicht gleich.

Die Seitenangaben sind die **gedruckten** Seitenzahlen. Die einwortigen
Belegstellen sind auf der jeweils angegebenen Seite vorhanden; die zweite
Seite gemeinsamer 7/8-Oberbegriffe steht zusätzlich im Abschnittsfeld. Die
Dokumente sind mit CC BY-SA 3.0 gekennzeichnet; Quelle ist jeweils das
Landesportal Sachsen-Anhalt. Die eigenen Kurzlabels ersetzen keine genaue
fachliche Prüfung im Original.

## Bildungsgang und sichere Verwendung

Der Lehrplan differenziert ab Klasse 7 zwischen haupt- und
realschulabschlussbezogenem Unterricht. Das bestehende Kinderprofil erfasst
zwar Land, Schulform und Klasse, aber **keinen bestätigten Bildungsgang**.
Deshalb gelten folgende Grenzen:

- 5/6 bleiben Doppeljahrgänge; es wird keine künstliche Einzelklasse daraus.
- 7/8 enthält nur grobe Oberbegriffe, die in beiden einschlägigen Abschnitten
  auftreten, und keine Gleichsetzung der Kompetenzniveaus.
- Exakte mathematische Jahrgang-9-Labels wurden nur aus der Schnittmenge der
  Hauptschule und der ausdrücklichen Realschul-Fußnote auf Seite 40 gewählt.
- Ausschließlich bildungsgangbezogene Abschnitte für Deutsch 9 bzw. 9/10 und
  Mathematik 9/10 sind als **Phase ohne Zahlenzuordnung** abgelegt. Die
  bestehenden Klassenfilter und die KI-Planung verwenden sie dadurch nicht
  automatisch; insbesondere wird Klasse 10 nicht durch eine Vermutung gefüllt.
  Eine künftige Erweiterung muss den Bildungsgang mit ausdrücklicher
  Nutzerbestätigung, eigener Revision und fachlicher Prüfung berücksichtigen.

Die Angaben sind Orientierung und kein Beweis für behandeltes oder
beherrschtes Wissen. Bestätigte Heftquellen und Elternplanung bleiben
maßgeblich.

## Import und Abnahmegrenzen

Das Paket erfüllt das bestehende `CatalogueInput`-Schema und kann nach
Operatorprüfung mit dem vorhandenen `/api/admin/curriculum/import`-Endpunkt
importiert werden. Der Import ist ausdrücklich, authentifiziert und auditiert;
das Bereitstellen dieser Datei allein verändert weder eine Installation noch
ein Kinderprofil. Derselbe Paketstand kann idempotent erneut importiert
werden. Der Versionsname ist unveränderlich; neue Fassungen benötigen neue
Kennungen. Bestehende Altdaten werden nicht überschrieben.

Der isolierte Integrationsfall `backend/tests/test_curriculum_de_st_sek_2019.py`
prüft Schema, Quellen, Bänder, getrennte Phasen, Import und erneuten Import,
Klassenfilter sowie dass kein Lern-, KI- oder Zeitbeleg entsteht. Er bestätigt
nicht die flächendeckende Lehrplanabdeckung, eine vollständige fachliche
Abnahme oder einen produktiven Import.
