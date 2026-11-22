"""Metadata-only explicit beta applications and decisions."""
import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = depends_on = None


def upgrade():
    op.create_table("beta_applications",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("family_id", sa.String(32), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(32), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.Integer()),
        sa.Column("decided_at", sa.Integer()),
        sa.Column("decided_by", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.CheckConstraint("status IN ('pending','approved','rejected','revoked')", name="ck_beta_status"),
        sa.CheckConstraint("revision >= 1", name="ck_beta_revision"))


def downgrade():
    raise RuntimeError("Beta decisions are audit evidence; use a forward correction.")
