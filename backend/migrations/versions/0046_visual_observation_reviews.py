"""Separate user reviews of provisional visual observations."""
import sqlalchemy as sa
from alembic import op

revision = "0046"
down_revision = "0045"
branch_labels = depends_on = None


def upgrade():
    op.create_table("visual_observation_reviews",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("material_id", sa.String(32), sa.ForeignKey("materials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("child_id", sa.String(32), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("source_revision", sa.Integer(), nullable=False),
        sa.Column("image_digest", sa.String(64)),
        sa.Column("observations_digest", sa.String(64), nullable=False),
        sa.Column("observation_index", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("observation", sa.JSON(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("material_id", "source_revision", "observations_digest", "observation_index", "version", name="uq_visual_observation_review"))
    op.create_index("ix_visual_observation_reviews_material_id", "visual_observation_reviews", ["material_id"])
    op.create_index("ix_visual_observation_reviews_child_id", "visual_observation_reviews", ["child_id"])


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM visual_observation_reviews")):
        raise RuntimeError("Visual observation reviews exist; use a forward correction.")
    op.drop_table("visual_observation_reviews")
