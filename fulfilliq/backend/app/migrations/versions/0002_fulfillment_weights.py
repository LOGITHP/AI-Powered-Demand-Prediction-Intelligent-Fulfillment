"""Persist configurable score weights in simulation settings."""

from alembic import op
from sqlalchemy import Column, Text, inspect

revision = "0002_fulfillment_weights"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

COLUMN = "fulfillment_weights"
DEFAULT = '{"availability":40,"inventory":20,"distance":20,"future_availability":10,"delivery_sla":10}'


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("simulation_state")}
    if COLUMN not in columns:
        op.add_column("simulation_state", Column(COLUMN, Text(), nullable=False, server_default=DEFAULT))


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("simulation_state")}
    if COLUMN in columns:
        op.drop_column("simulation_state", COLUMN)
