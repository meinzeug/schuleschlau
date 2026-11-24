"""Add the source-linked ST secondary physics headings without learner writes."""
import json

from alembic import op
from sqlalchemy.orm import Session

revision = '0053'
down_revision = '0052'
branch_labels = depends_on = None


def upgrade():
    from schulpilot.curriculum import REFERENCE, import_catalogue

    path = REFERENCE / 'curriculum-st-sekundarschule-physik-2019.json'
    with Session(bind=op.get_bind()) as db:
        import_catalogue(db, json.loads(path.read_text()))
        db.flush()


def downgrade():
    raise RuntimeError('Published curriculum evidence requires a forward correction.')
