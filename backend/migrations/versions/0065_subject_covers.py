"""Add approved public notebook covers without changing private subjects."""
from alembic import op

revision = "0065"
down_revision = "0064"
branch_labels = depends_on = None


def upgrade():
    from schulpilot.subject_registry import seed_public_covers_v4

    seed_public_covers_v4(op.get_bind())


def downgrade():
    raise RuntimeError("Published subject cover identities require a forward correction.")
