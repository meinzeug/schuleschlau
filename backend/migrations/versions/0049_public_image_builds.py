"""Track deduplicated public illustration jobs without exposing child data."""
import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = depends_on = None


def upgrade():
    op.create_table("public_image_builds",
        sa.Column("lookup_key", sa.String(64), primary_key=True),
        sa.Column("specification", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("job_id", sa.String(32), sa.ForeignKey("jobs.id", ondelete="SET NULL")),
        sa.Column("image_key", sa.String(64), sa.ForeignKey("public_images.cache_key", ondelete="SET NULL")),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False))


def downgrade():
    raise RuntimeError("Public image jobs require an explicit retention decision.")
