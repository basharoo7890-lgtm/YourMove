"""Initial schema baseline

Revision ID: 001
Revises:
Create Date: 2026-04-09

This migration represents the existing schema created by Base.metadata.create_all().
It serves as the baseline for all future migrations.
"""
from typing import Sequence, Union

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema is already created by Base.metadata.create_all() in lifespan.
    # This migration exists as the Alembic baseline so future migrations
    # can be applied incrementally.
    #
    # For new deployments: run `alembic upgrade head` after the first server start,
    # or stamp the DB: `alembic stamp 001`
    pass


def downgrade() -> None:
    pass
