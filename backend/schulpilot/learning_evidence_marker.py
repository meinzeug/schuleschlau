"""Private change marker for saved practice evidence, never a mastery verdict.

The marker is a versioned digest of narrowly selected metadata. It does not
read or return learner answers, source text, prompts, explanations, notes, or
provider responses. It is not a security token or an anonymisation method and
must remain in the child's private server-side data.

Callers must check family authorisation and use the existing Unit -> Child
lock order. A caller that persists/compares a marker across a provider call
must re-check source/plan/provider revisions separately; this module does not
lock rows, decide readiness, cancel or generate work, or call a provider.
"""

from __future__ import annotations

import hashlib
import hmac
import json

from sqlalchemy import and_, select

from .competence_models import QuestionCompetence
from .competences import VERSION as COMPETENCE_VERSION
from .db import Activity, Attempt, AttemptAssessment, Child, LearningUnit, Material, UnitSource
from .grades import subject_key

VERSION = "practice-evidence-marker-1"


def snapshot(db, child_id: str, subject: str, *, exclude_unit_id: str | None = None) -> dict[str, str]:
    """Return a child/subject-bound change marker from saved practice metadata.

    Optional exclusion avoids treating the target round's own later answers as
    changes to the earlier *other-round* basis. Only actual attempted units are
    included; opening material, reading or creating an unused round is not a
    performance observation. Subject normalisation intentionally matches the
    existing instructional strategy, including Mathe/Mathematik.

    Assumes pending writes have already been flushed. No implicit commit, no
    mutation, and no provider call. This marker includes current linked-source
    revision/confirmation and explicit competence-binding metadata, but is not
    a comprehensive semantic integrity check for legacy unbound question text.
    """
    if not isinstance(child_id, str) or not child_id or not db.get(Child, child_id):
        raise ValueError("Unknown child")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 80:
        raise ValueError("Invalid subject")
    if exclude_unit_id is not None and (not isinstance(exclude_unit_id, str) or not exclude_unit_id):
        raise ValueError("Invalid excluded unit")
    key = subject_key(subject)

    # Select scalar columns only. In particular, Attempt.answer and
    # LearningUnit.questions are deliberately absent from every query.
    units = {
        row.id: row.round_kind
        for row in db.execute(select(LearningUnit.id, LearningUnit.subject, LearningUnit.round_kind).where(
            LearningUnit.child_id == child_id
        ))
        if subject_key(row.subject) == key and row.id != exclude_unit_id
    }
    attempts = []
    attempted_pairs = set()
    attempted_units = set()
    if units:
        query = select(
            Attempt.id, Attempt.unit_id, Attempt.question_id, Attempt.created,
            Attempt.outcome, Attempt.assisted,
            Attempt.evaluation["method"].as_string().label("method"),
            Attempt.evaluation["independence_uncertain"].as_boolean().label("independence_uncertain"),
            Attempt.evaluation["attempt_number"].as_integer().label("attempt_number"),
        ).join(LearningUnit, LearningUnit.id == Attempt.unit_id).where(LearningUnit.child_id == child_id)
        for row in db.execute(query):
            if row.unit_id not in units:
                continue
            attempted_units.add(row.unit_id)
            attempted_pairs.add((row.unit_id, row.question_id))
            attempts.append([row.unit_id, row.question_id, row.id, row.created, row.outcome, row.assisted,
                             row.method, row.independence_uncertain, row.attempt_number])

    corrections, hints, sources, bindings = [], [], [], []
    if attempted_units:
        corrections = [list(row)[1:] for row in db.execute(select(
            Attempt.unit_id,
            AttemptAssessment.id, AttemptAssessment.attempt_id, AttemptAssessment.rules_version,
            AttemptAssessment.outcome, AttemptAssessment.created,
        ).join(Attempt, Attempt.id == AttemptAssessment.attempt_id)
            .join(LearningUnit, LearningUnit.id == Attempt.unit_id)
            .where(LearningUnit.child_id == child_id)) if row.unit_id in attempted_units]
        # Do not select Activity.detail; only explicitly recorded hints for
        # already-attempted rounds are related to a saved observation.
        hints = [list(row) for row in db.execute(select(Activity.id, Activity.unit_id, Activity.created)
            .join(LearningUnit, LearningUnit.id == Activity.unit_id).where(
                Activity.child_id == child_id, LearningUnit.child_id == child_id, Activity.kind == "hint"))
            if row.unit_id in attempted_units]
        # A foreign or removed material never grants access: the left join is
        # explicitly child-scoped and contributes only a missing-source marker.
        sources = [list(row) for row in db.execute(select(
            UnitSource.unit_id, UnitSource.material_id, UnitSource.revision,
            Material.revision, Material.confirmed,
        ).join(LearningUnit, LearningUnit.id == UnitSource.unit_id)
            .outerjoin(Material, and_(Material.id == UnitSource.material_id, Material.child_id == child_id))
            .where(LearningUnit.child_id == child_id)) if row.unit_id in attempted_units]
        rows = db.execute(select(
            QuestionCompetence.unit_id, QuestionCompetence.question_id,
            QuestionCompetence.competence_id, QuestionCompetence.catalog_version,
            QuestionCompetence.role, QuestionCompetence.question_digest,
        ).join(LearningUnit, LearningUnit.id == QuestionCompetence.unit_id)
            .where(QuestionCompetence.child_id == child_id, LearningUnit.child_id == child_id))
        bindings = [list(row) for row in rows if (row.unit_id, row.question_id) in attempted_pairs]

    # JSON sorting on each record handles missing optional fields without
    # comparing unlike Python types and keeps ordering independent of DB rows.
    def canonical(values):
        return sorted(values, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    payload = {
        "version": VERSION,
        "competence_catalog_version": COMPETENCE_VERSION,
        "child": child_id,
        "subject": key,
        "units": canonical([[item, units[item]] for item in attempted_units]),
        "attempts": canonical(attempts),
        "corrections": canonical(corrections),
        "hints": canonical(hints),
        "sources": canonical(sources),
        "bindings": canonical(bindings),
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return {"version": VERSION, "digest": hashlib.sha256(data).hexdigest()}


def matches(previous, current) -> bool:
    """Compare only complete supported markers; legacy/invalid data is unknown."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return False
    expected = {"version", "digest"}
    if set(previous) != expected or set(current) != expected:
        return False
    if previous["version"] != VERSION or current["version"] != VERSION:
        return False
    a, b = previous["digest"], current["digest"]
    return (isinstance(a, str) and isinstance(b, str) and len(a) == len(b) == 64
            and all(c in "0123456789abcdef" for c in a + b) and hmac.compare_digest(a, b))
