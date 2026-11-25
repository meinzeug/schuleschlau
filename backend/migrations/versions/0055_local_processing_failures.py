"""Bounded private technical receipts for pre-job failures."""
import sqlalchemy as sa
from alembic import op

revision = "0055"
down_revision = "0054"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "local_processing_failures",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("child_id", sa.String(32), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.String(32), sa.ForeignKey("learning_units.id", ondelete="CASCADE")),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
    )
    for column in ("child_id", "unit_id", "created"):
        op.create_index(f"ix_local_processing_failures_{column}", "local_processing_failures", [column])


def downgrade():
    raise RuntimeError("Private diagnostic retention requires an explicit forward correction.")
