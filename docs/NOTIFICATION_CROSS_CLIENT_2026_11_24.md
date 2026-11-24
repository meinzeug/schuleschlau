# Benachrichtigungen: unabhängige Webclients

Am 24.11.2026 wurde ein wiederholbarer Ende-zu-Ende-Test für die Glocke,
Lesebelege und die Navigation zur gespeicherten Lernrunde ergänzt. Er startet
ein lokales FastAPI-Backend mit isolierter SQLite-Datenbank und bedient den
Flutter-Webbuild über drei getrennte Chrome-Kontexte bei 390 × 844 Pixeln.
Die Familie, alle Inhalte und die gespeicherte Runde sind künstliche
Testdaten. Die Browser dürfen nur das lokale Testbackend erreichen.

Der Ablauf prüft:

- 60 Nachrichten mit Cursor-Fortsetzung: Beim Öffnen werden sichtbare Karten
  gelesen; unerreichte ältere Nachrichten bleiben ungelesen. Das Glockenmenü
  lädt ältere Karten und quittiert beim Scrollen zusätzlich sichtbare Karten.
- Die Karte „Deine Lernrunde ist bereit“ öffnet die tatsächlich gespeicherte
  Runde. Eine andere Familie darf weder deren Einheit abrufen noch die
  Benachrichtigung quittieren.
- Zwei unabhängig angemeldete Sitzungen desselben Elternkontos sehen denselben
  Lesestand; ein anderes berechtigtes Familienmitglied behält seinen eigenen.
  Auch die Gesamtansicht quittiert beim Scrollen weitere sichtbare Karten.
- Die Lese- und Navigationsvorgänge starten keinen neuen KI-Auftrag. Der
  Test erzeugt keine Pushzustellung und verwendet keine externen KI-Anbieter.

Der Test ist über `qa/run_notebook_local_browser.py` im Browser-Gate
eingebunden. Sein Opt-in verweigert vor dem App-Import eine fremde
`TEST_DATABASE_URL`; die Prüfung läuft nur auf einer isolierten SQLite-DB.
Die Benachrichtigungsregression wurde zusätzlich auf SQLite und isoliertem
PostgreSQL ausgeführt.

Ein ergänzender Versuch mit der installierten, anhand des APK-Hashes
verifizierten produktiven Android-Version 1.38.149+304 auf einem Emulator
konnte wegen wiederholter Hänger der Android-Systemoberfläche unter hoher
VM-Last nicht abgeschlossen werden. Das ausschließlich dafür angelegte
künstliche Konto wurde gelöscht. Daher belegt dieser Lauf weder einen nativen
Gerätewechsel noch FCM-Annahme oder sichtbare Pushzustellung. Die früheren
separaten Pushnachweise behalten ihren jeweils dokumentierten Versions- und
Geräteumfang; der übergeordnete Roadmap-Punkt bleibt offen.
