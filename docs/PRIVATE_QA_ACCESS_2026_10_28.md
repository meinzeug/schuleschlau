# Interner Zugang für den künstlichen Alltagstest

Die öffentliche Testphase und Bestellfunktion bleiben ausgeschaltet. Für den
ausdrücklich beauftragten Alltagstest gibt es einen lokalen, einmaligen
Operatorbefehl `python -m schulpilot.private_qa_access`, keinen öffentlichen
Endpunkt. Er akzeptiert nur die Kennungen der verifizierten, eigens für diesen
Test angelegten Familie und deren einzelnen Kinderzugangs sowie ausschließlich einen fest vorgegebenen Satz bereits
gespeicherter künstlicher Fotos. Der Befehl prüft Familienmitgliedschaft,
Testalias, Kinderzugang, Inhaltssummen, fehlende frühere Aufträge und Lernbelege
und den unveränderten öffentlichen Testphasenstatus. Er verändert keine anderen
Familien, startet keine KI und protokolliert keine Foto- oder Antwortinhalte.

Die Freigabe verwendet die bestehende Testphasenbuchung für höchstens 30 Tage,
100 Aufrufe und 15 USD. Jeder Auftrag unterliegt weiterhin den normalen
Reservierungen, Provider-, Sitzungs-, Datenschutz- und Globalgrenzen. Der
Datensatz trägt die eigene Version `private-photo-qa-20261028-1`; die lokale
Anlage ist gesondert auditierbar und idempotent. Es wird kein Zahlungseingang
behauptet. Die Begrenzung ist eine technische Obergrenze, keine Kostenzusage.

Die Prüfung der beiden künstlichen Fotos erfolgt bei Anlage. Weitere Uploads im
internen Testkonto müssen weiterhin ausdrücklich künstlich sein; die Prüfung
ist kein allgemeiner Filter für später ausgewählte Fotos. Das private Konto und
seine Zugangsdaten bleiben beim Betreiber. Die reguläre Kontolöschung entfernt
auch die Testbuchung; ohne solche Löschung endet sie automatisch nach 30 Tagen.


## Ergänzender Referenzsatz vom 4. November 2026

Der Operatorbefehl akzeptiert neben dem bisherigen Zweiersatz ausschließlich
die vier Dateien aus `testdata/ocr_synthetic/manifest.json` gemeinsam oder das
feste Paar aus Datei 01 und 03. Die erlaubten SHA-256-Werte beziehen sich auf
den bereinigten JPEG-Upload mit der produktiven Pillow-13-Pipeline, nicht auf
die jeweiligen Originaldateien. Beliebige Teilmengen, Mischungen, doppelte
und unbekannte Bilder bleiben ausgeschlossen; es gibt keinen öffentlichen
Endpunkt oder eine vom Aufrufer veränderbare Hashliste. Die Freigabe ist wie
bisher auf die beim Start geprüfte Familie bezogen; sie garantiert nicht,
dass später hochgeladene Fotos künstlich sind. Die Bildinhalte wurden künstlich
erzeugt und von einer KI gesichtet; eine unabhängige menschliche Prüfung steht
noch aus. Reale OCR-/Anbietertests und die Wirksamkeit der Bilderkennung sind
durch die Aufnahme in diesen Katalog nicht belegt.
