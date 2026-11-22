"""Add curated ST secondary subject references without changing learner data."""
from alembic import op
from sqlalchemy.orm import Session

revision = '0052'
down_revision = '0051'
branch_labels = depends_on = None


def upgrade():
    from schulpilot.curriculum import seed_additional

    # Join the migration transaction; the normal importer verifies host,
    # immutable document versions, subject identities and original year bands.
    with Session(bind=op.get_bind()) as db:
        seed_additional(db)
        db.flush()


def downgrade():
    raise RuntimeError('Published curriculum evidence requires a forward correction.')
