# Backend-Gesamtlauf vom 26.11.2026

Ein vollständiger isolierter SQLite-Lauf des Quellstands `b69df88` ergab
7.113 bestandene, 160 übersprungene, zwei erwartbar fehlgeschlagene und sechs
fehlgeschlagene Tests. Die 29 gemeldeten Untertests sind bereits Teil des
Laufs. Dies war keine erfolgreiche Gesamtabnahme und umfasste keine echten
Anbieteraufrufe oder Geräte.

Die Fehler wurden einzeln überprüft:

* Zwei Tests erwarteten eine Quellenbestätigung durch ein Kind. Der aktuelle
  beauftragte Ablauf lässt diese Entscheidung den Eltern. Die Prüfungen
  verlangen nun ausdrücklich die Ablehnung im Kinderzugang und bestätigen
  anschließend als berechtigtes Elternkonto. Die übrigen Schutz- und
  Löschbedingungen bleiben erhalten.
* Vier Tests für die Fortsetzung eines Schulbuddy-Gesprächs verwendeten eine
  künstliche Antwort **und** ein sichtbares Zitat mit der Lösung der noch
  offenen Frage. Der bestehende Lösungsschutz lehnte sie deshalb ab. Der neue
  künstliche Hinweis und sein echtes Quellenzitat verraten die Lösung nicht.
  Die Tests prüfen weiterhin, dass eine unveränderte Frage fortgesetzt und
  eine geänderte Frage nicht wiederverwendet wird. Ein zusätzlicher Statuscheck
  unterscheidet eine fehlgeschlagene Tutorantwort von einer gültigen.

Auf dem fortgeschriebenen Stand bestanden die betroffenen Fälle und die
zugehörigen Prüfungen erneut: 15 Tests auf SQLite und 31 auf isoliertem
PostgreSQL. Der historische Gesamtlauf wurde nicht nachträglich als bestanden
umetikettiert. Ein vollständiger erneuter Gesamtlauf des aktuellen Stands ist
für eine entsprechende Freigabe weiterhin erforderlich.

Im anschließenden Lauf des festgehaltenen Stands `9c8612c` zeigte sich
zusätzlich eine veraltete Erwartung in zwei Migrationstests: Eine spätere
Lehrplanmigration verhindert den Downgrade bereits vor dem älteren
Diagnoseschutz. Beide Tests prüfen jetzt den tatsächlich zuerst greifenden
Schutz; die ältere Sperre wird weiterhin direkt auf ihrem historischen
Migrationsstand geprüft. Die Testfälle bestanden anschließend auf SQLite
(zwei bestanden, ein PostgreSQL-Fall übersprungen) und auf isoliertem
PostgreSQL (drei bestanden). Der laufende Gesamttest bleibt an seinen
ursprünglichen Quellstand gebunden; sein Ergebnis wird nicht verändert.
