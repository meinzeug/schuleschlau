"""Feedback markers must belong to the unit and child being resolved."""

from types import SimpleNamespace

from schulpilot.learning import feedback_history_available, pending_feedback, unread_feedback_ids


def test_foreign_and_malformed_markers_do_not_hide_or_invent_feedback():
    unit = SimpleNamespace(id="unit", child_id="child", questions=[{"id": "q", "explanation": "hint"}])
    attempt = SimpleNamespace(id="attempt", question_id="q", answer="answer", outcome="correct",
                              assisted=False, created=1, evaluation={})

    def event(kind, *, child="child", unit_id="unit", detail=None):
        return SimpleNamespace(child_id=child, unit_id=unit_id, kind=kind,
                               detail={"attempt_id": "attempt"} if detail is None else detail)

    own_pending = event("feedback_pending")
    foreign_markers = [event("feedback_pending", child="other"),
                       event("feedback_pending", unit_id="other"),
                       event("feedback_pending", detail=[])]
    assert pending_feedback(unit, [attempt], foreign_markers) is None
    assert unread_feedback_ids(unit, [attempt], foreign_markers) == set()
    assert not feedback_history_available(unit, [attempt], foreign_markers)

    foreign_seen = [event("feedback_seen", child="other"), event("feedback_seen", unit_id="other"),
                    event("feedback_seen", detail=[])]
    events = [own_pending, *foreign_seen]
    assert pending_feedback(unit, [attempt], events)["attempt_id"] == "attempt"
    assert unread_feedback_ids(unit, [attempt], events) == {"attempt"}
    assert not feedback_history_available(unit, [attempt], events)

    events.append(event("feedback_seen"))
    assert pending_feedback(unit, [attempt], events) is None
    assert unread_feedback_ids(unit, [attempt], events) == set()
