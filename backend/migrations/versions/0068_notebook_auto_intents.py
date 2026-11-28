"""Persist bounded standalone notebook round preparation intents."""
import sqlalchemy as sa
from alembic import op

revision = "0068"
down_revision = "0067"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "notebook_auto_intents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("child_id", sa.String(32), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id", sa.String(32), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("session_id", sa.String(32), sa.ForeignKey("sessions.id", ondelete="SET NULL")),
        sa.Column("family_id", sa.String(32), nullable=False),
        sa.Column("selection", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("job_id", sa.String(32), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("material_id", "revision", name="uq_notebook_auto_revision"),
    )
    op.create_index("ix_notebook_auto_status_created", "notebook_auto_intents", ["status", "created", "id"])


def downgrade():
    raise RuntimeError("Published automatic notebook intents require a forward correction.")
