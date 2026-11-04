# Codex-Worker-Container: lesende Bestands- und Sicherheitsprüfung

Am 04.11.2026 wurde ausschließlich der bereits laufende isolierte
`schulpilot-codex`-Container auf `dorfspy` untersucht. Vor und nach dem
Auslesen meldete Podman dieselbe laufende Image-ID
`sha256:4108826b16ff42fc6b8491a5cf8361dc1e34c0c7aa4a6deba2ae3578ca19c8d4`
und denselben Startzeitpunkt. Die gepinnte ID aus
`/opt/schulpilot-codex/image-id` stimmte überein. Das lokale Image meldete
`localhost/schulpilot-codex:0.162.1`, den Image-Digest
`sha256:46543819cf8b2844fe749ad97fef4a2d60a5d7edc323bcea83a9c8ac2a492e52`
und Erstellungszeitpunkt 01.11.2026. Containerdateisystem und Betriebseinstellungen
wurden nicht geändert; es wurde kein weiterer KI-Auftrag gestartet.

Das laufende System identifiziert sich als Debian 12 Bookworm; die dort
verwendete Python-Laufzeit meldet 3.12.15 und `ssl` OpenSSL 3.0.22. Der
aktuelle Repository-Containerfile nennt als Basis `python:3.12-slim-bookworm`
mit Digest `sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258`.
Das ist der deklarierte Baueingang des vorliegenden Quellstands, kein
unabhängiger Attestierungsnachweis, dass der laufende Imageinhalt genau daraus
gebaut wurde. Die laufende Image-ID und der Image-Digest sind verschiedene
Kennungen und nicht mit dem Basisimage-Digest gleichzusetzen.

## Paketbestand und OSV

Die nicht personenbezogenen [dpkg-](dependency-inventory/codex-container-20261104/dpkg.tsv)
und [Python-Metadaten](dependency-inventory/codex-container-20261104/pypi.json)
enthalten 105 installierte Debian-Binärpakete, daraus 73 unterschiedliche
Quellpaket-/Versionspaare, und 18 Python-Distributionen. Die
[zeitgebundene OSV-Abfrage](dependency-inventory/codex-container-20261104/osv.json)
vom 04.11.2026 fragte die konkreten Debian-Quellversionen mit `Debian:12`
und die Python-Versionen mit `PyPI` ab. OSV meldete zu 27 der 73
Debian-Quellpaketversionen und zu einer der 18 Python-Distributionen mindestens
eine Kennung. Diese Mengen sind **keine Zahl nachgewiesen ausnutzbarer
Schwachstellen**: Einträge können sich überschneiden, zurückgestellt, für die
konkrete Nutzung irrelevant oder andernorts bereits entschärft sein. Umgekehrt
sind fehlende Meldungen kein Sicherheitsbeweis. Die zwölf Kennungen für
`pip 25.0.1` enthalten unter anderem Aliasdatensätze und sind nicht als zwölf
verschiedene Lücken zu zählen.

