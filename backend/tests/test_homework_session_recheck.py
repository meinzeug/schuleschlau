"""A child request waiting for the material lock must not use stale access."""

import pytest
from fastapi import HTTPException
from schulpilot.db import DB, Child, Material, Session, User, now
from schulpilot.homework import own_material
from schulpilot.security import Principal, digest
from sqlalchemy import select
from test_vocabulary import child_login


@pytest.mark.parametrize("change", ["unverified", "inactive", "other_user"])
def test_homework_write_rechecks_session_and_account_after_wait(api, household, change):
    parent, child = household
    child_login(api)
    token = api.headers["Authorization"].removeprefix("Bearer ")
    with DB.begin() as db:
        material = Material(child_id=child["id"], purpose="homework", title="Künstliche Aufgabe",
            subject="Mathematik", topic="Übung", content="Wie viel ist 2 + 2?", confirmed=True, status="confirmed")
        db.add(material)
        db.flush()
        material_id = material.id
    with DB() as db:
        session = db.scalar(select(Session).where(Session.token_hash == digest(token)))
        user = db.get(User, db.get(Child, child["id"]).user_id)
        principal = Principal(user, session)
        if change == "unverified":
            user.verified = False
        elif change == "inactive":
            session.seen = int(now()) - 7 * 86400 - 1
        else:
            session.user_id = parent["id"]
        with pytest.raises(HTTPException) as raised:
            own_material(db, principal, material_id, write=True)
        assert raised.value.status_code == 401
