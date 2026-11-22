"""Add sourced ST secondary chemistry and geography without learner writes."""
import json
from alembic import op
from sqlalchemy.orm import Session

revision = '0054'
down_revision = '0053'
branch_labels = depends_on = None


def upgrade():
    from schulpilot.curriculum import REFERENCE, import_catalogue

    path = REFERENCE / 'curriculum-st-sekundarschule-chemie-geographie-2019.json'
    with Session(bind=op.get_bind()) as db:
        import_catalogue(db, json.loads(path.read_text()))
        db.flush()


def downgrade():
    raise RuntimeError('Published curriculum evidence requires a forward correction.')
