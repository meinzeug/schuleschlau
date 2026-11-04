# Isoliertes Profil mit Warteschlange vom 4. November 2026

Das Profil misst einen begrenzten künstlichen Lastfall und keine produktive
Nutzerkapazität. Es verwendet die Arbeitsfassung auf Basis von `1559d967` und
den ergänzten Test `backend/tests/capacity_worker_profile.py`. Es verwendet
keine echten Konten, Bilder, Daten oder externen Anbieter. Der erste Versuch
wurde während des Anlegens künstlicher Familien durch das reguläre
IP-Registrierungslimit mit HTTP 429 beendet; es fanden dabei keine Messungen
statt. Der erfolgreiche zweite Versuch gibt jeder künstlichen Familie eine
eigene Testadresse, ohne die Anwendungslimits zu verändern.

## Reproduktion und Messaufbau

```sh
taskset -c 0 /home/dennis/schulpilot/.venv/bin/python \
  scripts/test_postgres.py backend/tests/capacity_worker_profile.py -s --tb=short
```

Der Aufruf verwendet einen eigenen kurzlebigen PostgreSQL-16-Cluster mit
privatem Unix-Socket, eine separate Testdatenbank und ein temporäres
Datenverzeichnis. Alle beteiligten Prozesse erben die Beschränkung auf einen
CPU-Kern. Ein künstlicher Anbieterantwort-Baustein verzögert jeden Aufruf um
100 ms; dies ist **keine Messung eines KI-Anbieters**. PostgreSQL wird nach
dem Lauf heruntergefahren. Die Anfragen nutzen den lokalen FastAPI-TestClient
im selben Prozess, ohne Netzwerk, TLS oder Reverse-Proxy. Registrierung und
Erstellung der künstlichen Familien erfolgen vor dem gemessenen Abschnitt.

Der Produktivserver hatte zum lesenden Vergleich einen verfügbaren CPU-Kern,
1.960.952 KiB RAM und für den separaten Worker ein systemd-Speicherlimit von
300 MiB. Der Testrechner hat erheblich mehr physischen Speicher; eine
vergleichbare 2-GiB-Speichergrenze wurde nicht erzwungen. TestClient, API,
Testtreiber und Worker laufen im Testprozess zusammen. Die RSS-Summe der
PostgreSQL-Prozesse zählt gemeinsam genutzte Speicherseiten mehrfach und ist
eine grobe obere Schätzung, keine Verbrauchsabrechnung. Ein Offsite-Prozess
war auf dem Testrechner während des Laufs aktiv; der Host war nicht exklusiv
reserviert. Die Angaben erlauben keine unmittelbare Ableitung produktiver
Worker-Speichergrenzen.

## Durchlauf und Messwerte

Der Test lief am 04.11.2026, während die synchronisierte Serveruhr ungefähr
12:14 UTC zeigte. Acht getrennte künstliche Familien verwenden jeweils eine
eigene Sitzung. Die JPEG-Testdaten sind 1.938.882 Bytes groß. Pro Familie
werden derselbe Upload und derselbe Auftrag je zweimal gleichzeitig gesendet.
Vier Datenbankverbindungen konkurrieren beim Claim um wartende Jobs; danach
arbeitet der tatsächliche Worker-Verarbeitungspfad die acht Jobs ab. Während
der Verarbeitung senden acht parallele Testclients Übersichts- und
Materiallisten-GETs, vier neue Uploads und vier Wiederholungen von
Auftragsreservierungen.

| Messung | Parallelität | Anfragen | Dauer | p95 | HTTP-Ergebnis |
| --- | ---: | ---: | ---: | ---: | --- |
| Übersicht | 1 | 24 | 4,035 s | 56,51 ms | 24 × 200 |
| Übersicht | 4 | 24 | 4,315 s | 277,82 ms | 24 × 200 |
| Übersicht | 8 | 24 | 4,617 s | 674,12 ms | 24 × 200 |
| Foto mit gleichem Schlüssel wiederholen | 8 | 16 | 4,978 s | 2.213,67 ms | 16 × 201 |
| Auftrag mit gleichem Schlüssel wiederholen | 8 | 16 | 2,937 s | 559,45 ms | 16 × 202 |
| Gemischte API-Zugriffe während Worker-Lauf | 8 | 24 | 5,634 s | 941,38 ms | 16 × 200, 4 × 201, 4 × 202 |

Die p95-Werte verwenden den nächsthöheren beobachteten Rang; bei 16 bis 24
Anfragen sind sie nur eine kleine Stichprobe. Der Test bestand: Die acht
wiederholten Uploads ergaben acht Seiten, die acht wiederholten Reservierungen
acht Aufträge und acht Reservierungen. Vier konkurrierende Claims lieferten
vier unterschiedliche Jobs. Alle acht Jobs wurden genau einmal versucht und
abgeschlossen; die Anfangstiefe der Warteschlange war acht, am Ende null. Das
ganzzahlig gemessene Alter des ältesten Jobs betrug vor der Abarbeitung zwei,
am Ende acht Sekunden. Der Workerabschnitt einschließlich gemischter Last
dauerte 6,464 Sekunden. Der gemessene Gesamtabschnitt dauerte 27,357 Sekunden,
die Python-CPU-Zeit 22,179 Sekunden. Die maximale Python-RSS war 510.192 KiB;
die größte abgetastete kombinierte RSS-Summe aus Python und PostgreSQL betrug
787.796 KiB. Acht simulierte und null externe Anbieteraufrufe wurden gezählt.

## Grenzen und Betriebsfolgen

Dieser Test deckt einen einzelnen künstlichen Laststoß bis acht parallele
Clients ab. Er beweist weder stabilen Dauerbetrieb noch eine Zahl gleichzeitig
lernender Familien. Die 100-ms-Anbieterantwort, das einprozessige TestClient-
Modell, die Registrierung außerhalb der Messung, andere Hardware und
fehlende Netzwerk-/TLS-/Gerätelatenz beschränken die Übertragbarkeit. Der
feste künstliche Seiteninhalt beweist keine Texterkennung. Die
zustandsbehaftete Berechnung von Antwortqualität und Anbieterlimits wurde
hier nicht abgenommen.

Als reproduzierbare **Testgrenze**, nicht als Produktionsversprechen, wurden
acht Familien, acht parallele Anfragen und eine Anfangswarteschlange von acht
Jobs erfolgreich beobachtet. Für dieses eine Profil wären eine Fehlerrate
über null oder eine nicht vollständig geleerte Warteschlange Warnsignale für
eine Untersuchung; diese Grenzwerte sind noch keine für den laufenden Betrieb
kalibrierten Alarme. Die existierende Betriebsmetrik markiert wartende Jobs
älter als 300 Sekunden; die Eignung dieses Werts für echte Modelllaufzeiten
ist durch die simulierte Antwort nicht belegt. Vor einer Freigabe wachsender
Nutzung sind ein reales Einsatzprofil, längere Laststufen, CPU-/Speichergrenzen
der separaten Dienste, Netzwerk und kontrollierte echte Anbieterzeiten sowie
daraus verantwortet festgelegte Alarmwerte erforderlich. Der große
Roadmap-Punkt bleibt bis dahin offen.
