"""Per-account regulatory update read state."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    op.create_table(
        "regulatory_update_reads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "update_id",
            sa.String(36),
            sa.ForeignKey("regulatory_updates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "update_id"),
    )
    op.create_index(
        "ix_regulatory_update_reads_user_id", "regulatory_update_reads", ["user_id"]
    )
    op.create_index(
        "ix_regulatory_update_reads_update_id", "regulatory_update_reads", ["update_id"]
    )


def downgrade():
    op.drop_table("regulatory_update_reads")
