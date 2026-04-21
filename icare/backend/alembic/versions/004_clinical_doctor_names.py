"""Add doctor_name to prescriptions and appointments (clinical records).

Revision ID: 004_clinical_doctor_names
Revises: 003_alerts_escalation
Create Date: 2026-04-21

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_clinical_doctor_names"
down_revision: Union[str, None] = "003_alerts_escalation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS doctor_name VARCHAR(255)"))
    op.execute(sa.text("ALTER TABLE appointments ADD COLUMN IF NOT EXISTS doctor_name VARCHAR(255)"))


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE appointments DROP COLUMN IF EXISTS doctor_name"))
    op.execute(sa.text("ALTER TABLE prescriptions DROP COLUMN IF EXISTS doctor_name"))
