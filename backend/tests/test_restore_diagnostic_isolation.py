"""Journal replay must not unlink a live operator diagnostic file."""

import pytest
from schulpilot.config import settings
from schulpilot.db import DB, Child, ErasureRequest, Material
from schulpilot.erasure import reconcile
from schulpilot.source_evaluation import WORK_ID
from schulpilot.source_lineage_models import SourceEvaluationBudget, SourceEvaluationCase
from sqlalchemy import select
from test_notebook_actions import photo


@pytest.mark.parametrize("scope", ["material", "child", "family"])
def test_replay_preserves_operator_diagnostics(api, household, scope):
    _, child = household
    material_id, _ = photo(api, child)
    case_id = "d" * 32
    with DB.begin() as db:
        family_id = db.get(Child, child["id"]).family_id
        db.add(SourceEvaluationBudget(id=WORK_ID, limit_micros=1))
        db.flush()
        db.add(SourceEvaluationCase(id=case_id, work_id=WORK_ID, material_id=material_id,
                                    tier="test", status="completed", reserved_micros=0))
    directory = settings.data_dir / "operator-diagnostics" / WORK_ID
    directory.mkdir(parents=True, exist_ok=True)
    marker = directory / (case_id + ".json")
    marker.write_text("synthetic diagnostic")
    target = {"material": material_id, "child": child["id"], "family": family_id}[scope]
    with DB.begin() as db:
        reconcile(db, [{"scope": scope, "target": target}])
    assert marker.read_text() == "synthetic diagnostic"
    with DB() as db:
        assert db.get(Material, material_id) is None
        assert not list(db.scalars(select(ErasureRequest.id)))
