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
import re

from sqlalchemy import String, and_, cast, func, literal, select, union_all

from .competence_models import QuestionCompetence
from .competences import VERSION as COMPETENCE_VERSION
from .db import Activity, Attempt, AttemptAssessment, Child, LearningUnit, Material, UnitSource
from .grades import subject_key

VERSION = "practice-evidence-marker-1"


class EvidenceMetadataError(ValueError):
    """Invalid evidence metadata; callers must not treat this as fresh evidence."""


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
        raise EvidenceMetadataError("Unknown child")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 80:
        raise EvidenceMetadataError("Invalid subject")
    if exclude_unit_id is not None and (not isinstance(exclude_unit_id, str) or not exclude_unit_id):
        raise EvidenceMetadataError("Invalid excluded unit")
    key = subject_key(subject)

    # Read all evidence rows in one SQL statement. At PostgreSQL READ COMMITTED
    # each statement observes one committed snapshot; separate SELECTs could mix
    # rows from different commits. The JSON arrays contain metadata only.
    # This does not protect the later comparison-to-publication interval.
    json_array = func.json_build_array if db.get_bind().dialect.name == "postgresql" else func.json_array

    def float_text(column):
        # SQLite JSON rounds REAL values; 17 significant digits preserve the
        # original double and therefore the existing digest across upgrades.
        return cast(column, String) if db.get_bind().dialect.name == "postgresql" else func.printf("%!.17g", column)

    def rows(kind, *columns):
        return select(literal(kind).label("kind"), cast(json_array(*columns), String).label("data"))

    statement = union_all(
        rows("unit", LearningUnit.id, LearningUnit.subject, LearningUnit.round_kind)
            .where(LearningUnit.child_id == child_id),
        rows("attempt", Attempt.unit_id, Attempt.question_id, Attempt.id, float_text(Attempt.created),
             Attempt.outcome, Attempt.assisted, Attempt.evaluation["method"].as_string(),
             Attempt.evaluation["independence_uncertain"].as_string(),
             Attempt.evaluation["attempt_number"].as_string())
            .select_from(Attempt).join(LearningUnit, LearningUnit.id == Attempt.unit_id).where(LearningUnit.child_id == child_id),
        rows("correction", Attempt.unit_id, AttemptAssessment.id, AttemptAssessment.attempt_id,
             AttemptAssessment.rules_version, AttemptAssessment.outcome, float_text(AttemptAssessment.created))
            .select_from(AttemptAssessment).join(Attempt, Attempt.id == AttemptAssessment.attempt_id)
            .join(LearningUnit, LearningUnit.id == Attempt.unit_id).where(LearningUnit.child_id == child_id),
        rows("hint", Activity.id, Activity.unit_id, Activity.created)
            .select_from(Activity).join(LearningUnit, LearningUnit.id == Activity.unit_id)
            .where(Activity.child_id == child_id, LearningUnit.child_id == child_id, Activity.kind == "hint"),
        rows("source", UnitSource.unit_id, UnitSource.material_id, UnitSource.revision,
             Material.revision, Material.confirmed)
            .select_from(UnitSource).join(LearningUnit, LearningUnit.id == UnitSource.unit_id)
            .outerjoin(Material, and_(Material.id == UnitSource.material_id, Material.child_id == child_id))
            .where(LearningUnit.child_id == child_id),
        rows("binding", QuestionCompetence.unit_id, QuestionCompetence.question_id,
             QuestionCompetence.competence_id, QuestionCompetence.catalog_version,
             QuestionCompetence.role, QuestionCompetence.question_digest)
            .select_from(QuestionCompetence).join(LearningUnit, LearningUnit.id == QuestionCompetence.unit_id)
            .where(QuestionCompetence.child_id == child_id, LearningUnit.child_id == child_id),
    )
    grouped = {name: [] for name in ("unit", "attempt", "correction", "hint", "source", "binding")}
    for kind, data in db.execute(statement):
        try:
            grouped[kind].append(json.loads(data))
        except (ValueError, TypeError) as error:
            raise EvidenceMetadataError("Invalid evidence metadata") from error

    if any(not isinstance(row[1], str) for row in grouped["unit"]):
        raise EvidenceMetadataError("Invalid evidence subject")
    units = {identifier: round_kind for identifier, subject_name, round_kind in grouped["unit"]
             if subject_key(subject_name) == key and identifier != exclude_unit_id}
    attempts = [row for row in grouped["attempt"] if row[0] in units]
    for row in attempts:
        # SQLite json_array encodes booleans as 0/1; normalise them back to
        # the Python values used by the original marker on both databases.
        try:
            row[3] = float(row[3])
        except (ValueError, TypeError, OverflowError) as error:
            raise EvidenceMetadataError("Invalid evidence timestamp") from error
        row[5] = bool(row[5])
        if row[7] is not None:
            value = row[7]
            if value in (True, False, 0, 1):
                row[7] = bool(value)
            elif isinstance(value, str) and value.lower() in ("true", "false", "1", "0"):
                row[7] = value.lower() in ("true", "1")
            else:
                raise EvidenceMetadataError("Invalid independence marker")
        if row[8] is not None:
            value = row[8]
            if type(value) is int:
                row[8] = value
            elif isinstance(value, str) and len(value) <= 32 and re.fullmatch(r"[+-]?[0-9]+", value):
                # The marker is advisory. A corrupted unbounded decimal string
                # must not reach Python's bounded integer conversion and turn
                # the observation into an unexpected start failure.
                row[8] = int(value)
            else:
                raise EvidenceMetadataError("Invalid attempt number")
    attempted_units = {row[0] for row in attempts}
    attempted_pairs = {(row[0], row[1]) for row in attempts}
    corrections = [row[1:] for row in grouped["correction"] if row[0] in attempted_units]
    for row in corrections:
        try:
            row[-1] = float(row[-1])
        except (ValueError, TypeError, OverflowError) as error:
            raise EvidenceMetadataError("Invalid correction timestamp") from error
    hints = [row for row in grouped["hint"] if row[1] in attempted_units]
    sources = [row for row in grouped["source"] if row[0] in attempted_units]
    for row in sources:
        if row[4] is not None:
            row[4] = bool(row[4])
    bindings = [row for row in grouped["binding"] if (row[0], row[1]) in attempted_pairs]

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
    try:
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError, OverflowError) as error:
        raise EvidenceMetadataError("Invalid evidence metadata") from error
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
