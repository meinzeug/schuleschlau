# OpenRouter-Klassifikation: CI-Regressionsvertrag

Der GitHub-Lauf [41983041448](https://github.com/meinzeug/schulpilot/actions/runs/41983041448)
für Commit `28886ba` scheiterte in `backend-0` mit fünf fehlgeschlagenen
Subtests in `test_openrouter_error_classification_139.py`. Der nachgelagerte
`backend-complete`-Job meldete daraufhin fehlende beziehungsweise unerwartete
Shard-Artefakte. Der ursprüngliche Lauf bleibt fehlgeschlagen.

Die seit `84512c1` beabsichtigte Zuordnung von ausdrücklich gemeldeten
Authentifizierungs-, Berechtigungs-, Zahlungs- und Anfrageproblemen zu
`not_configured` sowie des eingebetteten Codes 429 zu `provider_busy` war in
dem eigenständigen AST-Test noch nicht berücksichtigt. Der Fehler wurde lokal
mit denselben fünf fehlgeschlagenen Subtests reproduziert.

Der Testvertrag wurde an das konkrete aktuelle Verhalten angepasst und um
prüfbare Fälle für Integer- und Stringcodes, Timeout, ungültiges Schema,
Booleans, Fließkommazahlen, manipulierte Strings und unbekannte Codes
ergänzt. Vertrauliche Anbietertexte dürfen weiterhin weder in Fehlern noch
in öffentlichen Nachrichten erscheinen; unbekannte Kosten werden nicht als
Nullkosten behauptet. Die Änderung betrifft ausschließlich Tests, nicht
Provider, Reservierungen oder Wiederholungsverhalten. Der eigenständige
`python3 backend/tests/test_openrouter_error_classification_139.py`-Lauf
bestand; ein nachfolgender vollständiger GitHub-Lauf ist separat abzuwarten.
