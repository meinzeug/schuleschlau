"""Allow versioned, opaque source references in the erasure outbox."""
import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = depends_on = None


def upgrade():
    op.add_column("erasure_requests", sa.Column("details", sa.JSON(), nullable=True))


def downgrade():
    if op.get_bind().scalar(sa.text("SELECT count(*) FROM erasure_requests WHERE details IS NOT NULL")):
        raise RuntimeError("Versioned erasure records exist; use a forward correction.")
    with op.batch_alter_table("erasure_requests") as table:
        table.drop_column("details")
