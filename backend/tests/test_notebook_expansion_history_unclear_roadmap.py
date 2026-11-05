"""Safety contract for unparseable historical expansion exercises."""
import pytest
from schulpilot import notebook_fraction_expansions as planner
from schulpilot.math_tasks import _task
from test_notebook_fraction_expansions import prepared


@pytest.mark.parametrize("old_question", [
    r"Erweitere den Bruch \frac{1}{2} mit dem Faktor 2.",
    "Erweitere den Bruch 1/2 wie auf dem Bild.",
    "Erweitere ein Halb mit zwei.",
    "Erweitere 2 : 3 mit 2.",
    "Kürze 1/2 und erweitere 2/3 mit 2.",
    "Erweitere 1/2 mit 2 und addiere 3/4 + 2/5.",
    "Erweitere 1/2 und 2/3 mit 2.",
    "Erweitere 1/2 mit dem Faktor 2 oder 3.",
    "Erweitere 1/2 mit 2 oder drei.",
    "Erweitere 1/2 mit 2 und dem Dreifachen.",
    "Multipliziere Zähler und Nenner von 1/2 jeweils mit 3. Welcher Bruch entsteht?",
    "Verdopple Zähler und Nenner von 1/2.",
    "Nimm Zähler und Nenner von 1/2 jeweils mal 3.",
    "Ergänze zu einem gleichwertigen Bruch: 2/3 = ?/12.",
    "Finde einen gleichwertigen Bruch zu 2/3 mit Nenner 12.",
    "Schreibe 1/2 so, dass der Nenner 6 beträgt.",
])
def test_unclear_historical_expansion_does_not_generate_new_practice(household, old_question):
    _, payload, *_ = prepared(household, entry=False)
    payload["previous_prompts"] = [old_question]
    with pytest.raises(ValueError, match="nicht sicher vergleichen"):
        planner.prepare(planner.with_history(payload, [old_question]))


@pytest.mark.parametrize("old_question", [
    "Erweitere deinen Wortschatz um 3 passende Wörter.",
    "Erweitere das Bild um 2 blaue Kreise.",
    "Erweitere die Übersicht der Zählerstände um 3 Werte.",
    "Erweitere das Dreieck mit dem Faktor 3.",
    "Erweitere die Strecke von 3 cm mit dem Faktor 2.",
    "Warum bleibt der Wert eines Bruchs beim Erweitern gleich?",
    "Was bedeutet es, Zähler und Nenner mit derselben Zahl zu multiplizieren?",
    "Kürze den Bruch 1/2 vollständig.",
    "Halbiere Zähler und Nenner von 2/4.",
    "Was haben die gleichnamigen Brüche 1/5 und 3/5 gemeinsam?",
    "Schreibe 2/4 so, dass der Nenner 2 beträgt.",
    "Wie viele Kilometer sind 3 Meter?",
])
def test_unrelated_or_number_free_history_does_not_block(household, old_question):
    _, payload, *_ = prepared(household, entry=False)
    history = planner.with_history(payload, [old_question])
    assert history[planner.HISTORY_KEY]["unknown"] is False
    assert len(planner.prepare(history)[planner.KEY]["tasks"]) == 2


def test_known_exact_expansion_is_excluded_without_blocking(household):
    _, payload, *_ = prepared(household, entry=False)
    old = _task("expand", (1, 2, 2), "apply")[0]
    history = planner.with_history(payload, [old])
    assert history[planner.HISTORY_KEY]["unknown"] is False
    assert [1, 2, 2] in history[planner.HISTORY_KEY]["signatures"]
    plan = planner.prepare(history)[planner.KEY]
    assert all(planner.expansion._planned(task, "apply") != (1, 2, 2) for task in plan["tasks"])
