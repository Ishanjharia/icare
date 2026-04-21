"""Alerts table (UUID PK) + caregiver_phone on health_profiles.

Revision ID: 003_alerts_escalation
Revises: 002_vitals_thresholds
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_alerts_escalation"
down_revision: Union[str, None] = "002_vitals_thresholds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "health_profiles",
        sa.Column("caregiver_phone", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vital_type", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sms_sent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("caregiver_notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_patient_id"), "alerts", ["patient_id"], unique=False)
    op.create_index(op.f("ix_alerts_vital_type"), "alerts", ["vital_type"], unique=False)
    op.create_index(
        "ix_alerts_patient_ack",
        "alerts",
        ["patient_id", "acknowledged"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_patient_ack", table_name="alerts")
    op.drop_index(op.f("ix_alerts_vital_type"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_patient_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_column("health_profiles", "caregiver_phone")
