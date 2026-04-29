"""domain catalog schema

Revision ID: 20260429_0002
Revises: 20260428_0001
Create Date: 2026-04-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260429_0002"
down_revision = "20260428_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_key", sa.String(length=500), nullable=False),
        sa.Column("canonical_name", sa.String(length=300), nullable=False),
        sa.Column("brand", sa.String(length=160), nullable=True),
        sa.Column("quantity_value", sa.Float(), nullable=True),
        sa.Column("quantity_unit", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_key"),
    )
    op.create_index(op.f("ix_products_brand"), "products", ["brand"], unique=False)
    op.create_index(op.f("ix_products_canonical_name"), "products", ["canonical_name"], unique=False)

    op.create_table(
        "prices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "store_id",
            "observed_at",
            name="uq_prices_product_store_observed",
        ),
    )
    op.create_index(op.f("ix_prices_observed_at"), "prices", ["observed_at"], unique=False)
    op.create_index(
        "ix_prices_product_store_observed",
        "prices",
        ["product_id", "store_id", "observed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prices_product_store_observed", table_name="prices")
    op.drop_index(op.f("ix_prices_observed_at"), table_name="prices")
    op.drop_table("prices")
    op.drop_index(op.f("ix_products_canonical_name"), table_name="products")
    op.drop_index(op.f("ix_products_brand"), table_name="products")
    op.drop_table("products")
    op.drop_table("stores")

