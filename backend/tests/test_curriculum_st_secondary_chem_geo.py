"""Official subject scope; only explicitly starred grade-9 items are exact."""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from schulpilot import curriculum
from schulpilot.curriculum_schemas import CatalogueInput
from schulpilot.db import DB, Activity, Job, Subject, Usage
from schulpilot.db import engine as test_engine
from sqlalchemy import create_engine, event, func, select, text

SOURCE = Path(__file__).parents[1] / "schulpilot/reference/curriculum-st-sekundarschule-chemie-geographie-2019.json"


def package():
    return json.loads(SOURCE.read_text())


def test_official_scopes_and_grade_nine_footnotes():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.topics) == 22
    docs = {d.id: d for d in value.documents}
    assert set(docs) == {"st-sek-chemie-2019", "st-sek-geographie-2019"}
    assert all(
        (d.state_code, d.school_form_id, d.edition) == ("DE-ST", "de-st.sekundarschule", "01.08.2019")
        for d in docs.values()
    )
    assert all(d.source_status == "current_verified" and "CC BY-SA 3.0" in d.source_notes for d in docs.values())
    assert "f331d1430396c833b5aa8957f31f456b3f0a9b0eb42fd05c7d7505d15f2ae442" in docs["st-sek-chemie-2019"].source_notes
    assert (
        "fb6907714a209c8e2932c6aadb4e9680a080fb51205acf768c2400dc27ceecd8"
        in docs["st-sek-geographie-2019"].source_notes
    )
    for subject, count in [("chemie", 3), ("geographie", 2)]:
        rows = [t for t in value.topics if t.subject_key == subject]
        assert len(rows) == 11 and all(t.page and t.document_id == f"st-sek-{subject}-2019" for t in rows)
        exact = [t for t in rows if t.grade_kind == "exact"]
        assert len(exact) == count and all(t.grades == [9] and "Fußnote" in t.section for t in exact)
        assert all(t.grades in ([5, 6], [7, 8], [9, 10]) for t in rows if t.grade_kind == "band")


def test_import_and_read_are_idempotent_and_filter_grades(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        subject_ids = {
            s.key: s.id for s in db.scalars(select(Subject).where(Subject.key.in_(["chemie", "geographie"])))
        }
    with DB() as db:
        before = {m: db.scalar(select(func.count()).select_from(m)) for m in (Activity, Job, Usage)}

    def selected(subject, grade, form="de-st.sekundarschule"):
        response = api.get(
            "/api/curriculum/topics",
            params={
                "state_code": "DE-ST",
                "school_form_id": form,
                "subject_id": subject_ids[subject],
                "grade": grade,
                "limit": 50,
            },
        )
        assert response.status_code == 200
        return [r for r in response.json()["items"] if r["source"]["document_id"] == f"st-sek-{subject}-2019"]

    assert len(selected("geographie", 5)) == len(selected("geographie", 6)) == 3
    assert len(selected("geographie", 7)) == len(selected("geographie", 8)) == 4
    assert len(selected("geographie", 9)) == 4 and len(selected("geographie", 10)) == 2
    assert not selected("chemie", 6) and len(selected("chemie", 7)) == len(selected("chemie", 8)) == 6
    assert len(selected("chemie", 9)) == 5 and len(selected("chemie", 10)) == 2
    assert not selected("chemie", 7, "de-st.gymnasium")
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(m)) == before[m] for m in before)


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_upgrade_preserves_existing_private_evidence_and_is_idempotent(tmp_path, dialect):
    schema = None
    if dialect == "postgresql":
        if test_engine.dialect.name != "postgresql":
            pytest.skip("Requires isolated PostgreSQL.")
        schema = "st_chemgeo_" + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ["TEST_DATABASE_URL"], test_engine
    else:
        url = "sqlite:///" + str(tmp_path / "chemgeo.sqlite")
        engine = create_engine(url)

        @event.listens_for(engine, "connect")
        def enable_fk(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

    env = {**os.environ, "DATABASE_URL": url, "ENVIRONMENT": "test"}
    if schema:
        env["PGOPTIONS"] = f"-c search_path={schema}"
    command = [sys.executable, "-m", "alembic", "-c", str(Path(__file__).parents[1] / "alembic.ini"), "upgrade"]

    def scope(con):
        if schema:
            con.execute(text(f'SET LOCAL search_path TO "{schema}"'))

    try:
        result = subprocess.run([*command, "0053"], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        with engine.begin() as con:
            scope(con)
            con.execute(
                text("DELETE FROM curriculum_documents WHERE id IN ('st-sek-chemie-2019','st-sek-geographie-2019')")
            )
            con.execute(
                text(
                    "INSERT INTO families(id,name,synthetic,created,child_limit,call_limit,budget_micros,plan) VALUES('f','Synthetic',true,1,4,100,2000000,'Pilot')"
                )
            )
            con.execute(
                text(
                    "INSERT INTO users(id,username,display_name,password_hash,role,verified,disabled,created) VALUES('u','synthetic','Synthetic','SYNTHETIC-HASH','parent',true,false,1)"
                )
            )
            con.execute(
                text(
                    "INSERT INTO children(id,family_id,user_id,grade,subjects,school_type,region,preferences) VALUES('c','f','u',6,'[]','','','{}')"
                )
            )
            con.execute(
                text(
                    "INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Chemie','Test','Synthetic','[]','completed',true,'synthetic',1,300)"
                )
            )
            con.execute(
                text(
                    "INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"
                )
            )
        for _ in range(2):
            result = subprocess.run([*command, "0054"], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            with engine.begin() as con:
                scope(con)
                assert (
                    con.scalar(
                        text(
                            "SELECT count(*) FROM curriculum_topics WHERE document_id IN ('st-sek-chemie-2019','st-sek-geographie-2019')"
                        )
                    )
                    == 22
                )
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == "correct"
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
