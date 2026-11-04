"""Deleting a DB row must journal it even when file removal is unsafe."""

from types import SimpleNamespace

import pytest
from schulpilot import private_images
from schulpilot.config import settings
from schulpilot.db import DB, ErasureRequest, Material
from schulpilot.erasure import verify
from sqlalchemy import select
from test_notebook_actions import photo
from test_unconfirmed_deletion import review_day


@pytest.mark.parametrize("route", ["notebook", "school_day"])
def test_failed_upload_directory_removal_preserves_journal_and_does_not_report_success(
    api, household, monkeypatch, tmp_path, route
):
    _, child = household
    if route == "notebook":
        material_id, _ = photo(api, child)
        result = api.post(f"/api/children/{child['id']}/materials/delete-preview", json={"ids": [material_id]})
        assert result.status_code == 200
        token = result.json()["selection_token"]
    else:
        day, ids, _ = review_day(api, child, monkeypatch, count=1)
        material_id = ids[0]
    with DB() as db:
        material = db.get(Material, material_id)
        name = material.path
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / name).write_bytes(b"synthetic image")
    (tmp_path / "uploads").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(private_images, "settings", SimpleNamespace(data_dir=tmp_path))
    if route == "notebook":
        response = api.post(f"/api/children/{child['id']}/materials/bulk-delete", json={
            "selection_token": token, "delete_linked_units": True,
        })
    else:
        response = api.delete(f"/api/school-days/{day['id']}/pages/{material_id}")
    assert response.status_code == 500
    assert (outside / name).read_bytes() == b"synthetic image"
    with DB() as db:
        assert db.get(Material, material_id) is None
        row = db.scalar(select(ErasureRequest).where(ErasureRequest.scope == "material", ErasureRequest.target == material_id))
        assert row and row.published
    records = [verify(line, settings.master_key) for line in (settings.data_dir / "erasure-ledger.jsonl").read_text().splitlines()]
    assert any(row["scope"] == "material" and row["target"] == material_id for row in records)
