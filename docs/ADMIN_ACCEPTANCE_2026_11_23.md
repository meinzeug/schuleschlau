# Betriebsadministration: erneute technische Prüfung vom 23.11.2026

Die Prüfung verwendet ausschließlich künstliche Konten und Daten. Sie betrifft
den Entwicklungsstand auf Basis von Commit `e11cb57` einschließlich der in
`admin_beta_applications.dart` geänderten Beta-Kostenanzeige und der ergänzten
Tests. Es gab keine echten KI- oder Zahlungsanbieteraufrufe und keine Änderungen
an produktiven Konten oder Betreibereinstellungen.

## Ergebnisse

- `test_admin_users.py`, `test_admin_user_races.py`,
  `test_admin_ux_controls.py`, `test_child_cost_controls.py`,
  `test_child_cost_freshness.py`, `test_provider_cost_preflight.py`,
  `test_parent_audit_ux90.py`, `test_beta.py` und
  `test_installation_site_cas.py`: SQLite **136 bestanden, 9 ausgelassen**;
  isoliertes PostgreSQL **144 bestanden, 1 ausgelassen**. Ausgelassene Fälle
  gelten jeweils nicht als auf der betreffenden Datenbank bestanden.
- Private Originalbilder, Noten und Schulbuddy-Kontexte: je **3 bestanden**
  auf SQLite und isoliertem PostgreSQL.
- `test_review_consent_stale_identity.py`: SQLite **2 bestanden, 4
  ausgelassen**, isoliertes PostgreSQL **6 bestanden**. Die PostgreSQL-Fälle
  prüfen konkurrierende Freigabe- und Seitenprüfänderungen.
- Sieben Flutter-Dateien zur Administration und Beta-Oberfläche: **117
  bestanden**. Die künstlichen Fälle umfassen auch 320-/390-Pixel-Ansichten,
  vergrößerte Schrift, Entwürfe, widerrufene Sitzungen und den Notfallstopp.
- Chrome-Webrunner für `test/admin_workspace_test.dart`,
  `test/admin_child_costs_107_test.dart`, `test/admin_users_screen_test.dart`
  und `test/beta_frontend_test.dart`: **80 bestanden**.
- Die zusätzlichen Beta-Kostenfälle prüfen eine abgeschnittene Modellliste,
  eine serverseitige Kürzung sowie den kleinsten gespeicherten positiven
  USD-Betrag. Der kombinierte lokale Beta-Browserlauf ist gesondert in
  [BETA_BROWSER_2026_11_23.md](BETA_BROWSER_2026_11_23.md) beschrieben.

Die Tests prüfen Rollen- und Familienrechte, wirksame Kinder-/Familien- und
Systemgrenzen, Reservierungen, simulierte Kostenbelege, revisionsgebundene
Änderungen, Audits, konkurrierende Zugriffe und explizite Notstoppbedienung.
Die getesteten Mock-Antworten sind kein Nachweis der Erreichbarkeit eines
Anbieters, tatsächlicher Preise oder der Verwendung auf physischen Geräten.
Eine unabhängige Sicherheitsprüfung bleibt ein separater Roadmap-Punkt.

Die beiden Datenbankläufe verwenden durch die vorhandenen Testfixtures getrennte
Datenbanken; `scripts/test_postgres.py` erzeugt einen kurzlebigen Cluster.
Die konkreten Aufrufe entsprechen den Modullisten oben und den reproduzierbaren
Kommandos in [ADMIN_ACCEPTANCE_2026_11_04.md](ADMIN_ACCEPTANCE_2026_11_04.md),
ergänzt um `test_beta.py`, `test_installation_site_cas.py` und
`test_review_consent_stale_identity.py`.
