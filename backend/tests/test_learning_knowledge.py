"""Synthetic controller trace, original errors, distinct goals and later recall."""

import copy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from schulpilot import coaching
from schulpilot.db import (
    DB,
    Attempt,
    Child,
    LearningUnit,
    Material,
    Subject,
    SubjectAlias,
    UnitCoaching,
    UnitSource,
    now,
)
from schulpilot.learning_knowledge import evidence
from sqlalchemy import select
from test_adaptive_plan import action, session, submit
from test_adaptive_plan import fraction_profile as original_profile


@pytest.fixture
def profile(api, household):
    yield from original_profile.__wrapped__(api, household)


def test_full_fraction_trace_retains_errors_and_schedules_distinct_later_recall(profile):
    client, uid, mid, _, _, child = profile
    submit(client, uid, "sum", "2/9")
    assert action(client, uid, "review_prerequisite", "trace-probe-0001").status_code == 200
    probe = session(client, uid)["action"]["question_id"]
    submit(client, uid, probe, "2/6", key="trace-probe-answer-0001")
    assert action(client, uid, "visual_example", "trace-example-0001").status_code == 200
    assert action(client, uid, "check_understanding", "trace-fresh-0001").status_code == 200
    fresh = session(client, uid)["action"]["question_id"]
    submit(client, uid, fresh, "3/8", key="trace-fresh-answer-0001")
    knowledge = client.get(f"/api/units/{uid}/learning-session/knowledge").json()
    by_label = {g["label"]: g for g in knowledge["long_term"]}
    assert by_label["Brüche addieren"]["independent"] == 1
    assert by_label["Brüche addieren"]["needs_practice"] == 1
    assert by_label["Gleichwertige Brüche erkennen"]["independent"] == 1
    assert by_label["Brüche addieren"]["confidence"] != "repeated_recall"
    assert by_label["Brüche addieren"]["review_due"]
    # A reload only derives evidence. It does not manufacture another check day.
    assert client.get(f"/api/units/{uid}/learning-session/knowledge").json() == knowledge
    with DB.begin() as db:
        for attempt in db.scalars(select(Attempt).where(Attempt.unit_id == uid)):
            attempt.created = int(now()) - 9 * 86400
        template = copy.deepcopy(db.get(LearningUnit, uid).questions[0])
        revision = db.get(Material, mid).revision
    for day, prompt, answer in ((-8, "Berechne 2/5 + 1/10.", "1/2"),
            (-4, "Berechne 1/4 + 1/6.", "5/12"), (0, "Berechne 1/3 + 1/12.", "5/12")):
        with DB.begin() as db:
            q = dict(template, id="recall", prompt=prompt, answer=answer, explanation=prompt + " Ergebnis: " + answer)
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Erinnere dich an die gemeinsame Einteilung.", questions=[q],
                learning_root_id=uid, followup_of=uid, round_kind="spaced_review", introduction_seen=True,
                provider="openai", model="synthetic-model-fixture", synthetic=False)
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=revision))
            check_id = unit.id
        assert client.post(f"/api/units/{check_id}/start").status_code == 200
        result = submit(client, check_id, "recall", answer, key=f"trace-later-answer-{abs(day):04}")
        assert result["outcome"] == "correct" and not result["assisted"]
        with DB.begin() as db:
            attempt = db.get(Attempt, result["attempt_id"])
            attempt.created = int(now()) + day * 86400
    with DB() as db:
        states = evidence(db, db.get(LearningUnit, uid), [db.get(Material, mid)])
        state = next(g for g in states if g["label"] == "Brüche addieren")
        assert state["independent"] == 4 and state["needs_practice"] == 1
        assert state["confidence"] == "repeated_recall"
        assert len(state["successful_check_dates"]) == 3
        zone = ZoneInfo(db.get(Child, child["id"]).preferences.get("timezone", "Europe/Berlin"))
        assert state["review_due"] >= (datetime.fromtimestamp(now(), zone).date() + timedelta(days=7)).isoformat()
    # A corrected source keeps historical practice without asserting current mastery.
    with DB.begin() as db:
        db.get(Material, mid).revision += 1
    assert not client.get(f"/api/units/{uid}/learning-session/knowledge").json()["source_valid"]


