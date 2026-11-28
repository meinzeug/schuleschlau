"""Fail-closed policy for shared educational media; no network or AI calls.

Callers must authorize the child/family before supplying the explicitly known
profile. Merely importing provider metadata never constitutes a content review.
"""
import re
from urllib.parse import urlsplit

from sqlalchemy import func, select

from .curriculum import fingerprint
from .curriculum_models import CurriculumDocument, CurriculumTopic
from .db import Subject, User, now
from .media_explorer_models import MediaCurriculumLink, MediaEditorialReview, MediaResource

METADATA_MAX_AGE = 30 * 24 * 60 * 60
_YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def public_media_url(provider, provider_id, url):
    """Accept only a deterministic, credential-free link to the recorded video."""
    if provider != "youtube" or not isinstance(provider_id, str) or not _YOUTUBE_ID.fullmatch(provider_id):
        return False
    if not isinstance(url, str) or url != f"https://www.youtube.com/watch?v={provider_id}":
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.hostname == "www.youtube.com" and not parsed.username


def eligible(resource, link, topic, review, reviewer, *, state_code, school_form_id,
             level_kind, level_number, age, current_time):
    """Return a boolean only; unknown scope or uncertain evidence is not safe."""
    if (not resource or not link or not topic or not review or not reviewer
            or resource.available is not True or not public_media_url(resource.provider, resource.provider_id, resource.url)):
        return False
    if (type(current_time) is not int or type(resource.checked_at) is not int
            or resource.checked_at > current_time or current_time - resource.checked_at >= METADATA_MAX_AGE):
        return False
    if (link.active is not True or type(link.revision) is not int or link.revision < 1
            or link.resource_id != resource.id or link.topic_id != topic.id or link.topic_digest != topic.digest
            or topic.state_code != state_code or topic.school_form_id != school_form_id
            or not isinstance(state_code, str) or not re.fullmatch(r"[A-Z]{2}-[A-Z0-9]{1,3}", state_code)
            or resource.checked_region != state_code[:2]
            or level_kind != "klasse" or link.level_kind != level_kind
            or type(level_number) is not int or type(link.min_level) is not int or type(link.max_level) is not int
            or not link.min_level <= level_number <= link.max_level):
        return False
    # Curriculum grades are authoritative; an editorial link cannot widen a
    # source's explicitly documented grade band or invent a language year.
    topic_data = topic.data if isinstance(topic.data, dict) else {}
    grades = topic_data.get("grades")
    if (not topic_data or fingerprint(topic_data) != topic.digest
            or topic_data.get("id") != topic.id or topic_data.get("document_id") != topic.document_id
            or topic_data.get("title") != topic.title
            or topic_data.get("grade_kind") not in ("exact", "band")
            or not isinstance(grades, list) or any(type(grade) is not int for grade in grades)
            or level_number not in grades):
        return False
    if (review.resource_id != resource.id or review.resource_revision != resource.revision
            or review.decision != "approved" or review.evidence_scope != "content"
            or not review.reviewer_id or review.reviewer_id != reviewer.id
            or reviewer.role != "admin" or not reviewer.verified or reviewer.disabled
            or type(review.reviewed_at) is not int or review.reviewed_at > current_time
            or type(age) is not int or type(review.min_age) is not int or not 0 <= review.min_age <= age <= 99):
        return False
    if review.content_kind not in ("general", "historical_source", "propaganda", "sensitive"):
        return False
    if review.content_kind != "general" and not (review.context or "").strip():
        return False
    if review.content_kind in ("propaganda", "sensitive") and not (review.counterpoint or "").strip():
        return False
    return True


def select_for_topic(db, *, topic_id, subject_id, state_code, school_form_id,
                     level_kind, level_number, age, limit=12):
    """Select reviewed shared records, without changing progress or starting jobs.

    The school profile is deliberately an explicit argument: this helper does
    not derive a language learning year from a school year, look up a child, or
    authorize a request. The eventual endpoint must do those checks itself.
    """
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("Media limit must be between 1 and 20")
    current_time = int(now())  # Freshness must never depend on a client clock.
    if (not isinstance(state_code, str) or not state_code
            or not isinstance(school_form_id, str) or not school_form_id
            or level_kind != "klasse"
            or type(level_number) is not int or level_number < 1
            or type(age) is not int or not 0 <= age <= 99 or type(current_time) is not int):
        return []
    topic = db.get(CurriculumTopic, topic_id)
    subject = db.get(Subject, subject_id)
    if not topic or not subject or subject.owner_family_id is not None or topic.subject_id != subject.id:
        return []
    document = db.get(CurriculumDocument, topic.document_id)
    if (not document or not isinstance(document.data, dict) or not isinstance(topic.data, dict)
            or fingerprint(document.data) != document.digest or document.data.get("id") != document.id
            or document.state_code != topic.state_code
            or document.data.get("school_form_id") != topic.school_form_id
            or topic.data.get("subject_key") != subject.key):
        return []
    # Select the latest decision before filtering for approval: an older
    # approval must never outlive a newer editorial block. This is one bounded
    # query, independent of how many candidates the topic contains.
    latest = (select(MediaEditorialReview.resource_id,
                     func.max(MediaEditorialReview.review_number).label("number"))
              .join(MediaCurriculumLink, MediaCurriculumLink.resource_id == MediaEditorialReview.resource_id)
              .where(MediaCurriculumLink.topic_id == topic.id, MediaCurriculumLink.active.is_(True))
              .group_by(MediaEditorialReview.resource_id).subquery())
    rows = db.execute(
        select(MediaResource, MediaCurriculumLink, MediaEditorialReview, User)
        .join(MediaCurriculumLink, MediaCurriculumLink.resource_id == MediaResource.id)
        .join(latest, latest.c.resource_id == MediaResource.id)
        .join(MediaEditorialReview, (MediaEditorialReview.resource_id == latest.c.resource_id)
              & (MediaEditorialReview.review_number == latest.c.number))
        .join(User, User.id == MediaEditorialReview.reviewer_id)
        .where(MediaCurriculumLink.topic_id == topic.id, MediaCurriculumLink.active.is_(True), MediaResource.available.is_(True),
               MediaEditorialReview.decision == "approved", MediaEditorialReview.evidence_scope == "content")
        .order_by(MediaResource.id).limit(100)
    )
    result = []
    for resource, link, review, reviewer in rows:
        if eligible(resource, link, topic, review, reviewer, state_code=state_code,
                    school_form_id=school_form_id, level_kind=level_kind,
                    level_number=level_number, age=age, current_time=current_time):
            result.append({"id": resource.id, "title": resource.title, "provider": resource.provider,
                           "channel": resource.channel, "url": resource.url,
                           "duration_seconds": resource.duration_seconds,
                           "content_kind": review.content_kind, "context": review.context,
                           "counterpoint": review.counterpoint, "review_scope": "content"})
            if len(result) == limit:
                break
    return result
