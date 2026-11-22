import base64
import io
import json

import pytest
import httpx
from PIL import Image, PngImagePlugin

from schulpilot.public_image_contract import ImageContractError, parse_response, public_prompt, request_public_image


def response(image, *, cost=0.01030825):
    return json.dumps({"data": [{"b64_json": base64.b64encode(image).decode()}],
                       "usage": {"prompt_tokens": 39, "completion_tokens": 1024, "cost": cost}}).encode()


def image_bytes(size=(80, 80), *, metadata=False):
    out = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    if metadata:
        info.add_text("private", "must not survive")
    Image.new("RGB", size, "cyan").save(out, "PNG", pnginfo=info)
    return out.getvalue()


def test_provider_image_is_decoded_and_metadata_removed_with_billing():
    value = parse_response(response(image_bytes(metadata=True)))
    assert (value.width, value.height) == (80, 80)
    assert value.billing["cost_micros"] == 10309
    assert value.billing["cost_source"] == "reported"
    with Image.open(io.BytesIO(value.png)) as im:
        assert "private" not in im.info
        assert im.getpixel((0, 0)) == (0, 255, 255)


@pytest.mark.parametrize("payload,reason", [
    (b"not json", "response_json"),
    (json.dumps({"data": []}).encode(), "image_count"),
    (json.dumps({"data": [{"b64_json": "not base64!"}]}).encode(), "image_invalid"),
    (response(image_bytes((32, 32))), "image_dimensions"),
    (response(b"<svg></svg>"), "image_invalid"),
])
def test_invalid_provider_output_is_rejected(payload, reason):
    with pytest.raises(ImageContractError) as err:
        parse_response(payload)
    assert err.value.category == reason


def test_rejected_image_keeps_real_provider_cost():
    with pytest.raises(ImageContractError) as err:
        parse_response(response(image_bytes((32, 32))))
    assert err.value.billing["cost_micros"] == 10309


def test_missing_cost_is_unknown_not_free():
    raw = json.loads(response(image_bytes()))
    del raw["usage"]["cost"]
    result = parse_response(json.dumps(raw).encode())
    assert result.billing["cost_micros"] is None
    assert result.billing["cost_source"] == "unknown"


def test_multiple_images_are_not_accepted_and_keep_billing():
    raw = json.loads(response(image_bytes()))
    raw["data"].append(raw["data"][0])
    with pytest.raises(ImageContractError) as err:
        parse_response(json.dumps(raw).encode())
    assert err.value.category == "image_count"
    assert err.value.billing["cost_micros"] == 10309


def test_response_limit_rejects_before_parsing():
    from schulpilot.public_image_contract import MAX_RESPONSE_BYTES

    with pytest.raises(ImageContractError, match="response_size") as err:
        parse_response(b" " * (MAX_RESPONSE_BYTES + 1))
    assert err.value.billing is None


def test_prompt_uses_only_server_resolved_public_content(monkeypatch):
    from schulpilot import learning_assets

    selector = {"catalog_content_id": "public-id"}
    monkeypatch.setattr(learning_assets, "public_spec", lambda db, raw: {
        "subject": "Biologie", "catalog_topic": {"id": "public-topic"},
        "catalog_content": {"title": "Honigbienen"}})
    spec, prompt = public_prompt(None, selector)
    assert spec["catalog_content"]["title"] == "Honigbienen"
    assert '"topic": "Honigbienen"' in prompt
    assert "public-id" not in prompt


def test_prompt_does_not_accept_a_bare_unmatched_topic(monkeypatch):
    from schulpilot import learning_assets

    monkeypatch.setattr(learning_assets, "public_spec", lambda db, raw: {
        "subject": "Biologie", "catalog_topic": {"id": "public-topic"}, "catalog_content": None})
    with pytest.raises(ImageContractError, match="public_content_required"):
        public_prompt(None, {"catalog_topic_id": "public-topic"})


def test_prompt_accepts_server_curated_public_focus(monkeypatch):
    from schulpilot import learning_assets

    monkeypatch.setattr(learning_assets, "public_spec", lambda db, raw: {
        "subject": "Biologie", "catalog_topic": {"id": "public-topic"},
        "public_focus": {"id": "public-focus", "title": "Körperbau der Honigbiene"}})
    _, prompt = public_prompt(None, {"public_focus_id": "public-focus"})
    assert "Körperbau der Honigbiene" in prompt


def test_image_transport_pins_endpoint_privacy_and_single_public_prompt(monkeypatch):
    from schulpilot import learning_assets

    monkeypatch.setattr(learning_assets, "public_spec", lambda db, raw: {
        "subject": "Biologie", "catalog_topic": {"id": "public-topic"},
        "catalog_content": {"title": "Honigbienen"}})
    sent = []

    def reply(request):
        sent.append(request)
        return httpx.Response(200, content=response(image_bytes()))

    with httpx.Client(transport=httpx.MockTransport(reply)) as client:
        _, value = request_public_image(client, None, {"catalog_content_id": "public-id"},
            token="test-key", model="test/image-model", upstream="azure", region="standard")
    assert len(sent) == 1 and str(sent[0].url) == "https://openrouter.ai/api/v1/images"
    body = json.loads(sent[0].content)
    assert body["model"] == "test/image-model" and body["n"] == 1
    assert body["provider"] == {"only": ["azure"], "allow_fallbacks": False,
                                "data_collection": "deny", "zdr": True}
    assert "public-id" not in body["prompt"]
    assert value.billing["cost_micros"] == 10309


def test_redirect_is_not_followed(monkeypatch):
    from schulpilot import learning_assets

    monkeypatch.setattr(learning_assets, "public_spec", lambda db, raw: {
        "subject": "Biologie", "catalog_topic": {"id": "public-topic"},
        "catalog_content": {"title": "Honigbienen"}})
    seen = []
    def redirect(request):
        seen.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://example.org/"})
    with httpx.Client(transport=httpx.MockTransport(redirect), follow_redirects=True) as client:
        with pytest.raises(ImageContractError, match="provider_http") as err:
            request_public_image(client, None, {}, token="test-key", model="test/image-model",
                                 upstream="azure", region="standard")
    assert len(seen) == 1 and err.value.billing is None
