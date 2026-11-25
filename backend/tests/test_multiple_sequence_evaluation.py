"""A narrow numeric sequence is checked independently of a model's answer key."""

from schulpilot.answer_evaluation import evaluate


def question(prompt="Übung: Die Vielfachen von 5 beginnen mit 5;10;15;20. Welche Zahl kommt als Nächstes?", key="25"):
    return {"type": "short", "prompt": prompt, "answer": key, "accepted": []}


def test_explicit_sequence_is_assessed_and_does_not_disclose_answer():
    assert evaluate(question(), "25")["outcome"] == "correct"
    wrong = evaluate(question(), "23")
    assert wrong["outcome"] == "incorrect"
    assert wrong["method"] == "explicit_multiple_sequence_v1"
    assert "25" not in wrong["reason"]


def test_different_and_multidigit_factors_are_independently_computed():
    q = question("Die Vielfachen von 7 beginnen mit 7; 14; 21. Welche Zahl kommt als Nächstes?", "28")
    assert evaluate(q, "28")["outcome"] == "correct"
    assert evaluate(q, "29")["outcome"] == "incorrect"


def test_ambiguous_or_inconsistent_sequence_and_key_stay_uncertain():
    bad_sequence = question("Die Vielfachen von 5 beginnen mit 5;10;14;20. Welche Zahl kommt als Nächstes?")
    assert evaluate(bad_sequence, "23")["outcome"] == "uncertain"
    assert evaluate(question(key="23"), "24")["outcome"] == "uncertain"
    assert evaluate(question(key="23"), "23")["outcome"] == "uncertain"
    assert evaluate(question(), "etwa fünfundzwanzig")["outcome"] == "uncertain"
    assert evaluate(question("Nenne ein Vielfaches von 5."), "58")["outcome"] == "uncertain"
