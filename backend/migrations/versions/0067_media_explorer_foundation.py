"""Add isolated public media candidates and revision-bound editorial evidence."""
import sqlalchemy as sa
from alembic import op

revision = "0067"
down_revision = "0066"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "media_resources",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("provider_id", sa.String(128), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("channel", sa.String(200), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("checked_region", sa.String(2), nullable=False),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("checked_at", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("provider", "provider_id", name="uq_media_provider_item"),
        sa.CheckConstraint("revision >= 1", name="ck_media_resource_revision"),
        sa.CheckConstraint("checked_at >= 0", name="ck_media_resource_check"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_duration"),
    )
    op.create_index("ix_media_resource_availability", "media_resources", ["available", "checked_at"])
    op.create_table(
        "media_curriculum_links",
        sa.Column("resource_id", sa.String(32), sa.ForeignKey("media_resources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("topic_id", sa.String(140), sa.ForeignKey("curriculum_topics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("topic_digest", sa.String(64), nullable=False),
        sa.Column("level_kind", sa.String(16), nullable=False),
        sa.Column("min_level", sa.Integer(), nullable=False),
        sa.Column("max_level", sa.Integer(), nullable=False),
        sa.CheckConstraint("min_level >= 1 AND max_level >= min_level", name="ck_media_level_range"),
    )
    op.create_index("ix_media_topic_level", "media_curriculum_links", ["topic_id", "level_kind", "min_level", "max_level"])
    op.create_table(
        "media_editorial_reviews",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("resource_id", sa.String(32), sa.ForeignKey("media_resources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_revision", sa.Integer(), nullable=False),
        sa.Column("review_number", sa.Integer(), nullable=False),
        sa.Column("reviewer_id", sa.String(32), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("evidence_scope", sa.String(16), nullable=False),
        sa.Column("content_kind", sa.String(24), nullable=False),
        sa.Column("min_age", sa.Integer(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("counterpoint", sa.Text(), nullable=False),
        sa.Column("reviewed_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("resource_revision >= 1", name="ck_media_review_revision"),
        sa.CheckConstraint("review_number >= 1", name="ck_media_review_number"),
        sa.CheckConstraint("min_age >= 0 AND min_age <= 99", name="ck_media_review_age"),
        sa.CheckConstraint("decision IN ('approved', 'rejected', 'blocked')", name="ck_media_review_decision"),
        sa.CheckConstraint("evidence_scope IN ('metadata', 'content')", name="ck_media_review_scope"),
        sa.CheckConstraint("content_kind IN ('general', 'historical_source', 'propaganda', 'sensitive')", name="ck_media_review_kind"),
        sa.UniqueConstraint("resource_id", "review_number", name="uq_media_review_number"),
    )
    op.create_index("ix_media_editorial_reviews_resource_id", "media_editorial_reviews", ["resource_id"])
    op.create_index("ix_media_review_latest", "media_editorial_reviews", ["resource_id", "review_number"])


def downgrade():
    raise RuntimeError("Published editorial evidence requires a forward correction.")
