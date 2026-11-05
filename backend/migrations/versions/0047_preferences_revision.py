"""Version child learning preferences for explicit concurrent edits."""

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = depends_on = None


def upgrade():
    op.add_column("children", sa.Column("preferences_revision", sa.Integer(), nullable=False, server_default="1"))


def downgrade():
    raise RuntimeError("Preferences revision protects concurrent changes; use a forward correction.")
