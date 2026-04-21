"""Vitals offline queue + per-patient threshold overrides.

Revision ID: 002_vitals_thresholds
Revises: 001_users_health
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_vitals_thresholds"
down_revision: Union[str, None] = "001_users_health"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS vitals_queue CASCADE"))
    op.create_table(
        "vitals_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vitals_queue_patient_id"), "vitals_queue", ["patient_id"], unique=False)
    op.create_index(op.f("ix_vitals_queue_metric"), "vitals_queue", ["metric"], unique=False)
    op.create_index(op.f("ix_vitals_queue_synced"), "vitals_queue", ["synced"], unique=False)

    op.create_table(
        "patient_vitals_thresholds",
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("patient_id"),
    )


def downgrade() -> None:
    op.drop_table("patient_vitals_thresholds")
    op.drop_index(op.f("ix_vitals_queue_synced"), table_name="vitals_queue")
    op.drop_index(op.f("ix_vitals_queue_metric"), table_name="vitals_queue")
    op.drop_index(op.f("ix_vitals_queue_patient_id"), table_name="vitals_queue")
    op.drop_table("vitals_queue")
