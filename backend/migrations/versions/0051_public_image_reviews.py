"""Versioned machine assessments of already sanitised public images."""
import sqlalchemy as sa
from alembic import op

revision = '0051'
down_revision = '0050'
branch_labels = depends_on = None


def upgrade():
    op.create_table('public_image_reviews',
        sa.Column('image_key', sa.String(64), sa.ForeignKey('public_images.cache_key', ondelete='CASCADE'), primary_key=True),
        sa.Column('job_id', sa.String(32), sa.ForeignKey('jobs.id', ondelete='SET NULL'), unique=True),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('image_sha256', sa.String(64), nullable=False),
        sa.Column('specification_digest', sa.String(64), nullable=False),
        sa.Column('review_version', sa.String(40), nullable=False),
        sa.Column('reviewer_model', sa.String(160)),
        sa.Column('reviewer_upstream', sa.String(100)),
        sa.Column('reference_available', sa.Integer(), nullable=False),
        sa.Column('assessment', sa.JSON()),
        sa.Column('updated', sa.Integer(), nullable=False),
        sa.CheckConstraint("status IN ('pending','approved','rejected','uncertain','unavailable')", name='ck_public_image_review_status'),
        sa.CheckConstraint('attempts >= 0 AND attempts <= 2', name='ck_public_image_review_attempts'),
        sa.CheckConstraint('reference_available IN (0, 1)', name='ck_public_image_review_reference'))


def downgrade():
    raise RuntimeError('Public image review evidence requires a forward correction.')
