"""Artificial equations split across TeX spans remain literal student work."""

import pytest
from schulpilot.db import DB, Material
from schulpilot.exam_review import arithmetic_warnings
from schulpilot.exam_review_models import ExamReview
from sqlalchemy import select
from test_exam_reviews import paper as paper_fixture
from test_exam_reviews import ready
from test_exam_reviews import transport as transport_fixture


@pytest.fixture
def paper(api, household):
    yield from paper_fixture.__wrapped__(api, household)


@pytest.fixture
def transport(monkeypatch):
    return transport_fixture.__wrapped__(monkeypatch)


@pytest.mark.parametrize(('answer', 'expected'), [
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{8}\)', True),
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{4}\)', False),
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) vielleicht = \(\frac{3}{8}\)', False),
    (r'\(x\) + \(\frac{2}{4}\) = \(\frac{3}{8}\)', False),
    (r'\(\frac{1}{0}\) + \(\frac{2}{4}\) = \(\frac{3}{8}\)', False),
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{8}', False),
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{\),', False),
    (r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{8}\) vermutlich', False),
])
def test_only_complete_numeric_equations_over_multiple_math_spans_are_checked(answer, expected):
    warnings = arithmetic_warnings(answer)
    assert bool(warnings) is expected
    if expected:
        assert len(warnings) == 1
        assert warnings[0]['expression'] == answer
        assert 'Links steht 3/4, rechts 3/8' in warnings[0]['message']


def test_review_keeps_original_and_adds_separate_warning(paper, transport):
    question = 'Berechne 1/4 + 2/4.'
    answer = r'\(\frac{1}{4}\) + \(\frac{2}{4}\) = \(\frac{3}{8}\)'
    with DB.begin() as db:
        db.get(Material, paper['material_id']).content = question + '\n' + answer
    transport['output']['tasks'][0].update(question=question, original_answer=answer, teacher_feedback='',
        score_label='', uncertainties=['Die Handschrift ist zu prüfen.'], sources=[{'ref': 'p1', 'quote': question}])
    response = ready(paper, transport)
    task = response['tasks'][0]
    assert task['original_answer'] == answer and task['uncertainties'] == ['Die Handschrift ist zu prüfen.']
    assert len(task['arithmetic_warnings']) == 1
    with DB() as db:
        saved = db.scalar(select(ExamReview).where(ExamReview.exam_id == paper['exam_id']))
        assert saved.report['tasks'][0]['original_answer'] == answer
        assert 'arithmetic_warnings' not in saved.report['tasks'][0]
