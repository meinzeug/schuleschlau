"""Keyset pagination over raw notice candidates; validation remains authoritative.

The cursor advances over *examined* candidates, including stale ones, so a
bounded validation pass never silently skips older valid events.
"""
import base64
import binascii
import json
import re

from fastapi import HTTPException
from sqlalchemy import case, literal, select, tuple_, union_all

from .db import FamilyCall, Job, LanguageProject, Message, VocabularyImport
from .exam_models import ExamRound
from .exam_review_models import ExamReview, ExamReviewPractice
from .parent_reminder_models import ParentGoalReminderEvent

PAGE_SIZE = 50
SCAN_LIMIT = 500
BATCH = 50


def encode_cursor(stamp, key):
    data = json.dumps([1, stamp, key], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def decode_cursor(value):
    try:
        if not isinstance(value, str) or not 1 <= len(value) <= 512 or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        if (not isinstance(data, list) or len(data) != 3 or type(data[0]) is not int or data[0] != 1 or
                type(data[1]) is not int or data[1] < 0 or data[1] > 9999999999 or
                not isinstance(data[2], str) or not re.fullmatch(r"[a-z_]+:[a-z0-9:]+", data[2]) or
                len(data[2]) > 150):
            raise ValueError()
        return data[1], data[2]
    except (ValueError, TypeError, UnicodeError, binascii.Error):
        raise HTTPException(400, "Diese Nachrichtenposition ist ungültig. Bitte neu laden.") from None


def _query(user, ids, cutoff, current):
    """Only private IDs and timestamps; each candidate is revalidated later."""
    message_kinds = (["reply", "preparation", "reminder"] if user.role == "child"
                     else ["help", "interest", "plan_change", "preparation"])
    message_key = case(
        (Message.kind == "round_ready", literal("round_ready:") + Message.id),
        else_=literal("message:") + Message.id,
    )
    queries = [select(Message.created.label("stamp"), message_key.label("key")).where(
        Message.child_id.in_(ids), Message.kind.in_([*message_kinds, "round_ready"]),
        Message.created > cutoff, Message.created <= current,
        (Message.sender_id.is_(None) | (Message.sender_id != user.id))),
    ]
    if user.role == "parent":
        queries.extend([
            select(FamilyCall.created.label("stamp"), (literal("family_call:") + FamilyCall.id).label("key"))
            .where(FamilyCall.child_id.in_(ids), FamilyCall.created > cutoff, FamilyCall.created <= current),
            select(ParentGoalReminderEvent.created.label("stamp"),
                (literal("parent_goal:") + ParentGoalReminderEvent.id).label("key"))
            .where(ParentGoalReminderEvent.user_id == user.id, ParentGoalReminderEvent.child_id.in_(ids),
                ParentGoalReminderEvent.created > cutoff, ParentGoalReminderEvent.created <= current),
        ])
    for model, prefix in ((LanguageProject, "language_ready:"), (VocabularyImport, "words_ready:")):
        queries.append(select(Job.finished.label("stamp"), (literal(prefix) + model.id).label("key"))
            .select_from(model).join(Job, Job.id == model.job_id)
            .where(model.child_id.in_(ids), Job.status.in_(["completed", "failed"]),
                Job.finished > cutoff, Job.finished <= current))
    for model in (ExamRound, ExamReview, ExamReviewPractice):
        queries.append(select(Job.finished.label("stamp"),
                (literal("exam_ready:") + model.id + literal(":") + Job.id).label("key"))
            .select_from(model).join(Job, Job.id == model.job_id)
            .where(Job.child_id.in_(ids), Job.status == "completed", Job.finished > cutoff, Job.finished <= current))
    return union_all(*queries).subquery()


def _newest_preparation(db, user, item, current, cutoff):
    """Keep one current day notice across page boundaries, as in the legacy feed."""
    if item["kind"] != "preparation" or not item["id"].startswith("message:"):
        return True
    message = db.get(Message, item["id"].split(":", 1)[1])
    context = message.context if message and isinstance(message.context, dict) else {}
    if len(context) != 1 or not isinstance(context.get("day_id"), str):
        return True
    # Candidates with identical day binding have the same current source and
    # permissions. Restrict to exactly that shape before choosing the newest.
    candidates = db.execute(select(Message.id, Message.context).where(
        Message.child_id == message.child_id, Message.kind == "preparation",
        Message.created > cutoff, Message.created <= current,
        (Message.sender_id.is_(None) | (Message.sender_id != user.id)),
        Message.context["day_id"].as_string() == context["day_id"],
    ).order_by(Message.created.desc(), Message.id.desc()).limit(SCAN_LIMIT + 1))
    for candidate_id, candidate_context in candidates:
        if candidate_context == context:
            return candidate_id == message.id
    # A pathological run of malformed contexts must not hide a valid page.
    # Conservatively show it; the client may see a duplicate day notification.
    return True


def page(db, user, current, before, *, direct_messages=False, direct_exams=False):
    from .notification_inbox import RETENTION_DAYS, recent_events
    from .notifications import children_for

    if user.role not in ("child", "parent"):
        # Reuse the existing audit/403 path, including its explicit commit.
        recent_events(db, user, current)
    children = children_for(db, user)
    ids = [child.id for child in children]
    cutoff = current - RETENTION_DAYS * 86400
    # Exam reminders are current-state projections, bounded per child and not
    # persisted as rows. Include only their IDs in the same global ordering.
    reminders = []
    from .exams import due_reminders
    for child in children:
        for row in due_reminders(db, child, current):
            key = f"exam_reminder:{row['session_id']}:{row['revision']}"
            if row["created"] > cutoff and (before is None or (row["created"], key) < before):
                reminders.append((row["created"], key))
    source = _query(user, ids, cutoff, current)
    # Python merge/order and cursor comparison use raw ASCII ordering. Do not
    # depend on the database's installation-specific linguistic collation.
    key_column = source.c.key.collate("BINARY" if db.bind.dialect.name == "sqlite" else "C")
    result, position, examined = [], before, 0
    # Re-query after the last examined candidate. Small batches keep expensive
    # authority/source checks bounded and prevent invalid rows hiding results.
    while examined < SCAN_LIMIT and len(result) < PAGE_SIZE:
        query = select(source.c.stamp, source.c.key)
        if position is not None:
            query = query.where(tuple_(source.c.stamp, key_column) < position)
        rows = [(int(stamp), key) for stamp, key in db.execute(
            query.order_by(source.c.stamp.desc(), key_column.desc()).limit(BATCH))]
        candidates = sorted(set(rows + [r for r in reminders if position is None or r < position]), reverse=True)[:BATCH]
        if not candidates:
            return result, None
        validated = {item["id"]: item for item in recent_events(db, user, current,
            direct_messages=direct_messages, direct_exams=direct_exams,
            event_keys={key for _, key in candidates})}
        for stamp, key in candidates:
            position = (stamp, key)
            examined += 1
            item = validated.get(key)
            if item and item["created"] == stamp and _newest_preparation(db, user, item, current, cutoff):
                result.append(item)
            if examined >= SCAN_LIMIT or len(result) >= PAGE_SIZE:
                break
    # Returning a cursor on an exact boundary is intentional: a final empty
    # request can discover that no candidates remain, without an unbounded scan.
    return result, encode_cursor(*position) if position else None
