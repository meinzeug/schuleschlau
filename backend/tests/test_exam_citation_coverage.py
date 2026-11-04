"""A valid quote from the same page must actually evidence the assigned task."""

import copy

import pytest
from schulpilot import exam_review
from schulpilot.providers import ProviderError
from test_exam_review_append import request, second_report, start
from test_exam_reviews import REPORT, finish, no_learning
from test_exam_reviews import paper as paper
from test_exam_reviews import transport as transport


def test_unrelated_but_literal_quote_does_not_replace_task_evidence(paper, transport):
    before = start(paper, transport)
    second_report(transport)
    # This text is genuinely on the cited page, but describes another line.
    transport["output"]["tasks"][0]["sources"][0]["quote"] = "Nenner bleibt 4."
    response = request(paper)
    assert response.status_code == 202
    finish()
    after = paper["client"].get(paper["path"]).json()
    assert after["status"] == "ready" and after["tasks"] == before["tasks"]
    assert after["analysis_batch"]["status"] == "failed"
    assert "Originalaufgabe" in after["analysis_batch"]["error"]
    assert len(transport["calls"]) == 2
    no_learning()


@pytest.mark.parametrize("quotes,valid", [
    (["Lies den Satz", "und erkläre die Bedeutung."], True),
    (["Lies den Satz und", "Satz und erkläre die Bedeutung."], True),
    (["Lies den Satz", "die Bedeutung."], False),
    (["eine andere Zeile"], False),
    (["Die Aufgabe lautet: Lies den Satz und erkläre die Bedeutung."], True),
])
def test_question_is_fully_covered_by_literal_citations(quotes, valid):
    question = "Lies den Satz und erkläre die Bedeutung."
    task = copy.deepcopy(REPORT["tasks"][0])
    task.update(question=question, original_answer="", teacher_feedback="", score_label="",
        sources=[{"ref": "p1", "quote": quote} for quote in quotes])
    report = {"summary": "Künstliche Aufgabe", "uncertainties": [], "tasks": [task]}
    source = {"ref": "p1", "content": question + "\nDie Aufgabe lautet: " + question + "\neine andere Zeile"}
    refs = [{"ref": "p1", "id": "a" * 32, "label": "Künstliche Seite"}]
    if valid:
        assert exam_review.checked_report(report, [source], refs)["tasks"][0]["question"] == question
    else:
        with pytest.raises(ProviderError, match="Originalaufgabe"):
            exam_review.checked_report(report, [source], refs)


def test_long_original_question_can_be_quoted_in_overlapping_parts():
    question = "Zeile " + "abc " * 300 + "Ende."
    first, second = question[:1000], question[950:]
    task = copy.deepcopy(REPORT["tasks"][0])
    task.update(question=question, original_answer="", teacher_feedback="", score_label="",
        sources=[{"ref": "p1", "quote": first}, {"ref": "p1", "quote": second}])
    report = {"summary": "Künstliche Aufgabe", "uncertainties": [], "tasks": [task]}
    result = exam_review.checked_report(report, [{"ref": "p1", "content": question}],
        [{"ref": "p1", "id": "a" * 32, "label": "Künstliche Seite"}])
    assert result["tasks"][0]["question"] == question
