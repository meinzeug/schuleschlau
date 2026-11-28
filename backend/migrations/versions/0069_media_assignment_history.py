"""Make editorial media mappings revisioned and retain their changes."""
import sqlalchemy as sa
from alembic import op

revision = "0069"
down_revision = "0068"
branch_labels = depends_on = None


def upgrade():
    # Existing links remain active and retain their original pedagogical scope.
    op.add_column("media_curriculum_links", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("media_curriculum_links", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table(
        "media_curriculum_link_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("resource_id", sa.String(32), sa.ForeignKey("media_resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.String(140), sa.ForeignKey("curriculum_topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("topic_digest", sa.String(64), nullable=False),
        sa.Column("min_level", sa.Integer(), nullable=False),
        sa.Column("max_level", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("resource_id", "topic_id", "revision", name="uq_media_link_event_revision"),
        sa.CheckConstraint("action IN ('inherited', 'created', 'updated', 'removed', 'restored')", name="ck_media_link_event_action"),
    )
    op.create_index("ix_media_link_event_history", "media_curriculum_link_events", ["resource_id", "topic_id", "revision"])


def downgrade():
    raise RuntimeError("Published editorial mapping history requires a forward correction.")
