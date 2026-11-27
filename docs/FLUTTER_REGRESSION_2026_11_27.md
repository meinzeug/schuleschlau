# Flutter-Gesamtlauf vom 27.11.2026

Der Lauf verwendete den unveränderten Commit
`733a5a2c672b5119c4f633a9a9d66481d88f7dc2` in einem isolierten Git-Worktree
und die vorhandene, für das Projekt fixierte Flutter-Toolchain. Die drei
dateibasierten Teilmengen wurden nacheinander ohne Testfilter ausgeführt.
`scripts/run_flutter_shard.py verify` prüfte die quellgebundenen Berichte:
alle 385 Testdateien waren jeweils genau einmal enthalten, 4.980 Fälle
bestanden und 19 waren übersprungen. Jeder Teilprozess endete erfolgreich;
Quellbestand und Inventar blieben während des jeweiligen Laufs unverändert.

Die [drei Teilberichte und der Gesamtbericht](evidence/flutter-733a5a2/) sind
ohne private Inhalte gespeichert. Der Gesamtbericht enthält den Commit sowie
die Quellen-, Inventar- und Berichtprüfsummen. Die Berichte zeigen auch die
jeweilige Anzahl übersprungener Fälle; sie ersetzen keine gesonderte Prüfung
dieser Fälle. Der frühere Lauf auf `3133fea` scheiterte an einer veralteten
Erwartung im Test zur gespeicherten Lernwegaktion; diese wurde vor dem hier
erfassten Lauf auf die tatsächliche Schaltfläche korrigiert.

Der Lauf umfasst künstliche Flutter-Tests. Er ist weder eine Live- oder
Android-Geräteabnahme noch ein Nachweis der fachlichen Modellqualität. Nach
`733a5a2` entstandene Änderungen sind durch diesen Gesamtlauf nicht abgedeckt
und benötigen eigene oder erneute Prüfungen. Es wurde kein Release ausgelöst.

Wiederholung im betreffenden Quellstand, mit installiertem Projekt-SDK:

```sh
python3 scripts/run_flutter_shard.py --root "$PWD" run --shard-index 0 --receipt /tmp/flutter-0.json --flutter /pfad/zum/flutter
python3 scripts/run_flutter_shard.py --root "$PWD" run --shard-index 1 --receipt /tmp/flutter-1.json --flutter /pfad/zum/flutter
python3 scripts/run_flutter_shard.py --root "$PWD" run --shard-index 2 --receipt /tmp/flutter-2.json --flutter /pfad/zum/flutter
python3 scripts/run_flutter_shard.py --root "$PWD" verify --receipts /tmp/flutter-0.json /tmp/flutter-1.json /tmp/flutter-2.json --receipt /tmp/flutter-gesamt.json
```
