# Verspätete Loginantwort im Browser: offener Kontowechsel-Race

Ein isolierter Regressionstest zeigt eine zusätzliche Grenze der lokalen
Authentifizierungsrevision: Die Revision verhindert, dass Dart eine
überholte Antwort übernimmt. Sie verhindert nicht, dass der Browser den
`HttpOnly`-Cookie aus dieser HTTP-Antwort bereits übernommen hat.

In `backend/tests/test_login_cookie_race_evidence.py` beantwortet die echte
FastAPI-Anmeldung zwei künstliche Elternkonten in umgekehrter Reihenfolge. Die
erste erfolgreiche Antwort wird vor dem Senden ihrer Header zurückgehalten;
die zweite trifft vorher ein. `/auth/me` zeigt zuerst das zweite Konto. Nach
Freigabe der ersten Antwort zeigt derselbe echte Chrome-Browser jedoch das
erste Konto. Beide Antworten waren erfolgreich. Der Test verwendet ein
lokales, bei jedem Lauf neu erzeugtes SQLite und künstliche Zugangsdaten. Er
ruft keine Produktionssysteme oder Provider auf. Es ist ein Browser-/API-Test,
kein Flutter-, Android-, Google- oder Mehrgerätetest. Er dokumentiert die
aktuelle Schwäche und ist kein Nachweis einer Fehlerbehebung.

```sh
TMPDIR=/dev/shm LOGOUT_COOKIE_RACE_BROWSER=1 PYTHONPATH=backend \
  /home/dennis/schulpilot/.venv/bin/pytest -q \
  backend/tests/test_login_cookie_race_evidence.py
```

Der vorhandene Browser-Opt-in verweigert vor dem Import eine explizite
Testdatenbank und erzeugt eine isolierte SQLite-Datenbank. Der Test besteht,
wenn das fehlerhafte Verhalten erfolgreich reproduziert wurde. Wird die
Schwäche behoben, muss die Erwartung umgestellt werden; ein grüner Lauf dieser
Fassung ist **kein** Sicherheitsnachweis.

## Folgerung für die offene Lernplansperre

Ein bloßes `authenticationPending`-Flag, das bei Abbruch oder dem neueren
Login auf `false` gesetzt wird, genügt nicht: Ein alter Transport kann später
noch einen neuen Cookie setzen. Ein späterer Lernplan-GET könnte somit mit
anderer Serversitzung laufen als die von der Flutter-Ansicht angenommene.
Ausstehende Cookie-setzende Transporte müssten bis zum tatsächlichen Ende
berücksichtigt und ungewisse Sitzungen ausdrücklich bestätigt werden. Ein
Lesen darf keine Anmeldung oder Mutation automatisch wiederholen.

Eine belastbare Lösung muss auch andere Tabs, App-Neustart, Logout, Demo,
Google-Start und -Abschluss, erfolgreiche und fehlgeschlagene Logins,
verzögerte Antworten und ältere Clients behandeln. Der beobachtete Race
wurde weder durch den Lernplan-Fix noch durch den gesonderten Logout-Fix
behoben. Bis eine vollständige Lösung samt echten Cookie-Racetests existiert,
bleibt dieser Punkt offen.

## Konkreter Entwurf: serverseitig widerrufbare Generation

Ein möglicher Fix benötigt einen gemeinsamen, serverseitig verwalteten
Browserkontext und eine monoton vergebene Anmeldegeneration. Der Kontext ist
kein Ersatz für eine Sitzung und darf für sich allein weder Inhalte noch
Anmeldung autorisieren. Bei einer ausdrücklich begonnenen Kontoaktion wird
unter Datenbanksperre eine neue Generation reserviert. Das abschließende
Ausstellen der Sitzung muss dieselbe Generation in derselben Transaktion
prüfen; bei einer neueren Kontoaktion darf die alte keine gültige Sitzung mehr
erzeugen. Bereits ausgestellte ältere Sitzungen dieses Browserkontexts müssen
serverseitig ungültig werden. Auf erfolgreichen Google- und Demo-Zugängen und
beim Logout muss dieselbe Regel gelten; ein lokaler Flutter-Zähler reicht
nicht. Die Reihenfolge bedeutet dabei zunächst **Serverannahmereihenfolge**;
sie beweist nicht, welche Aktion in zwei Tabs der Mensch zuerst ausgelöst
hat.

