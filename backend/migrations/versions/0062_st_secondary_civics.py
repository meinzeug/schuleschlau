"""Add the sourced ST secondary civic-education overview."""
import json

from alembic import op
from sqlalchemy.orm import Session

revision = "0062"
down_revision = "0061"
branch_labels = depends_on = None


def upgrade():
    from schulpilot.curriculum import REFERENCE, import_catalogue

    path = REFERENCE / "curriculum-st-sekundarschule-sozialkunde-2019.json"
    with Session(bind=op.get_bind()) as db:
        import_catalogue(db, json.loads(path.read_text()))
        db.flush()


def downgrade():
    raise RuntimeError("Published curriculum evidence requires a forward correction.")