def test_repeated_failure_after_help_finishes_without_a_fourth_attempt(profile):
    client, uid, _, _, _, _ = profile
    submit(client, uid, "sum", "2/9")
    action(client, uid, "review_prerequisite", "failure-probe-0001")
    probe = session(client, uid)["action"]["question_id"]
    submit(client, uid, probe, "2/6", key="failure-probe-answer-0001")
    action(client, uid, "visual_example", "failure-example-0001")
    action(client, uid, "check_understanding", "failure-fresh-0001")
    fresh = session(client, uid)["action"]["question_id"]
    for index in range(3):
        value = submit(client, uid, fresh, "2/12", key=f"failure-answer-{index:04}")
        if index < 2:
            action(client, uid, "visual_example", f"failure-example-{index + 2:04}")
            action(client, uid, "practice", f"failure-retry-{index:04}")
    assert value["unit"]["learning_session"]["short_plan"]["phase"] == "closed"
    assert session(client, uid)["action"]["question_id"] == "reduce"
    assert client.post(f"/api/units/{uid}/questions/{fresh}/answer", json={"answer": "3/8"}).status_code == 409


@pytest.mark.parametrize("assisted", [True, False])
def test_uncertain_independence_never_creates_source_scoped_check_days(profile, assisted):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        template = copy.deepcopy(db.get(LearningUnit, uid).questions[0])
        revision = db.get(Material, mid).revision
        for index, days in enumerate((9, 5, 1)):
            prompt = f"Berechne 1/{index + 3} + 1/{index + 4}."
            question = dict(template, id="recall", prompt=prompt)
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer=question["answer"], outcome="correct",
                assisted=assisted, evaluation={"independence_uncertain": True}, created=int(now()) - days * 86400))
        db.flush()
        state = next(row for row in evidence(db, db.get(LearningUnit, uid), [db.get(Material, mid)])
            if row["label"] == "Brüche addieren")
        assert state["tasks"] == state["attempts"] == state["uncertain"] == 3
        assert state["independent"] == state["supported"] == 0
        assert state["successful_check_dates"] == [] and state["last_independent_success"] is None
        assert state["last_difficulty"] is None and state["confidence"] == "unverified"
        assert state["review_due"] is None


def test_uncertain_independence_does_not_postpone_source_scoped_recall(profile):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        template = copy.deepcopy(db.get(LearningUnit, uid).questions[0])
        source = db.get(Material, mid)
        for days, prompt in ((9, "Berechne 2/5 + 1/10."), (5, "Berechne 1/4 + 1/6."),
                (1, "Berechne 1/3 + 1/12.")):
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[dict(template, id="recall", prompt=prompt)],
                learning_root_id=uid, followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=int(now()) - days * 86400))
        db.flush()
        def get_state():
            return next(row for row in evidence(db, db.get(LearningUnit, uid), [source])
                if row["label"] == "Brüche addieren")
        before = get_state()
        assert before["confidence"] == "repeated_recall" and before["review_due"]
        db.add(Attempt(unit_id=uid, question_id="sum", answer="fixture", outcome="correct", assisted=True,
            evaluation={"independence_uncertain": True}, created=int(now())))
        db.flush()
        after = get_state()
        assert after["uncertain"] == 1 and after["last_difficulty"] is None
        assert after["review_due"] == before["review_due"]
        assert after["successful_check_dates"] == before["successful_check_dates"]
        assert after["confidence"] == "repeated_recall"


def test_source_scoped_spacing_uses_only_check_days_after_latest_difficulty(profile):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        stamp = int(now())
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        template = copy.deepcopy(root.questions[0])
        db.add(Attempt(unit_id=uid, question_id="sum", answer="fixture", outcome="incorrect",
            assisted=False, created=stamp - 10 * 86400))
        for index, days in enumerate((40, 35, 30, 25, 20, 9, 5, 1)):
            question = dict(template, id="recall", prompt=f"Berechne 1/{index + 3} + 1/{index + 4}.")
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamp - days * 86400))
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Brüche addieren")
        assert state["confidence"] == "repeated_recall" and len(state["successful_check_dates"]) == 8
        zone = ZoneInfo(db.get(Child, child["id"]).preferences.get("timezone", "Europe/Berlin"))
        anchor = datetime.fromtimestamp(stamp - 86400, zone).date()
        assert state["review_due"] == coaching.planned_review(db.get(Child, child["id"]), "Mathematik",
            state["successful_check_dates"][-3:], anchor=anchor)
        assert state["review_due"] != coaching.planned_review(db.get(Child, child["id"]), "Mathematik",
            state["successful_check_dates"], anchor=anchor)