Eine bereits gesendete alte Antwort kann den Cookie trotzdem später ersetzen:
Der Browser speichert Set-Cookie außerhalb der Flutter-Kontrolle. Die ältere
Generation muss beim nächsten geschützten Request serverseitig abgelehnt
werden. Dadurch wird ein falscher Kontoübergang verhindert; die neuere gültige
Sitzung kann im Browser dennoch verloren gehen und eine bewusste erneute
Anmeldung erforderlich werden. Diese Verfügbarkeitsgrenze darf nicht als
verlustfreie Wiederherstellung ausgegeben werden.

Zusätzlich ist ein an die aktuell angezeigte Sitzung gebundener,
nicht-autorisierender Erwartungswert für geschützte Requests zu prüfen: Der
Server vergleicht ihn mit der durch den HttpOnly-Cookie authentifizierten
Sitzung, bevor er private Daten zurückgibt oder ändert. Ein anderer aktiver
Tab darf nicht still den Benutzer der dargestellten Ansicht austauschen. Ein
Sitzungsbezeichner allein ist kein Zugangstoken und ersetzt weder bestehende
Sitzungs- noch Familienrechte. Für direkten Bild-/PDF-Abruf, Downloads,
SSE/Push, Serviceworker, Kaltstart und native Bearerzugänge ist eine jeweils
passende Bindung erforderlich; unbeprüfte Ausnahmen würden die Zusicherung
aufheben.

Vor einer Implementierung sind folgende Punkte zu lösen und nachzuweisen:

- Wie entsteht bei einem erstmalig anonymen Webbesuch eine gemeinsame
  Browserbindung, wenn zwei Tabs gleichzeitig initialisieren und beide
  Set-Cookie-Antworten in beliebiger Reihenfolge ankommen? Auch Browserdaten-
  Löschung, private Fenster und getrennte Android-/Systembrowser sind zu
  beachten. Ein zufällig vom Client gelieferter Wert ist keine Berechtigung.
- Transaktionen müssen unter PostgreSQL die Generation bei konkurrierender
  Reservierung, Sitzungserstellung und Widerruf atomar sperren und erneut
  prüfen. Netzwerkabbruch, Abbruch nach Commit und erneute Anfrage dürfen
  weder alte Sitzungen wiederbeleben noch ein automatisches Login auslösen.
- Migration und Release-Reihenfolge müssen für vorhandene gültige Sitzungen
  und gecachte Webclients ausdrücklich definiert werden. Ein alter Client
  darf die neue Bindung nicht durch Weglassen eines Headers umgehen; zugleich
  darf eine neue obligatorische Prüfung nicht unbemerkt alle bestehenden
  Download-, Google-, Setup- und nativen Abläufe beschädigen.
- Tests müssen künstliche echte HTTP-Cookies und mindestens zwei Browsertabs
  mit kontrolliert vertauschten Antworten verwenden: beide Login-Reihenfolgen,
  Fehler und Abbruch, ältere Antwort nach neuem Login und nach Logout,
  Google-Start/-Abschluss, Demo sowie einen Requests-vorher-und-nachher-Test
  auf private Lesung **und** Mutation. Flutter-Zustand und native Trennung
  benötigen eigene Prüfungen. Der obige Test ist dafür nur der Ausgangspunkt.

Der Entwurf ist nicht implementiert; insbesondere sind atomare
Browserbootstrap-Bindung und die kontrollierte Behandlung alter Clients
weiter offen. Eine sofortige pauschale Änderung von `authenticated()` oder
`beginAuthentication()` wäre daher nicht ausreichend geprüft.

## Begrenzte zusätzliche Konto-Abwehr

Die nachträglich ergänzte optionale Kontoprüfung für die gemeinsame
Flutter-API wird in `ACCOUNT_ASSERTION_2026_11_06.md` beschrieben. Der echte
Browsertest weist weiterhin den Cookie-Wechsel nach und prüft zusätzlich,
dass ein mit dem neueren Konto markierter Lese- oder Logout-Request nach dem
Wechsel zurückgewiesen wird. Die Cookie-Generation selbst bleibt offen.
