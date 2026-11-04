"""Prompt guidance is not a substitute for deterministic validation."""

import pytest
from schulpilot import package_transport
from schulpilot.schemas import Question


def question(prompt, answer):
    return {'id': 'q1', 'type': 'short', 'prompt': prompt, 'answer': answer,
        'options': [], 'accepted': [], 'hints': ['Vergleiche Zähler und Nenner.'],
        'explanation': 'Beide Zahlen gehören zusammen.'}


def test_subject_specific_package_guidance_requires_factor_in_actual_question():
    math = package_transport.rules({'selected_groups': [{'subject': 'Mathematik'}]}, indexed_choices=False)
    other = package_transport.rules({'selected_groups': [{'subject': 'Deutsch'}]}, indexed_choices=False)
    assert 'free-answer fraction expansion MUST state one explicit positive integer factor IN THE QUESTION' in math
    assert 'intermediate reduction step MUST state one explicit positive integer divisor IN THE QUESTION' in math
    assert 'MATH:' not in other


@pytest.mark.parametrize(('prompt', 'answer'), [
    ('Erweitere 1/2.', '2/4'),
    ('Kürze 6/12 in einem Schritt.', '3/6'),
])
def test_ambiguous_unplanned_questions_are_still_rejected(prompt, answer):
    with pytest.raises(ValueError, match='mehrdeutig'):
        Question.model_validate(question(prompt, answer))


def test_explicit_factor_and_full_reduction_keep_existing_strict_checks():
    Question.model_validate(question('Erweitere 1/2 mit dem Faktor 2.', '2/4'))
    Question.model_validate(question('Kürze 6/12 vollständig.', '1/2'))
    with pytest.raises(ValueError):
        Question.model_validate(question('Erweitere 1/2 mit dem Faktor 2.', '3/6'))