def test_earliest_answer_not_unit_creation_sets_duplicate_recall_day(profile):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        stamp = int(now())
        template = copy.deepcopy(root.questions[0])
        prompt = "Berechne 2/5 + 1/10."
        for unit_age, answer_age in ((10, 1), (8, 7)):
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[dict(template, id="recall", prompt=prompt)],
                learning_root_id=uid, followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture",
                created=stamp - unit_age * 86400)
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="1/2", outcome="correct",
                assisted=False, created=stamp - answer_age * 86400))
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Brüche addieren")
        zone = ZoneInfo(db.get(Child, child["id"]).preferences.get("timezone", "Europe/Berlin"))
        assert state["successful_check_dates"] == [datetime.fromtimestamp(stamp - 7 * 86400, zone).date().isoformat()]
        assert state["independent"] == state["attempts"] == 2


def test_uncertainty_flag_cannot_hide_an_actual_retry(profile):
    _, uid, mid, _, _, _ = profile
    with DB.begin() as db:
        stamp = int(now())
        db.add(Attempt(unit_id=uid, question_id="sum", answer="wrong", outcome="incorrect", assisted=False,
            created=stamp - 1, evaluation={"attempt_number": 1}))
        db.add(Attempt(unit_id=uid, question_id="sum", answer="right", outcome="correct", assisted=False,
            created=stamp, evaluation={"attempt_number": 2, "independence_uncertain": True}))
        db.flush()
        state = next(row for row in evidence(db, db.get(LearningUnit, uid), [db.get(Material, mid)])
            if row["label"] == "Brüche addieren")
        assert state["tasks"] == state["supported"] == 1 and state["attempts"] == 2
        assert state["uncertain"] == state["independent"] == 0
        assert state["last_difficulty"] == stamp and state["successful_check_dates"] == []


def test_legacy_answers_without_source_revision_remain_practice_not_current_mastery(profile):
    from fractions import Fraction

    from schulpilot.learning_progress import read_ledger, totals

    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        source = db.get(Material, mid)
        question = copy.deepcopy(db.get(LearningUnit, uid).questions[0])
        # Three old, successful checks would ordinarily satisfy the product's
        # recall criterion. Their legacy material_id proves no source revision.
        for days in (9, 5, 1):
            prompt = f"Berechne 1/{days + 1} + 1/{days + 1}."
            answer = str(Fraction(2, days + 1))
            q = {**question, "prompt": prompt, "answer": answer, "explanation": prompt + " Ergebnis: " + answer}
            old = LearningUnit(child_id=child["id"], material_id=mid,
                subject="Mathematik", topic="Brüche", questions=[q],
                explanation="Künstliche alte Runde.", round_kind="spaced_review",
                status="completed", completed=int(now()) - days * 86400,
                provider="openai", model="synthetic-model-fixture", synthetic=False)
            db.add(old)
            db.flush()
            db.add(Attempt(unit_id=old.id, question_id=q["id"], answer=answer,
                outcome="correct", assisted=False, created=old.completed))
        source.revision += 1
    with DB() as db:
        states = evidence(db, db.get(LearningUnit, uid), [db.get(Material, mid)])
        addition = next(g for g in states if g["label"] == "Brüche addieren")
        assert addition["tasks"] == addition["independent"] == 0
        assert addition["historical_tasks"] == 3
        assert addition["successful_check_dates"] == []
        assert addition["confidence"] == "unverified" and addition["review_due"] is None
        # Original dated answers still count in the ordinary practice overview.
        practice = totals(read_ledger(db, child["id"]))
        assert practice["practiced_tasks"] == practice["independent_tasks"] == 3
        assert len(list(db.scalars(select(Attempt)))) == 3


