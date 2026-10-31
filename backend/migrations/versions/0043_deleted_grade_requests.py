"""Prevent retries from recreating a grade after explicit deletion."""

import sqlalchemy as sa
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "deleted_grade_requests",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("child_id", sa.String(32), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_key_digest", sa.String(64), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("child_id", "request_key_digest", name="uq_deleted_grade_request"),
    )
    op.create_index("ix_deleted_grade_requests_child_id", "deleted_grade_requests", ["child_id"])
    op.create_index("ix_deleted_grade_requests_created", "deleted_grade_requests", ["created"])
    op.create_table(
        "grade_import_grade_links",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("child_id", sa.String(32), sa.ForeignKey("children.id", ondelete="CASCADE"), nullable=False),
        sa.Column("import_id", sa.String(32), sa.ForeignKey("grade_imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grade_id", sa.String(32), sa.ForeignKey("school_grades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_index", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.UniqueConstraint("import_id", "entry_index", name="uq_grade_import_entry_link"),
    )
    for key in ("child_id", "import_id", "grade_id"):
        op.create_index(f"ix_grade_import_grade_links_{key}", "grade_import_grade_links", [key])


def downgrade():
    if (op.get_bind().scalar(sa.text("SELECT count(*) FROM deleted_grade_requests"))
            or op.get_bind().scalar(sa.text("SELECT count(*) FROM grade_import_grade_links"))):
        raise RuntimeError("Grade deletion records or source links exist; use a forward correction.")
    op.drop_table("grade_import_grade_links")
    op.drop_table("deleted_grade_requests")
