"""Artificial notebook browsing must stay private and have no learning effects."""

from conftest import create_child
from schulpilot.db import DB, Activity, Attempt, Job, LearningUnit, Material, Usage
from sqlalchemy import func, select
from test_notebook_actions import kid, photo


def test_browsing_five_photo_sources_is_private_bounded_and_read_only(api, household):
    parent, child = household
    sibling = create_child(api, parent, "private-sibling")
    titles = ["Arbeitsblatt", "Hefter", "Arbeitsheft", "Buchseite", "Testseite"]
    pages = [photo(api, child, title=title)[0] for title in titles]
    private, _ = photo(api, sibling, title="Privat")
    # Many pages exercise stable pagination without disclosing contents.
    with DB.begin() as db:
        for n in range(42):
            db.add(Material(child_id=child["id"], title=f"Zusatz {n:02}",
                            subject="Mathematik", content="INHALT PRIVAT", created=1000+n))

    def counts():
        with DB() as db:
            return tuple(db.scalar(select(func.count()).select_from(model))
                         for model in (Job, Usage, LearningUnit, Attempt, Activity))

    before = counts()
    with kid() as client:
        url = f"/api/children/{child['id']}/materials"
        all_ids = []
        for number in (1, 2, 3):
            response = client.get(url, params={"page": number, "sort": "oldest"})
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 47 and len(data["items"]) <= 20
            assert "INHALT PRIVAT" not in response.text
            all_ids.extend(item["id"] for item in data["items"])
        assert len(set(all_ids)) == 47
        for title, page in zip(titles, pages, strict=True):
            result = client.get(url, params={"q": title}).json()
            assert page in [item["id"] for item in result["items"]]
            image = client.get(f"/api/materials/{page}/image")
            assert image.status_code == 200
            assert image.headers["cache-control"] == "no-store"
        assert client.get(f"/api/materials/{private}/image").status_code == 404
        assert client.get(f"/api/children/{sibling['id']}/materials").status_code == 404
    assert counts() == before