def test_deliberate_skip_is_idempotent_and_never_an_answer(profile):
    client, uid, _, _, _, _ = profile
    state = session(client, uid)
    body = {"request_key": "skip-artificial-0001", "revision": state["revision"], "question_id": "sum"}
    response = client.post(f"/api/units/{uid}/learning-session/skip", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "paused"
    assert client.post(f"/api/units/{uid}/learning-session/skip", json=body).status_code == 200
    with DB() as db:
        assert not db.scalar(select(Attempt.id).where(Attempt.unit_id == uid))
        assert db.get(LearningUnit, uid).completed is None

@pytest.mark.parametrize("prior_kind,prior_outcome,prior_assisted,prior_uncertain", [
    ("learning", "incorrect", False, False),
    ("check", "correct", True, False),
    ("learning", "correct", False, True),
])
def test_previously_answered_question_is_not_fresh_source_recall(
        profile, prior_kind, prior_outcome, prior_assisted, prior_uncertain):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        stamp = int(now())
        template = copy.deepcopy(root.questions[0])
        prompts = ["Berechne 2/5 + 1/10.", "Berechne 1/4 + 1/6.", "Berechne 1/3 + 1/12."]
        attempts = []
        for days, prompt, kind, outcome, assisted, uncertain in [
            (11, prompts[0], prior_kind, prior_outcome, prior_assisted, prior_uncertain),
            *[(days, prompt, "spaced_review", "correct", False, False)
              for days, prompt in zip((9, 5, 1), prompts, strict=True)],
        ]:
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[dict(template, id="recall", prompt=prompt)],
                learning_root_id=uid, followup_of=uid, round_kind=kind, provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            attempt = Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome=outcome,
                assisted=assisted, evaluation={"independence_uncertain": uncertain}, created=stamp - days * 86400)
            db.add(attempt)
            attempts.append(attempt)
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Brüche addieren")
        zone = ZoneInfo(db.get(Child, child["id"]).preferences.get("timezone", "Europe/Berlin"))
        expected = [datetime.fromtimestamp(stamp - days * 86400, zone).date().isoformat() for days in (5, 1)]
        assert state["successful_check_dates"] == expected
        assert state["confidence"] != "repeated_recall"
        assert state["tasks"] == state["attempts"] == 4
        assert set(state["evidence_refs"]) == {"attempt:" + row.id for row in attempts}


def test_non_math_source_recall_preserves_chemistry_case(profile):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        root.subject, root.topic = "Chemie", "Chemische Zeichen"
        root.subject_id = None
        source.subject, source.topic = root.subject, root.topic
        source.content = "CO steht für Kohlenmonoxid und Co für Cobalt."
        source.source_blocks = []
        root.questions = [{**copy.deepcopy(root.questions[0]), "learning_goal_id": "symbols",
            "prompt": "Welche Stoffe gehören zu den Zeichen?"}]
        db.add(UnitCoaching(unit_id=uid, status="ready", report={"learning_goals": [
            {"id": "symbols", "label": "Chemische Zeichen zuordnen", "source_excerpt": source.content}]}))
        stamp = int(now())
        for days, notation in ((5, "CO"), (1, "Co")):
            question = dict(root.questions[0], id="recall", prompt=f"Welcher Stoff wird mit {notation} bezeichnet?")
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject=root.subject, topic=root.topic,
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamp - days * 86400))
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Chemische Zeichen zuordnen")
        assert len(state["successful_check_dates"]) == 2
        assert state["independent"] == state["attempts"] == 2


