"""Add link-loss, dose-breakdown and radiation-zone columns (contracts 03 and 04)

The columns are nullable so the rollout is safe in any order after this migration:
rows written before the simulator produces these fields keep NULL, meaning "not
computed yet", and an older consumer can still insert. Adding a nullable column with
no default does not rewrite the hypertables.

Revision ID: c4e8a1f26b3d
Revises: d5159fa9708e
Create Date: 2026-11-22 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4e8a1f26b3d'
down_revision: str | Sequence[str] | None = 'd5159fa9708e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_COLUMNS = {
    'comms_output': (
        ('link_loss_reason', sa.String(length=20)),
    ),
    'radiation_output': (
        ('belt_dose_rate_rad_s', sa.Double()),
        ('gcr_dose_rate_rad_s', sa.Double()),
        ('cumulative_belt_dose_krad', sa.Double()),
        ('radiation_zone', sa.String(length=20)),
    ),
    'telemetry_packet': (
        ('dsn_visibility', sa.Boolean()),
        ('link_loss_reason', sa.String(length=20)),
        ('radiation_zone', sa.String(length=20)),
    ),
}


def upgrade() -> None:
    """Upgrade schema."""
    for table, columns in NEW_COLUMNS.items():
        for name, column_type in columns:
            op.add_column(table, sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table, columns in NEW_COLUMNS.items():
        for name, _ in reversed(columns):
            op.drop_column(table, name)
