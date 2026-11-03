"""Add ingested_at write-time column to synthetic tables

Synthetic rows are keyed on simulation time (timestamp_utc). When the producer
restarts at an earlier MET, a previous run's later timestamps keep sorting as
"newest" and the live dashboard looks frozen. ingested_at records when the
consumer last wrote each row, so the API can order by write time instead.

Existing rows get the migration time, so anything written afterwards sorts ahead
of them (ties are broken on timestamp_utc by the API).

Revision ID: d5159fa9708e
Revises: 611662aa06a2
Create Date: 2026-11-03 21:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5159fa9708e'
down_revision: str | Sequence[str] | None = '611662aa06a2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SYNTHETIC_TABLES = (
    'anomaly_events',
    'comms_output',
    'cross_model_state',
    'ml_feature_vectors',
    'power_output',
    'radiation_output',
    'state_snapshot',
    'telemetry_packet',
    'thermal_output',
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in SYNTHETIC_TABLES:
        op.add_column(
            table,
            sa.Column(
                'ingested_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('now()'),
                nullable=False,
            ),
        )
        op.create_index(
            f'idx_{table}_ingested_at', table, [sa.literal_column('ingested_at DESC')]
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in SYNTHETIC_TABLES:
        op.drop_index(f'idx_{table}_ingested_at', table_name=table)
        op.drop_column(table, 'ingested_at')