def test_source_evidence_uses_subject_identity_and_keeps_other_subjects_separate(profile):
    from schulpilot.subject_registry import alias_key, identity, resolve

    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        family_id = db.get(Child, child["id"]).family_id
        maths = resolve(db, "Mathematik", family_id)
        german = resolve(db, "Deutsch", family_id)
        assert maths and german and maths.id != german.id
        root.subject, root.subject_id = "Mathematik", maths.id
        private = Subject(id=identity("custom-private-maths-test", family_id), key="custom-private-maths-test",
            title="Mathematik", owner_family_id=family_id, cover_key="other",
            active=True, sort_order=100)
        db.add(private)
        db.flush()
        db.add(SubjectAlias(key=alias_key("Mathematik", family_id), subject_id=private.id,
            family_id=family_id, normalized="mathematik"))
        db.flush()
        template = copy.deepcopy(root.questions[0])
        stamps = int(now())
        cases = [
            ("Mathe", None, "Berechne 2/5 + 1/10.", True),
            ("Mathematik", maths.id, "Berechne 1/4 + 1/6.", True),
            ("Mathematik", None, "Berechne 1/11 + 1/22.", False),  # ambiguous historic label
            ("Deutsch", german.id, "Berechne 1/3 + 1/12.", False),
            # A stale display label is not a substitute for its stored identity.
            ("Mathematik", german.id, "Berechne 2/7 + 1/14.", False),
            ("Mathematik", private.id, "Berechne 2/9 + 1/18.", False),
        ]
        expected = set()
        for index, (label, subject_id, prompt, included) in enumerate(cases):
            question = dict(template, id="recall", prompt=prompt)
            other = LearningUnit(child_id=child["id"], material_id=mid, subject=label, subject_id=subject_id,
                topic="Brüche", explanation="Künstliche Wiederholung.", questions=[question],
                learning_root_id=uid, followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(other)
            db.flush()
            # Simulate legacy rows and existing stored IDs independently of the
            # normal insert hook, which derives the ID from today's label.
            other.subject_id = subject_id
            db.add(UnitSource(unit_id=other.id, material_id=mid, revision=source.revision))
            attempt = Attempt(unit_id=other.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamps - (10 - index) * 86400)
            db.add(attempt)
            db.flush()
            if included:
                expected.add("attempt:" + attempt.id)
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Brüche addieren")
        assert state["tasks"] == state["attempts"] == state["independent"] == 2
        assert set(state["evidence_refs"]) == expected
        assert len(state["successful_check_dates"]) == 2


def test_same_second_duplicate_source_recall_is_not_guessed(profile):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        stamp = int(now()) - 86400
        attempts = []
        for _ in range(2):
            question = dict(copy.deepcopy(root.questions[0]), id="recall", prompt="Berechne 2/5 + 1/10.")
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject="Mathematik", topic="Brüche",
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            attempt = Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamp)
            db.add(attempt)
            attempts.append(attempt)
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Brüche addieren")
        assert state["successful_check_dates"] == []
        assert state["independent"] == state["attempts"] == 2
        assert set(state["evidence_refs"]) == {"attempt:" + attempt.id for attempt in attempts}


@pytest.mark.parametrize("prior_goal,old_revision", [("g2", False), ("g1", True)])
def test_exposure_in_other_goal_or_historical_source_is_not_fresh(profile, prior_goal, old_revision):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        stamp = int(now())
        db.add(UnitCoaching(unit_id=uid, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Lernziel A", "source_excerpt": source.content[:40]},
            {"id": "g2", "label": "Lernziel B", "source_excerpt": source.content[:40]},
        ]}))
        template = copy.deepcopy(root.questions[0])
        for days, goal, prompt in ((3, prior_goal, "Berechne 1/4 + 1/4."),
                                   (1, "g1", "Wie viel ist 1/4 + 1/4?")):
            question = dict(template, id="recall", learning_goal_id=goal, prompt=prompt)
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject=root.subject, topic=root.topic,
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid,
                revision=source.revision - 1 if old_revision and days == 3 else source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamp - days * 86400))
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Lernziel A")
        assert state["successful_check_dates"] == []
        assert state["tasks"] == state["attempts"] == 1
        assert state["historical_tasks"] == int(old_revision)


@pytest.mark.parametrize("old_subject,expected_checks", [("Unbekanntes Altfach", 0), ("Deutsch", 1)])
def test_uncertain_old_subject_only_affects_exposure_not_competence(profile, old_subject, expected_checks):
    _, uid, mid, _, _, child = profile
    with DB.begin() as db:
        root, source = db.get(LearningUnit, uid), db.get(Material, mid)
        stamp = int(now())
        db.add(UnitCoaching(unit_id=uid, status="ready", report={"learning_goals": [
            {"id": "g1", "label": "Lernziel A", "source_excerpt": source.content[:40]},
        ]}))
        for days, subject in ((3, old_subject), (1, root.subject)):
            question = dict(copy.deepcopy(root.questions[0]), id="recall", learning_goal_id="g1",
                prompt="Berechne 1/4 + 1/4.")
            unit = LearningUnit(child_id=child["id"], material_id=mid, subject=subject, topic=root.topic,
                explanation="Künstliche Wiederholung.", questions=[question], learning_root_id=uid,
                followup_of=uid, round_kind="spaced_review", provider="synthetic-fixture")
            db.add(unit)
            db.flush()
            db.add(UnitSource(unit_id=unit.id, material_id=mid, revision=source.revision))
            db.add(Attempt(unit_id=unit.id, question_id="recall", answer="fixture", outcome="correct",
                assisted=False, created=stamp - days * 86400))
        db.flush()
        state = next(row for row in evidence(db, root, [source]) if row["label"] == "Lernziel A")
        assert len(state["successful_check_dates"]) == expected_checks
        assert state["tasks"] == state["attempts"] == 1
        assert state["historical_tasks"] == 0
