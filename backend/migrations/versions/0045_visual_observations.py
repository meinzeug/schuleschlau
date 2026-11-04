"""Store provisional image observations separately from literal transcription."""
import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = depends_on = None


def upgrade():
    op.add_column("materials", sa.Column("visual_observations", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    rows = op.get_bind().execute(sa.text("SELECT visual_observations FROM materials"))
    if any(value not in (None, [], "[]") for (value,) in rows):
        raise RuntimeError("Visual observations exist; use a forward correction.")
    with op.batch_alter_table("materials") as table:
        table.drop_column("visual_observations")
