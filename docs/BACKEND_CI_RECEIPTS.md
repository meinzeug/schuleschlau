# Backend-CI: Sammlung, Ausführung und Zusammenführung

Der Backend-Testlauf teilt die vollständige pytest-Sammlung dateiweise auf
drei Matrixjobs auf. Jeder Job speichert einen ausführlichen lokalen
Sammlungsbeleg und erstellt einen kleinen Ergebnisbeleg **erst nach** einem
erfolgreich beendeten pytest-Prozess. Der Runner prüft, dass jede ausgewählte
Testidentität genau einen Abschlussbericht hatte. Normale Erfolge, Skips,
XFAIL und nicht-striktes XPASS stehen getrennt im Ergebnis. Ein Fehler,
striktes XPASS, abgebrochener Lauf, fehlender Test oder ein reiner
`--collect-only`-Lauf erzeugt keinen gültigen Ergebnisbeleg.

Jeder Matrixjob lädt seinen eigenen Beleg als `backend-shard-0`, `-1` oder
`-2` hoch. Der anschließende Job `backend-complete` lädt ausschließlich die
Artefakte desselben Workflowlaufs und prüft exakt drei getrennte Verzeichnisse
mit den jeweils passend benannten Dateien. Die Belege müssen die gleiche
GitHub-Quellrevision, Sammlung und erwartete Partitionen nennen; die Anzahl
und der Digest jeder tatsächlich gewählten Partition müssen zu ihrer Position
passen. Fehlende, doppelte, zusätzliche oder vertauschte Belege und ein nicht
erfolgreicher Matrixlauf lassen die Prüfung fehlschlagen. Im Gesamtergebnis
bleiben Skips und XFAIL/XPASS sichtbar; sie werden nicht als bestandene Tests
ausgegeben.

Für diese Übergabe sind `actions/upload-artifact` v4.6.2 auf
`ea165f8d65b6e75b540449e92b4886f43607fa02` und
`actions/download-artifact` v4.3.0 auf
`d3f86a106a0bac45b974a628896c90dbdf5c8093` festgelegt. Artefakte werden
nach sieben Tagen gelöscht; die ursprünglichen Joblogs bleiben getrennt.

Die Belege weisen Identitäten und Ergebnisse der ausgewählten pytest-Fälle
nach, keine fachliche Vollständigkeit, Quellcode-Integritätsmessung oder
manuelle Geräteabnahme. Die gesonderte PostgreSQL-Konkurrenzsuite verlangt
zusätzlich einen erfolgreichen JUnit-Bericht ohne Skips, einschließlich des
Eltern-Zuordnungs-Rennentests. Ein neuer GitHub-Job wird nur dann zu einem
erforderlichen Merge-Status, wenn die tatsächlich geltenden Repository-Regeln
ihn auch verlangen; diese Einstellung ändert der Workflow nicht selbst.
