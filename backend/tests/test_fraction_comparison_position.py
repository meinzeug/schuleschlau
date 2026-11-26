"""Finite comparison views are private reading state, never learner evidence."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from schulpilot import visual_positions
from schulpilot.schulbuddy_graphics import _phase
from schulpilot.schulbuddy_schemas import BuddyScope


def step():
    return {"id": "fc_test", "reference": {"id": "math.fraction.comparison", "version": 1},
        "presentation": {"blocks": [{"kind": "fraction", "numbers": pair} for pair in
            ([1, 3], [3, 4], [4, 12], [9, 12])]}}


@pytest.mark.parametrize("phase,expected", [
    ("comparison-original", [[1, 3], [3, 4]]),
    ("comparison-common", [[4, 12], [9, 12]]),
])
def test_buddy_receives_only_visible_checked_comparison_state(phase, expected):
    saved = step()
    block = saved["presentation"]["blocks"][0]
    assert _phase(block, phase, step=saved, index=0) == {
        "phase": phase, "fractions": expected, "derived_locally": True}
    assert BuddyScope(unit_id="u", explanation_kind="question", question_id="q", explanation_step_id="fc_test",
        graphic_index=0, graphic_phase=phase).graphic_phase == phase
    with pytest.raises(HTTPException):
        _phase(block, phase, step=saved, index=1)
    wrong = step()
    wrong["reference"]["id"] = "math.fraction.part_whole"
    with pytest.raises(HTTPException):
        _phase(block, phase, step=wrong, index=0)


@pytest.mark.parametrize("phase", ["comparison-original", "comparison-common"])
def test_position_is_limited_to_matching_disclosed_comparison_step(monkeypatch, phase):
    saved = step()
    monkeypatch.setattr(visual_positions, "unit_data", lambda *args, **kwargs: {"explanation_steps": [saved]})
    value = visual_positions.Position(explanation_kind="intro", explanation_step_id="fc_test", graphic_phase=phase)
    assert visual_positions.checked(None, None, SimpleNamespace(role="parent"), value)["graphic_phase"] == phase
    saved["reference"]["id"] = "math.fraction.part_whole"
    with pytest.raises(HTTPException):
        visual_positions.checked(None, None, SimpleNamespace(role="parent"), value)
