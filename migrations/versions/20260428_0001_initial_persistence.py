"""initial persistence schema

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260428_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "baskets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("user_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_baskets_user_id"), "baskets", ["user_id"], unique=False)

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.String(length=255), nullable=False),
        sa.Column("store", sa.String(length=40), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_history_date"), "price_history", ["date"], unique=False)
    op.create_index(op.f("ix_price_history_product_id"), "price_history", ["product_id"], unique=False)
    op.create_index(op.f("ix_price_history_store"), "price_history", ["store"], unique=False)

    op.create_table(
        "basket_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("basket_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("store", sa.String(length=40), nullable=False),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["basket_id"], ["baskets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_basket_items_basket_id"), "basket_items", ["basket_id"], unique=False)
    op.create_index(op.f("ix_basket_items_product_id"), "basket_items", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_basket_items_product_id"), table_name="basket_items")
    op.drop_index(op.f("ix_basket_items_basket_id"), table_name="basket_items")
    op.drop_table("basket_items")
    op.drop_index(op.f("ix_price_history_store"), table_name="price_history")
    op.drop_index(op.f("ix_price_history_product_id"), table_name="price_history")
    op.drop_index(op.f("ix_price_history_date"), table_name="price_history")
    op.drop_table("price_history")
    op.drop_index(op.f("ix_baskets_user_id"), table_name="baskets")
    op.drop_table("baskets")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
