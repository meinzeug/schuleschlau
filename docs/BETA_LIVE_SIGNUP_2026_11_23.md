# Beta-Bewerbung: Zielserver-Stichprobe vom 23.11.2026

Eine eigens erzeugte, ausschließlich dem eingerichteten Betreiber-Testpostfach
zugeordnete Gmail-Plusadresse durchlief auf `schuleschlau.dorfspy.de` die
reguläre Beta-Registrierung. Die tatsächliche E-Mail kam im eigenen Postfach
an; der einmalige Bestätigungslink wurde über die reguläre API eingelöst.
Das künstliche Elternkonto meldete sich an und sah seinen Antrag als `pending`.
Anschließend wurde ein künstliches Kind angelegt und mit eigenem Zugang
angemeldet. Das Elternkonto löschte abschließend die eigene Testfamilie über
den vorgesehenen authentifizierten Kontolöschungsweg; der private lokale
Wiederherstellungsbeleg wurde danach entfernt.

Dieser Lauf nutzte echte HTTPS-API-Aufrufe und echte Mailzustellung; er war kein
Browserlauf. Er verwendete keine Kinderdaten, keine KI-Aufträge und verursachte
keine KI-Kosten. Er enthält insbesondere **keine Adminentscheidung**, keine
Beta-Freigabe und keinen echten Foto-/Lernweg. Der lokal isolierte UI-Lauf in
[BETA_BROWSER_2026_11_23.md](BETA_BROWSER_2026_11_23.md) ergänzt, ersetzt aber
nicht diese fehlende Produktionsprüfung.

Das eng begrenzte Prüfwerkzeug `scripts/beta_live_signup_smoke.py` verwendet
nur eine zufällige Plusadresse des konfigurierten eigenen Testpostfachs und
schreibt vor der Registrierung ein privates Wiederherstellungsjournal. Bei
Fehlern bleibt es für `--cleanup` erhalten. Bestätigungscodes, Passwörter und
Adressen werden nicht ausgegeben oder ins Repository geschrieben. Ein später
verifiziertes Konto kann auch bei vorübergehend nicht erreichbarem Testpostfach
gelöscht werden. Das Werkzeug darf niemals auf bereits vorhandene Familien
oder beliebige Postfächer erweitert werden.
