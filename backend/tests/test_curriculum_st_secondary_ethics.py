"""Sourced ST ethics overview: grade bands, read-only use and migration."""
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

SOURCE = Path(__file__).parents[1] / "schulpilot/reference/curriculum-st-sekundarschule-ethik-2019.json"


def package():
    return json.loads(SOURCE.read_text())


def test_source_scope_and_three_bands():
    value = CatalogueInput.model_validate(package())
    assert value.coverage.complete is False and len(value.documents) == 1 and len(value.topics) == 21
    document = value.documents[0]
    assert (document.state_code, document.school_form_id, document.edition) == (
        "DE-ST", "de-st.sekundarschule", "01.08.2019")
    assert document.source_status == "current_verified" and "CC BY-SA 3.0" in document.source_notes
    assert "27de7a705c3df422292adf8176408b3ecf2cfde097f0a39ddaa5f5d809a2e487" in document.source_notes
    for grades in ([5, 6], [7, 8], [9, 10]):
        rows = [row for row in value.topics if row.grades == grades]
        assert len(rows) == 7
        assert all(row.grade_kind == "band" and row.page == 8 and row.section == "3.1" for row in rows)
        assert all(row.subject_key == "ethik" and row.canonical_topic_key is None for row in rows)


def test_import_and_read_are_idempotent_and_filter_bands(api, household):
    with DB.begin() as db:
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        assert curriculum.import_catalogue(db, package())["topics_added"] == 0
        subject_id = db.scalar(select(Subject.id).where(Subject.key == "ethik", Subject.owner_family_id.is_(None)))
    with DB() as db:
        before = {model: db.scalar(select(func.count()).select_from(model)) for model in (Activity, Job, Usage)}

    def selected(grade, form="de-st.sekundarschule"):
        response = api.get("/api/curriculum/topics", params={"state_code": "DE-ST", "school_form_id": form,
                           "subject_id": subject_id, "grade": grade, "limit": 50})
        assert response.status_code == 200
        return [row for row in response.json()["items"] if row["source"]["document_id"] == "st-sek-ethik-2019"]

    assert not selected(4) and not selected(11)
    for grade in range(5, 11):
        assert len(selected(grade)) == 7
    assert not selected(6, "de-st.gymnasium")
    with DB() as db:
        assert all(db.scalar(select(func.count()).select_from(model)) == before[model] for model in before)


@pytest.mark.parametrize("dialect", ["sqlite", "postgresql"])
def test_upgrade_preserves_existing_private_evidence_and_is_idempotent(tmp_path, dialect):
    schema = None
    if dialect == "postgresql":
        if test_engine.dialect.name != "postgresql":
            pytest.skip("Requires isolated PostgreSQL.")
        schema = "st_ethics_" + uuid.uuid4().hex
        with test_engine.begin() as con:
            con.execute(text(f'CREATE SCHEMA "{schema}"'))
        url, engine = os.environ["TEST_DATABASE_URL"], test_engine
    else:
        url = "sqlite:///" + str(tmp_path / "ethics.sqlite")
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
        result = subprocess.run([*command, "0055"], env=env, capture_output=True)
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        with engine.begin() as con:
            scope(con)
            con.execute(
                text("DELETE FROM curriculum_documents WHERE id = 'st-sek-ethik-2019'")
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
            result = subprocess.run([*command, "0056"], env=env, capture_output=True)
            assert result.returncode == 0, result.stderr.decode(errors="replace")
            with engine.begin() as con:
                scope(con)
                assert (
                    con.scalar(
                        text(
                            "SELECT count(*) FROM curriculum_topics WHERE document_id = 'st-sek-ethik-2019'"
                        )
                    )
                    == 21
                )
                assert con.scalar(text("SELECT outcome FROM attempts WHERE id='attempt'")) == "correct"
                assert con.scalar(text("SELECT active_seconds FROM learning_units WHERE id='unit'")) == 300
    finally:
        if schema:
            with test_engine.begin() as con:
                con.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        else:
            engine.dispose()
