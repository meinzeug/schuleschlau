"""Official physics scope: no guessed grade or graduation track."""

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

SOURCE = Path(__file__).parents[1] / "schulpilot/reference/curriculum-st-sekundarschule-physik-2019.json"


def package():
    return json.loads(SOURCE.read_text())


def test_official_physics_scope_and_alternatives():
    value = CatalogueInput.model_validate(package())
    doc = value.documents[0]
    assert (doc.state_code, doc.school_form_id, doc.edition) == ("DE-ST", "de-st.sekundarschule", "01.08.2019")
    assert doc.source_status == "current_verified" and "CC BY-SA 3.0" in doc.source_notes
    assert "f5f801f566956e9049142361831306184c18e2bc1ddad3eb339b6578e3b9cbdb" in doc.source_notes
    assert value.coverage.complete is False and len(value.topics) == 17
    assert len([t for t in value.topics if t.grade_kind == "exact" and t.grades == [6]]) == 3
    assert len([t for t in value.topics if t.grade_kind == "band" and t.grades == [7, 8]]) == 4
    phases = [t for t in value.topics if t.grade_kind == "phase"]
    assert len(phases) == 10 and all(t.grades is None for t in phases)
    assert sum("Wahlalternative" in t.title for t in phases) == 2
    assert all(t.subject_key == "physik" and t.page and t.document_id == doc.id for t in value.topics)


def test_import_is_idempotent_and_grade_scope_never_invents_track(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == "physik"))
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)}

    def selected(grade=None, form="de-st.sekundarschule", phase=None):
        params = {"state_code": "DE-ST", "school_form_id": form, "subject_id": subject_id, "limit": 50}
        if grade is not None:
            params["grade"] = grade
        if phase:
            params["phase"] = phase
        response = api.get("/api/curriculum/topics", params=params)
        assert response.status_code == 200
        return [r for r in response.json()["items"] if r["source"]["document_id"] == "st-sek-physics-2019"]

    assert not selected(5)
    assert len(selected(6)) == 3 and len(selected(7)) == len(selected(8)) == 4
    assert not selected(9) and not selected(10) and not selected(6, "de-st.gymnasium")
    assert len(selected(phase="Realschulabschlussbezogener Unterricht (9/10)")) == 7
    assert len(selected(phase="Hauptschulabschlussbezogener Unterricht (9)")) == 3
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(m)) == before[m] for m in before)


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_upgrade_adds_public_physics_without_changing_private_work(tmp_path, dialect):
    schema = None
    if dialect == "postgresql":
        if test_engine.dialect.name != "postgresql":
            pytest.skip("Requires isolated PostgreSQL.")
        schema = "st_physics_" + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ["TEST_DATABASE_URL"], test_engine
    else:
        url = "sqlite:///" + str(tmp_path / "physics.sqlite")
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
        result = subprocess.run([*command, "0052"], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        with engine.begin() as con:
            scope(con)
            con.execute(text("DELETE FROM curriculum_documents WHERE id='st-sek-physics-2019'"))
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
                    "INSERT INTO learning_units(id,child_id,subject,topic,explanation,questions,status,synthetic,provider,created,active_seconds) VALUES('unit','c','Physik','Test','Synthetic','[]','completed',true,'synthetic',1,300)"
                )
            )
            con.execute(
                text(
                    "INSERT INTO attempts(id,unit_id,question_id,answer,outcome,assisted,created) VALUES('attempt','unit','q1','\"synthetic\"','correct',false,1)"
                )
            )
        for _ in range(2):
            result = subprocess.run([*command, "0053"], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            with engine.begin() as con:
                scope(con)
                assert (
                    con.scalar(text("SELECT count(*) FROM curriculum_topics WHERE document_id='st-sek-physics-2019'"))
                    == 17
                )
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == "correct"
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
