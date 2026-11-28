"""Add Astronomie as a separate subject and sourced ST overview."""
import json

from alembic import op
from sqlalchemy.orm import Session

revision = "0064"
down_revision = "0063"
branch_labels = depends_on = None


def upgrade():
    from schulpilot.curriculum import REFERENCE, import_catalogue
    from schulpilot.subject_registry import seed_additional_v3

    connection = op.get_bind()
    seed_additional_v3(connection)
    path = REFERENCE / "curriculum-st-sekundarschule-astronomie-2019.json"
    with Session(bind=connection) as db:
        import_catalogue(db, json.loads(path.read_text()))
        db.flush()


def downgrade():
    raise RuntimeError("Published subject and curriculum evidence require a forward correction.")
