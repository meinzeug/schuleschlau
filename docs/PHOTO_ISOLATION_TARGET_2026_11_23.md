# Fotodienst auf dem Zielserver, 23. November 2026

Die Prüfung verwendete Release `e9f2275` (1.38.141), ausschließlich ein im
Arbeitsspeicher künstlich erzeugtes weißes JPEG und keine Kinder- oder
Produktionsfotos. Weder Datei noch Datenbankeintrag wurden erstellt und kein
KI-Anbieter aufgerufen.

Der installierte `schulpilot-photo.service` war aktiv; systemd meldete ein
Speicherlimit von 256 MiB und 16 Tasks. Für die API waren 350 MiB eingestellt.
Ein Prozess mit der UID der API und ihrer Socket-Zusatzgruppe prüfte die UID
des Socketpartners und sendete ein JPEG mit 640 × 480 Pixeln und EXIF-Drehung.
Der Dienst antwortete mit einem dekodierbaren JPEG von 480 × 640 Pixeln. Die
Abfrage verwendete den zur laufenden Codeversion gehörigen Decoderfingerabdruck.
Ein zweiter Prozess mit anderer UID und derselben Socketgruppe wurde vor dem
Verarbeiten abgewiesen. Beide Prüfungen verwendeten den tatsächlichen lokalen
Produktivsocket; die laufende API und der Worker wurden nicht neugestartet.

Diese Stichprobe belegt weder den vollständigen authentifizierten Webimport
noch parallele Großbildlast, reale Mobilnetzbedingungen, OCR oder die
Rückkehr auf eine andere Releaseversion. Die bestehende isolierte Mischlast-
und Rückwegdokumentation bleibt maßgeblich; die umfassende Kapazitätsabnahme
bleibt offen.
