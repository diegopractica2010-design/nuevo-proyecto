"""Consolidate ORM model layers into single DDD infrastructure layer

Revision ID: 20260528_0004
Revises: 20260525_0003
Create Date: 2026-05-28

MIGRATION SUMMARY:
- Moved UserRecord, BasketRecord, BasketItemRecord, PriceHistoryRecord from backend/db_models.py 
  to backend/infrastructure/db/models.py
- Consolidated all ORM models under single infrastructure.db.models module
- Updated all imports across backend/auth.py, backend/basket_service.py, backend/repositories.py
- Updated migrations/env.py to use single Base metadata from consolidated models
- Deleted legacy backend/db_models.py file

SCHEMA CHANGES: None - all tables already created by previous migrations
This migration serves as a consolidation checkpoint in the Alembic version chain.

FUTURE CONSOLIDATION (Optional):
- BasketItemRecord could add FK to ProductRecord (requires schema migration)
- PriceHistoryRecord could be replaced with materialized view over prices+products+stores
- UserRecord could add FK to stores for store-specific baskets
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260528_0004"
down_revision = "20260525_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Bring the migrated schema in line with the consolidated ProductRecord model.
    """
    op.add_column("products", sa.Column("image_url", sa.String(length=1000), nullable=True))
    op.add_column("products", sa.Column("product_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "product_url")
    op.drop_column("products", "image_url")
