# Größenprüfung für Heftausschnitte

Die Anzeige eines privaten Heftausschnitts liest weiterhin nur die berechtigte,
revisionsgebundene Originaldatei. Für neue Uploads gilt eine Obergrenze von
16.000.000 Bildpunkten; ältere oder beschädigte gespeicherte Dateien müssen
jedoch nicht durch den aktuellen Decoder gegangen sein. Bisher hat die
Ausschnittfunktion vor dem `crop` nicht selbst geprüft, ob die Bildabmessungen
diese Grenze einhalten. Eine kleine komprimierte Datei kann beim Dekodieren
wesentlich mehr Arbeitsspeicher benötigen.

Die Prüfung liest zunächst nur den Bildkopf und weist größere Quellen mit
HTTP 422 ab, bevor sie Pixel für den Ausschnitt lädt. Die Antwort verweist auf
das vollständige Heftfoto. Genau 16.000.000 Bildpunkte bleiben zulässig. Die
Datei wird dabei weder geändert noch gelöscht; die bestehende Rechteprüfung,
Revisionsbindung, Dateigrößenbegrenzung und der gemeinsame Verarbeitungsplatz
bleiben erhalten. Auch eine als Fehler konfigurierte Pillow-Bildwarnung soll
als kontrollierte Ablehnung behandelt werden.

Die Tests verwenden ausschließlich künstliche Bilder. Die Quellen-,
Berechtigungs- und Fotoeingangssuite bestand mit 52 Fällen auf SQLite (einer
übersprungen) und 53 auf isoliertem PostgreSQL. Der endgültige Grenzfall mit
zu Fehlern verschärften Warnungen bestand gesondert auf beiden Datenbanken.
Die Kontrolle der Bildabmessung und der gezielte Grenzfall sind keine produktive Lastmessung und
belegen nicht den vollständigen Speicherschutz anderer Bildpfade, mehrerer
API-Prozesse oder den produktiven Rückweg. Der übergeordnete Kapazitätspunkt
bleibt offen.

Bei Profilbildern wird die bestehende Obergrenze von acht Megapixeln bereits
vor der Pixelverarbeitung geprüft. Wenn jedoch Pillow-Warnungen als Fehler
konfiguriert sind, konnte ein noch größeres Bild vor dieser Prüfung eine
unkontrollierte Ausnahme erzeugen. Der Profilbildpfad behandelt auch diese
Warnung als ungültige Eingabe; es werden weder Freigaben geändert noch Bilder
gespeichert. Der künstliche Regressionstest schlug mit dem bisherigen Verhalten
fehl und prüft die kontrollierte Ablehnung.
