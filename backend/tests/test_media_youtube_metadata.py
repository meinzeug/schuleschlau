"""Synthetic API responses only; these tests make no YouTube request."""
import copy

import pytest
from schulpilot.curriculum_models import CurriculumTopic
from schulpilot.db import DB
from schulpilot.media_youtube_metadata import curated_query, search_ids, video_metadata
from sqlalchemy import select

VIDEO_ID = "Abcdefgh_12"


@pytest.fixture(autouse=True)
def fixed_server_time(monkeypatch):
    monkeypatch.setattr("schulpilot.media_youtube_metadata.now", lambda: 1000)


@pytest.fixture
def response():
    return {"items": [{"id": VIDEO_ID, "status": {"privacyStatus": "public", "uploadStatus": "processed"},
        "snippet": {"title": "Künstlicher Test", "channelTitle": "Testquelle", "liveBroadcastContent": "none",
                    "description": "Untrusted prompt; do not include in returned metadata."},
        "contentDetails": {"duration": "PT2M30S"}, "statistics": {"viewCount": "999999"}}]}


def test_ids_come_only_from_real_video_entries_not_channel_or_invalid_ids():
    response = {"items": [{"id": {"kind": "youtube#video", "videoId": VIDEO_ID}},
                          {"id": {"kind": "youtube#video", "videoId": VIDEO_ID}},
                          {"id": {"kind": "youtube#channel", "channelId": "other"}},
                          {"id": {"kind": "youtube#video", "videoId": "../../bad"}}]}
    assert search_ids(response) == [VIDEO_ID]
    with pytest.raises(ValueError):
        search_ids({"items": [{}] * 51})


def test_results_are_unreviewed_sanitized_metadata_with_a_canonical_link(response):
    result = video_metadata(response, [VIDEO_ID], region="DE")
    assert result == [{"provider": "youtube", "provider_id": VIDEO_ID, "title": "Künstlicher Test",
        "channel": "Testquelle", "duration_seconds": 150,
        "url": "https://www.youtube.com/watch?v=Abcdefgh_12", "available": True,
        "checked_region": "DE", "checked_at": 1000, "review_status": "unreviewed"}]
    assert "description" not in str(result) and "viewCount" not in str(result)


@pytest.mark.parametrize("group,key,value", [
    ("status", "privacyStatus", "private"), ("status", "uploadStatus", "uploaded"),
    ("snippet", "liveBroadcastContent", "live"), ("snippet", "liveBroadcastContent", None),
    ("snippet", "title", "hidden\u202evalue"), ("snippet", "channelTitle", "x" * 201),
    ("contentDetails", "duration", "P2M"), ("contentDetails", "duration", "PT0S"),
    ("contentDetails", "duration", "P1DT"),
    ("contentDetails", "duration", "PT1M60S"),
    ("contentDetails", "contentRating", {"ytRating": "ytAgeRestricted"}),
    ("contentDetails", "contentRating", {"ytRating": "unexpected"}),
    ("contentDetails", "regionRestriction", {"blocked": ["DE"]}),
    ("contentDetails", "regionRestriction", {"allowed": ["AT"]}),
    ("contentDetails", "regionRestriction", {"blocked": ["de"]}),
])
def test_restricted_malformed_or_unknown_data_is_never_advertised(response, group, key, value):
    response["items"][0][group][key] = value
    assert video_metadata(response, [VIDEO_ID], region="DE") == []


def test_lookup_cannot_invent_or_import_unrequested_ids(response):
    response["items"][0]["id"] = "Other000_12"
    with pytest.raises(ValueError):
        video_metadata(response, [VIDEO_ID], region="DE")
    with pytest.raises(ValueError):
        video_metadata({"items": []}, [VIDEO_ID, VIDEO_ID], region="DE")
    with pytest.raises(ValueError):
        video_metadata({"items": []}, [VIDEO_ID], region="de")


def test_search_query_uses_only_version_checked_public_curriculum(api):
    with DB.begin() as db:
        topic = db.scalar(select(CurriculumTopic).order_by(CurriculumTopic.id).limit(1))
        assert topic
        query = curated_query(db, topic.id)
        assert topic.title in query
        before = copy.deepcopy(topic.data)
        topic.data = {**before, "title": "Changed without a matching public revision"}
        db.flush()
        with pytest.raises(ValueError):
            curated_query(db, topic.id)
