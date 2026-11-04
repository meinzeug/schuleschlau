"""Artificial malformed upload pointers never become filesystem authority."""

import io
import json
import os
import zipfile
from types import SimpleNamespace

import pytest
from schulpilot import private_images
from schulpilot.config import settings
from schulpilot.db import DB, Material
from schulpilot.families import unlink_uploads
from schulpilot.private_images import MAX_IMAGE_BYTES, read


def test_bounded_read_rejects_traversal_links_and_nonregular_files(tmp_path, monkeypatch):
    monkeypatch.setattr(private_images, "settings", SimpleNamespace(data_dir=tmp_path))
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "normal.jpg").write_bytes(b"synthetic photo")
    secret = tmp_path / "secret.jpg"
    secret.write_bytes(b"synthetic private content")
    (uploads / "link.jpg").symlink_to(secret)
    os.link(secret, uploads / "hardlink.jpg")
    os.mkfifo(uploads / "pipe.jpg")
    with (uploads / "large.jpg").open("wb") as image:
        image.truncate(MAX_IMAGE_BYTES + 1)
    assert read("normal.jpg") == b"synthetic photo"
    for name in ("../secret.jpg", str(secret), "link.jpg", "hardlink.jpg", "pipe.jpg", "large.jpg", "x\x00.jpg", None):
        assert read(name) is None
    with pytest.raises(ValueError):
        unlink_uploads(["../secret.jpg", str(secret)])
    assert secret.read_bytes() == b"synthetic private content"


@pytest.mark.parametrize("bad_name", ["../secret.jpg", "link.jpg"])
def test_image_and_exports_do_not_follow_invalid_material_path(api, household, bad_name):
    user, child = household
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(exist_ok=True)
    secret = settings.data_dir / "secret.jpg"
    secret.write_bytes(b"SYNTHETIC-DO-NOT-EXPOSE")
    link = uploads / "link.jpg"
    link.unlink(missing_ok=True)
    link.symlink_to(secret)
    (uploads / "normal.jpg").write_bytes(b"SYNTHETIC-OWN-PHOTO")
    with DB.begin() as db:
        bad = Material(child_id=child["id"], title="Ungültiger Fotopfad", path=bad_name)
        good = Material(child_id=child["id"], title="Eigene Seite", path="normal.jpg")
        db.add_all([bad, good])
        db.flush()
        bad_id, good_id = bad.id, good.id
    assert api.get(f"/api/materials/{bad_id}/image").status_code == 404
    assert api.get(f"/api/materials/{good_id}/image").content == b"SYNTHETIC-OWN-PHOTO"
    for route in (f'/api/children/{child["id"]}/export',
                  f'/api/families/{user["families"][0]["id"]}/export'):
        response = api.get(route)
        assert response.status_code == 200
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert archive.read("materials/normal.jpg") == b"SYNTHETIC-OWN-PHOTO"
            assert json.loads(archive.read("fehlende-fotos.json"))["material_ids"] == [bad_id]
            assert all(not name.endswith("link.jpg") and ".." not in name for name in archive.namelist())
            assert b"SYNTHETIC-DO-NOT-EXPOSE" not in b"".join(archive.read(name) for name in archive.namelist())


def test_upload_directory_symlink_is_not_followed(tmp_path, monkeypatch):
    monkeypatch.setattr(private_images, "settings", SimpleNamespace(data_dir=tmp_path))
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "normal.jpg").write_bytes(b"synthetic private image")
    (tmp_path / "uploads").symlink_to(outside, target_is_directory=True)
    assert read("normal.jpg") is None


def test_removing_when_upload_directory_is_absent_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(private_images, "settings", SimpleNamespace(data_dir=tmp_path))
    private_images.remove("a" * 32 + ".jpg")
    assert not (tmp_path / "uploads").exists()
