"""Artificial examples of the rule; no private learner content."""

from fractions import Fraction

import pytest
from schulpilot.fraction_comparison_rule import evidence, plan, rule

RULE = (
    "1. Schritt: Finde das kleinste gemeinsame Vielfache (kgV) von den Nennern!\n"
    "2. Schritt: Erweitere beide Brüche auf den gleichen Nenner!\n"
    "3. Schritt: Vergleiche die Zähler!"
)


def test_complete_ordered_procedure_returns_literal_excerpt():
    content = "Künstliche Lernseite\n" + RULE + "\nBeispiel: 1/4 und 2/3."
    quote = evidence(content)
    assert quote is not None and quote in content
    assert "Finde" in quote and quote.endswith("Zähler")


@pytest.mark.parametrize("content", [
    "Brüche vergleichen. Das kgV der Nenner hilft.",
    "Finde das kgV der Nenner. Vergleiche die Zähler.",
    "Vergleiche die Zähler. Erweitere beide Brüche auf den gleichen Nenner. Finde das kgV der Nenner.",
    "Finde das kgV der Nenner. Erweitere beide Brüche auf den gleichen Nenner. Vergleiche nicht die Zähler.",
    "Falsch: Finde das kgV der Nenner. Erweitere beide Brüche auf den gleichen Nenner. Vergleiche die Zähler.",
    "Falsches Vorgehen:\nFinde das kgV der Nenner. Erweitere beide Brüche auf den gleichen Nenner. Vergleiche die Zähler.",
    "Finde das kgV der Nenner. Erweitere beide Brüche auf den gleichen Nenner. Vergleiche die Zähler. Das ist falsch!",
    "Finde das kgV der Nenner.\n\nEin anderes Thema. Erweitere beide Brüche auf den gleichen Nenner. Vergleiche die Zähler.",
    "Finde das kgV der Nenner. Erweitere die Brüche auf den gleichen Nenner. Vergleiche die Nenner.",
    "Finde das kgV der Nenner. " + "Anderer Abschnitt. " * 20 + "Erweitere beide Brüche auf den gleichen Nenner. Vergleiche die Zähler.",
])
def test_unproven_restricted_or_incomplete_procedure_is_not_evidence(content):
    assert evidence(content) is None


def test_new_questions_are_calculated_and_do_not_repeat_originals_or_history():
    content = RULE + "\nBeispiel: 1/4 und 2/3."
    previous = ["Welcher Bruch ist größer: 2/5 oder 1/2? Gib den größeren Bruch an."]
    tasks = plan(content, previous, 5, "synthetic")
    assert len(tasks) == 5 and plan(content, previous, 5, "synthetic") == tasks
    seen = set()
    for task in tasks:
        proof = task["comparison"]
        left, right = proof["left"], proof["right"]
        assert left not in ([1, 4], [2, 3]) and right not in ([1, 4], [2, 3])
        assert Fraction(task["answer"]) == max(Fraction(*left), Fraction(*right))
        assert proof["common_denominator"] <= 24
        assert all(proof["common_denominator"] % pair[1] == 0 for pair in (left, right))
        pair = tuple(sorted((tuple(left), tuple(right))))
        assert pair not in seen and pair != ((1, 2), (2, 5))
        seen.add(pair)
        assert task["source_excerpt"] in content


def test_no_new_questions_are_planned_from_a_topic_or_an_invalid_request():
    assert plan("Brüche vergleichen", [], 2, "x") == []
    assert plan(RULE, [], True, "x") == []
    assert plan(RULE, [], 6, "x") == []
    assert plan(RULE, [None], 2, "x") == []


def test_old_comparison_with_leading_zeroes_remains_excluded():
    first = plan(RULE, [], 1, "synthetic")[0]
    left, right = first["comparison"]["left"], first["comparison"]["right"]
    previous = f"Vergleiche {left[0]:02d}/{left[1]:02d} und {right[0]:02d}/{right[1]:02d}."
    next_task = plan(RULE, [previous], 1, "synthetic")[0]
    assert next_task["comparison"] != first["comparison"]


def test_numbered_safe_blocks_have_three_separate_literal_quotes():
    content = ("Künstliche Heftseite\n\n1. Schritt: Finde das kgV von den Nennern!\n\n"
        "Beispiel: kgV(2;3)=6.\n\n2. Schritt: Erweitere beide Brüche auf den „kgV-Nenner“.\n\n"
        "3. Schritt: Vergleiche die Zähler!\n\n1/3 und 3/4.")
    found = rule(content)
    assert found and found["kind"] == "numbered_safe_blocks" and len(found["quotes"]) == 3
    assert all(quote in content for quote in found["quotes"])
    assert len(plan(content, [], 2, "synthetic")) == 2


@pytest.mark.parametrize("content", [
    "1. Schritt: Finde das kgV der Nenner.\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.",
    "Falsch:\n\n1. Schritt: Finde das kgV der Nenner.\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.\n\n3. Schritt: Vergleiche die Zähler.",
    "1. Schritt: Finde das kgV der Nenner.\n\nNicht machen!\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.\n\n3. Schritt: Vergleiche die Zähler.",
    "1. Schritt: Finde das kgV der Nenner.\n\n3. Schritt: Vergleiche die Zähler.\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.",
    "1. Schritt: Finde das kgV der Nenner.\n\n2. Schritt: Erweitere beide Brüche nicht auf den gleichen Nenner.\n\n3. Schritt: Vergleiche die Zähler.",
    "1. Schritt: Finde das kgV der Nenner.\n\n1. Schritt: Eine andere Aufgabe.\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.\n\n3. Schritt: Vergleiche die Zähler.",
    "1. Schritt: Finde das kgV der Nenner.\n\n2. Schritt: Erweitere beide Brüche auf den gleichen Nenner.\n\n3. Schritt: Vergleiche die Zähler.\n\nFalsch: Dieses Vorgehen nicht benutzen.",
    "1. Schritt: Finde das kgV der Nenner. 1. Schritt: Etwas anderes. 2. Schritt: Erweitere beide Brüche auf den gleichen Nenner. 3. Schritt: Vergleiche die Zähler.",
])
def test_incomplete_contradicted_or_reordered_numbered_blocks_do_not_authorize_rule(content):
    assert rule(content) is None and plan(content, [], 1, "synthetic") == []
