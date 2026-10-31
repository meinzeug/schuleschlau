# Betreiberentscheidungen und technische Umsetzung

Diese Übersicht ordnet widersprüchlich wirkende historische Angaben ein.
Abgefragter Serverstand am 31.10.2026: Release `484a9be`, abgeschlossene
Installation Revision 6. Die Abfrage war lesend und gab keine Schlüssel oder
Familieninhalte aus. Einstellungen können sich danach ändern.

| Thema | Maßgeblicher Auftrag und Stand | Umsetzung beziehungsweise offene Grenze |
| --- | --- | --- |
| Tages-/Wochenzeit | Seit 17.10. sind dies Mindestziele, keine Höchstgrenzen. | Freiwilliges Weiterlernen darf auch danach starten. Gespeicherte Aktivitätssekunden sind maßgeblich; siehe `LEARNING_MODEL.md` und `test_minimum_learning_time.py`. |
| Heftseitenprüfung | Der spätere Auftrag verlangt eine zweite KI-Lesung im konfigurierten Automodus; daneben bleibt manuelle Prüfung möglich. | Installation meldet `automatic`. Neue Installationen starten manuell. Die separate, reservierte Gegenprüfung und ihre Unsicherheiten bleiben in `material_review.py` und `test_material_auto_review.py` nachvollziehbar; kein Modellaufruf allein durch eine Statusabfrage. |
| Fehlerhafte oder unleserliche Seite | Der Auftrag will möglichst keinen unnötigen Stillstand; Unlesbares darf nicht zu erfundenem Wissen werden. | Automodus übernimmt sichere Teile und kennzeichnet Unsicherheiten. Ein technischer Fehler ist kein erfolgreicher Gegencheck; eine vollständig unlesbare Seite erzeugt keinen erfundenen Inhalt. Details und Grenzen: `AFTER_SCHOOL.md`. |
| KI-Anbieter | Free-OpenRouter vom 14.10. und Codex vom 15.10. sind historische Betreiberentscheidungen; der ausdrückliche Wechsel zu bezahltem OpenRouter am 20.10. folgte später. | `provider_config` ID 1 ist die im normalen Anbietercode gelesene Konfiguration: Revision 37, OpenRouter, `openai/gpt-6.1-sol`, `medium`, `free_only=false`, `zdr=true`, Notstopp aus. Ein zweiter gespeicherter Codex-Datensatz ist dadurch kein Beleg für automatischen Fallback. |
| Terra statt Sol | Der Nutzer hat den Wechsel unter der Bedingung erfolgreicher Tests beauftragt. | Die am Stichtag tatsächlich eingestellte Route verwendet weiterhin Sol. Solange ein revisionsgebundener erfolgreicher Vergleich und eine wirksame Änderung nicht belegt sind, wird Terra nicht als aktiviert behauptet und die Route nicht allein wegen älterer Dokumentation umgestellt. |
| Reservierung und Grenzen | Spätere Freigaben erlauben höhere Reservierungen; Reservierung ist keine tatsächliche Rechnung. | Der ausgelesene Hauptdatensatz enthält `reserve_micros=4867499`, `global_limit_micros=100000000` und `max_output_tokens=8000`. Es handelt sich um technische gespeicherte Werte, nicht um einen individuellen Kontostand oder eine bestätigte Abrechnung; effektive Route und Familien-/Kinderlimits werden zusätzlich geprüft. |
| Push | Die vorläufige Sperre im älteren Teil von `APPROVALS.md` wurde für diese Installation durch die spätere Betriebsentscheidung ersetzt. | Installation meldet `push_approved=true`. Elternfreigabe, Geräte-Opt-in und neutrale Payload bleiben erforderlich. FCM-Annahme ist keine beobachtete native Zustellung. |
| Datenfreigabe | Die Betreiberfreigabe vom 14.10. bleibt bestehen; spätere Anbieter- und Pushentscheidungen sind getrennt zu betrachten. | Installation meldet `real_data_approved=true`. Eine Betreiberentscheidung ist kein Ersatz für eine externe Vertrags- oder Rechtsprüfung. |
| Marke und Domain | Nutzerentscheidung: SchuleSchlau als App-Name; bisherige Adresse behalten. | `schulpilot.dorfspy.de` bleibt aktiv. Keine Registrierung von `schuleschlau.com` und kein Domainumzug werden daraus abgeleitet. |
| Android | Direct und Play sind getrennte Wege; physischer Androidtest ist zurückgestellt. | Der aktive Release ist `1.38.54+209`. Eine nächste Direct-APK benötigt einen höheren Versionscode; ein signiertes Artefakt belegt weder Installation noch sichtbare Pushzustellung. |

Diese Übersicht dokumentiert den vorgefundenen Zustand; sie verändert weder
Provider, Kosten, Freigaben noch Lernstände. Historische Messungen und
Freigaben in `STATUS.md`, `APPROVALS.md` und älteren Runbooks bleiben datiert
erhalten. Fehlende Vergleichs- oder Geräteevidenz bleibt offen.
