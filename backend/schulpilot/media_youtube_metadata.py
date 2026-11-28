"""Validate actual YouTube Data API responses without making network requests.

This is an inert adapter, not a downloader or a content analysis. Public
metadata is untrusted and cannot authorize publication. No child data is an
input. API requests, quota, key storage and expiry handling remain separate.
"""
import re
import unicodedata

from .curriculum import fingerprint
from .curriculum_models import CurriculumDocument, CurriculumTopic
from .db import Subject, now

_VIDEO = re.compile(r"[A-Za-z0-9_-]{11}\Z")
_REGION = re.compile(r"[A-Z]{2}\Z")
_DURATION = re.compile(r"P(?:(\d{1,3})D)?T(?:(\d{1,3})H)?(?:(\d{1,2})M)?(?:(\d{1,2})S)?\Z")


def _bounded_text(value, maximum):
    if (not isinstance(value, str) or not value.strip() or len(value) > maximum
            or any(unicodedata.category(char).startswith("C") for char in value)):
        raise ValueError("Invalid public metadata text")
    return value.strip()


def curated_query(db, topic_id):
    """Build a query exclusively from a still-matching public curriculum row."""
    topic = db.get(CurriculumTopic, topic_id)
    if not topic or not isinstance(topic.data, dict):
        raise ValueError("Reviewed public curriculum topic unavailable")
    subject = db.get(Subject, topic.subject_id)
    document = db.get(CurriculumDocument, topic.document_id)
    if (not subject or subject.owner_family_id is not None or fingerprint(topic.data) != topic.digest
            or topic.data.get("id") != topic.id or topic.data.get("document_id") != topic.document_id
            or topic.data.get("title") != topic.title or topic.data.get("subject_key") != subject.key
            or not document or not isinstance(document.data, dict) or fingerprint(document.data) != document.digest
            or document.data.get("id") != document.id or document.state_code != topic.state_code
            or document.data.get("school_form_id") != topic.school_form_id):
        raise ValueError("Curriculum provenance no longer matches")
    return _bounded_text(subject.title, 160) + " " + _bounded_text(topic.title, 200)


def search_ids(response):
    """Only IDs actually received as video search results; never invent IDs."""
    if not isinstance(response, dict) or not isinstance(response.get("items"), list) or len(response["items"]) > 50:
        raise ValueError("Invalid search response")
    found, seen = [], set()
    for item in response["items"]:
        identifier = item.get("id") if isinstance(item, dict) else None
        if not isinstance(identifier, dict) or identifier.get("kind") != "youtube#video":
            continue
        value = identifier.get("videoId")
        if isinstance(value, str) and _VIDEO.fullmatch(value) and value not in seen:
            seen.add(value)
            found.append(value)
    return found


def _duration(value):
    match = _DURATION.fullmatch(value) if isinstance(value, str) else None
    if not match or not any(part is not None for part in match.groups()[1:]):
        raise ValueError("Invalid video duration")
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    if minutes > 59 or seconds > 59 or (days and hours > 23):
        raise ValueError("Invalid video duration")
    total = days * 86400 + hours * 3600 + minutes * 60 + seconds
    if not 0 < total <= 31 * 86400:
        raise ValueError("Invalid video duration")
    return total


def _region_available(restrictions, region):
    if restrictions is None:
        return True
    if not isinstance(restrictions, dict) or set(restrictions) - {"allowed", "blocked"}:
        return False
    if "allowed" in restrictions and "blocked" in restrictions:
        return False
    for value in restrictions.values():
        if not isinstance(value, list) or any(not isinstance(code, str) or not _REGION.fullmatch(code) for code in value):
            return False
    if "allowed" in restrictions:
        return region in restrictions["allowed"]
    return region not in restrictions.get("blocked", [])


def video_metadata(response, requested_ids, *, region):
    """Return finite public metadata from verified IDs, not a review or ranking.

    Missing, private, restricted and live videos are excluded. Titles and
    channel names are untrusted display text, never instructions or proof.
    """
    checked_at = int(now())  # A client must not extend metadata retention.
    if (not isinstance(requested_ids, list) or not 1 <= len(requested_ids) <= 50
            or any(not isinstance(item, str) or not _VIDEO.fullmatch(item) for item in requested_ids)
            or len(set(requested_ids)) != len(requested_ids)
            or not isinstance(region, str) or not _REGION.fullmatch(region)
            or type(checked_at) is not int or checked_at < 0):
        raise ValueError("Invalid lookup scope")
    if not isinstance(response, dict) or not isinstance(response.get("items"), list) or len(response["items"]) > 50:
        raise ValueError("Invalid video response")
    requested, seen, result = set(requested_ids), set(), []
    for item in response["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or item["id"] not in requested:
            raise ValueError("Unexpected video identifier")
        identifier = item["id"]
        if identifier in seen:
            raise ValueError("Duplicate video identifier")
        seen.add(identifier)
        status, details, snippet = item.get("status"), item.get("contentDetails"), item.get("snippet")
        if not all(isinstance(part, dict) for part in (status, details, snippet)):
            continue
        rating = details.get("contentRating", {})
        if (status.get("privacyStatus") != "public" or status.get("uploadStatus") != "processed"
                or snippet.get("liveBroadcastContent") != "none"
                or not isinstance(rating, dict) or "ytRating" in rating
                or not _region_available(details.get("regionRestriction"), region)):
            continue
        try:
            title = _bounded_text(snippet.get("title"), 300)
            channel = _bounded_text(snippet.get("channelTitle"), 200)
            duration = _duration(details.get("duration"))
        except ValueError:
            continue
        result.append({"provider": "youtube", "provider_id": identifier,
            "title": title, "channel": channel, "duration_seconds": duration,
            "url": "https://www.youtube.com/watch?v=" + identifier,
            "available": True, "checked_region": region, "checked_at": checked_at,
            "review_status": "unreviewed"})
    return result
