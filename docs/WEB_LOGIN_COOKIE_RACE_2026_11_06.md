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