Für die konkrete Priorisierung zuerst die von der Laufzeit benutzte
TLS-Bibliothek prüfen: OSV erfasst `openssl 3.0.22-1~deb12u1` unter
[DEBIAN-CVE-2026-35189](https://osv.dev/vulnerability/DEBIAN-CVE-2026-35189)
und nennt `3.0.22-1~deb12u2` als korrigierte Version. Anschließend die übrigen
OpenSSL-/glibc-/Netzwerkpaketmeldungen und die tatsächlich erreichbaren Pfade
anhand der Debian-Sicherheitsdaten und der Sandbox-Konfiguration bewerten.
Für `pip` nennt [GHSA-4xh5-x5gv-qwph](https://osv.dev/vulnerability/GHSA-4xh5-x5gv-qwph)
Version 25.3 als behoben; die konkrete Ausnutzbarkeit hängt vom Umgang mit
Archiven ab und wurde nicht nachgewiesen. Der normale Worker startet keine
bewusste `pip install`-Aktion während eines Lernauftrags; daraus folgt kein
allgemeiner Ausschluss des Risikos.

Die Bestandsprüfung umfasst **nicht** die kopierte Codex-CLI und deren
statisch eingebundene Komponenten, die separat gebaute Python-Laufzeit, alle
Dateien außerhalb der Paketdatenbanken, Host, Kernel oder die tatsächliche
Ausnutzbarkeit. OSV konvertiert unter anderem Debian-Sicherheitsdaten; aktuelle
und fehlende Einträge müssen gesondert bewertet werden.
[OSV-Datenquellen](https://google.github.io/osv.dev/data/).

## Wiederholung und sichere Abnahme einer Korrektur

Nur auf dem eigenen autorisierten Zielserver ausführen. Diese Befehle lesen
explizit Paketmetadaten, keine Authentisierung, Umgebung oder Dateiinhalte aus
Nutzeraufträgen:

```sh
ssh -o BatchMode=yes dorfspy 'bash -s' > /tmp/codex-dpkg.tsv <<'REMOTE'
cd /var/lib/schulpilot-codex || exit 1
sudo -H -u schulpilot-codex env XDG_RUNTIME_DIR=/run/schulpilot-codex-runtime podman --cgroup-manager=cgroupfs exec schulpilot-codex dpkg-query -W -f='${db:Status-Status}\t${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n'
REMOTE
ssh -o BatchMode=yes dorfspy 'bash -s' > /tmp/codex-pypi.json <<'REMOTE'
cd /var/lib/schulpilot-codex || exit 1
sudo -H -u schulpilot-codex env XDG_RUNTIME_DIR=/run/schulpilot-codex-runtime podman --cgroup-manager=cgroupfs exec schulpilot-codex python -c 'import importlib.metadata as m, json; print(json.dumps(sorted(({"name": d.metadata["Name"], "version": d.version} for d in m.distributions()), key=lambda x: x["name"].lower())))'
REMOTE
python3 scripts/audit_codex_container_packages.py --dpkg /tmp/codex-dpkg.tsv \
  --pypi /tmp/codex-pypi.json --output /tmp/codex-osv.json
```

Image-ID und Startzeit vor und nach der Probenahme kontrollieren; bei Wechsel
ist das Ergebnis keine atomare Imageaufnahme. Das Skript fragt ausschließlich
öffentliche Paketnamen und Versionen ab, verfolgt OSV-Seitentokens, lehnt
fehlerhafte Antworten ab und beendet sich bei Treffern mit Exitcode 1. Es
aktualisiert nichts. Ergebnisse sind datiert und müssen bei neuen
Sicherheitsmeldungen erneut geprüft werden.

Ein geeigneter nächster Schritt ist ein reproduzierbarer lokaler Neuaufbau mit
konkret geprüftem, unveränderlichem Python-Bookworm-Image-Digest, das die
benötigten Debian-Korrekturen enthält, und einer überprüften pip-Version. Den
neuen Bestand erneut gegen OSV und Debian prüfen und die bestehenden
Codex-Worker-, Sandbox-, Anbieter- und Kostenprüfungen ausführen. Anschließend
in einer isolierten Containerumgebung auch Dateisystem-/Netz-/Socketgrenzen,
CLI-Anmeldung, Modellkatalog und künstliche Aufträge prüfen; neue
Providerfreigaben oder Limits nicht stillschweigend ändern. Der lokale
Arbeitsrechner verfügte bei dieser Untersuchung über kein Docker, Podman oder
Buildah, sodass weder ein neuer Digest noch eine Containerkorrektur hier
gebaut oder abgenommen wurde. Kein Serverwechsel und kein Deploy erfolgten.

## Lesende Prüfung eines isolierten Testbuilds und eines Imagekandidaten

Am 04.11.2026 gegen 06:00 UTC waren auf dem Dateisystem `/`, das auch
`/tmp` und den derzeitigen Codex-Store enthält, ungefähr 15 GiB frei. Das
laufende Codex-Image meldete 457.856.724 Bytes, der bestehende Store belegte
ungefähr 5,1 GiB. Das sind Momentaufnahmen, keine für einen Build reservierte
Kapazität oder eine Zusicherung für Parallelbetrieb mit Sicherungen und
anderen Diensten. Podman 4.9.3 ist vorhanden; es bietet Optionen für getrennte
Graph-, Laufzeit- und Temporärverzeichnisse. Nicht privilegierte
User-Namespaces sind laut Hostkonfiguration grundsätzlich zugelassen.

Die lesend geprüften Sub-UID-/Sub-GID-Bereiche gehörten jedoch ausschließlich
den produktiven Konten `schulpilot-codex` und `schulpilot-repair`. `nobody`
besitzt keinen solchen Bereich. Ein alternativer Podman-Store unter einem der
produktiven Konten würde dessen bestehende Dateizugriffsrechte nicht isolieren;
eine Store-Trennung allein belegt deshalb keinen Schutz der Zugänge. Das
Funktionieren eines Builds unter `nobody` ohne Sub-IDs ist nicht nachgewiesen.
Es wurde weder ein Testnutzer angelegt noch ein temporärer Store, Image oder
Container auf dem Server erzeugt.

Sicherer nächster Schritt: eine **separate Test-VM** ohne produktive Konten,
Credentials, Sockets oder Dateifreigaben mit begrenztem Platz, eigenem
Rootless-Buildkonto und eigenen Sub-IDs einrichten. Den Worker dort aus einem
geprüften Quellstand bauen; Bildinhalt, Sicherheitsmeldungen und
Sandboxgrenzen sowie die künstlichen Worker- und Providerfälle prüfen. Erst
nach einem getrennten, dokumentierten Freigabe- und Rückweg kann später ein
Produktivwechsel geplant werden. Alternativ müsste ein neuer dedizierter
Testnutzer auf dem Server samt Zugriffsgrenzen und Kapazität explizit vorab
bereitgestellt und geprüft werden. Der hier angewiesene lesende Check hat
weder eine solche Einrichtung vorgenommen noch sie als gleich sicher belegt.

Als **nicht getesteter Kandidat** wurde über das öffentliche offizielle
[Python-Image](https://hub.docker.com/_/python) am 04.11.2026 das damalige
`3.12-slim-bookworm`-OCI-Indexmanifest abgerufen und mit dessen SHA-256
abgeglichen:
`sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337`.
Das darin ausgewiesene Linux-amd64-Manifest hat den Digest
`sha256:623674a14ef93d052bb9b0de4dbf5f28eb578a35263838941cc8aa43213c1487`.
Auch dessen Manifest und alle vier heruntergeladenen Layer stimmten mit ihren
jeweiligen Digests überein. Ohne ein Image zu starten, wurde aus den
Archivlayern der Debian-Paketstatus gelesen: Dort stehen `openssl` und
`libssl3` jeweils auf `3.0.22-1~deb12u2`, der von OSV für das oben genannte
OpenSSL-Beispiel als behoben genannten Version. Das belegt **nicht**, dass
andere OpenSSL-Meldungen oder der gesamte Container behoben sind.

In einem Layer wurde weiterhin eine `pip`-Distributionsmetadatei für 25.0.1
gefunden. Ein finales Worker-Image mit möglichen späteren Löschungen oder
Upgrades wurde nicht gebaut; die pip-Meldungen dürfen daher nicht als gelöst
angenommen werden. Bei einem echten Kandidatenbuild sind der endgültige
Paketbestand, sämtliche Layer, die kopierte Codex-Binärdatei sowie alle
relevanten OSV-/Debian-Befunde erneut zu prüfen. Die beiden genannten Digests
wurden nicht im Repository-Containerfile eingetragen und nicht deployt.
