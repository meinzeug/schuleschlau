"""Public-only immutable generated illustration cache."""
import sqlalchemy as sa
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = depends_on = None


def upgrade():
    op.create_table("public_images",
        sa.Column("cache_key", sa.String(64), primary_key=True),
        sa.Column("lookup_key", sa.String(64), nullable=False),
        sa.Column("specification", sa.JSON(), nullable=False),
        sa.Column("format_version", sa.String(40), nullable=False),
        sa.Column("model", sa.String(160), nullable=False),
        sa.Column("upstream", sa.String(100), nullable=False),
        sa.Column("region", sa.String(20), nullable=False),
        sa.Column("png", sa.LargeBinary(), nullable=False),
        sa.Column("png_sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("factual_status", sa.String(24), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False))
    op.create_index("ix_public_images_lookup_key", "public_images", ["lookup_key"])


def downgrade():
    raise RuntimeError("Public generated image versions require an explicit retention decision.")
