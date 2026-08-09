"""Baseline migration

Revision ID: f8f12c721cd1
Revises: 
Create Date: 2026-08-09 22:45:20.859353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8f12c721cd1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Stocks table
    if 'stocks' not in existing_tables:
        op.create_table('stocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('min_price', sa.Float(), nullable=False),
        sa.Column('max_price', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('stocks', schema=None) as batch_op:
            batch_op.create_index('idx_active_symbol', ['is_active', 'symbol'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_is_active'), ['is_active'], unique=False)
            batch_op.create_index(batch_op.f('ix_stocks_symbol'), ['symbol'], unique=True)

    # 2. Users table
    if 'users' not in existing_tables:
        op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
            batch_op.create_index(batch_op.f('ix_users_id'), ['id'], unique=False)

    # 3. Orders table
    if 'orders' not in existing_tables:
        op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('price', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.DECIMAL(precision=18, scale=2), nullable=False),
        sa.Column('side', sa.Enum('BUY', 'SELL', name='orderside'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'CANCELLED', 'FAILED', name='orderstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.create_index('idx_user_created', ['user_id', 'created_at'], unique=False)
            batch_op.create_index('idx_user_status', ['user_id', 'status'], unique=False)
            batch_op.create_index(batch_op.f('ix_orders_created_at'), ['created_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_orders_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_orders_status'), ['status'], unique=False)
            batch_op.create_index(batch_op.f('ix_orders_symbol'), ['symbol'], unique=False)
            batch_op.create_index(batch_op.f('ix_orders_user_id'), ['user_id'], unique=False)

    # 4. Positions table
    if 'positions' not in existing_tables:
        op.create_table('positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('average_price', sa.DECIMAL(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'symbol', name='uq_user_symbol')
        )
        with op.batch_alter_table('positions', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_positions_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_positions_symbol'), ['symbol'], unique=False)
            batch_op.create_index(batch_op.f('ix_positions_user_id'), ['user_id'], unique=False)

    # 5. Wallets table
    if 'wallets' not in existing_tables:
        op.create_table('wallets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.DECIMAL(precision=18, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('wallets', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_wallets_id'), ['id'], unique=False)
            batch_op.create_index(batch_op.f('ix_wallets_user_id'), ['user_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if 'wallets' in existing_tables:
        with op.batch_alter_table('wallets', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_wallets_user_id'))
            batch_op.drop_index(batch_op.f('ix_wallets_id'))
        op.drop_table('wallets')

    if 'positions' in existing_tables:
        with op.batch_alter_table('positions', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_positions_user_id'))
            batch_op.drop_index(batch_op.f('ix_positions_symbol'))
            batch_op.drop_index(batch_op.f('ix_positions_id'))
        op.drop_table('positions')

    if 'orders' in existing_tables:
        with op.batch_alter_table('orders', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_orders_user_id'))
            batch_op.drop_index(batch_op.f('ix_orders_symbol'))
            batch_op.drop_index(batch_op.f('ix_orders_status'))
            batch_op.drop_index(batch_op.f('ix_orders_id'))
            batch_op.drop_index(batch_op.f('ix_orders_created_at'))
            batch_op.drop_index('idx_user_status')
            batch_op.drop_index('idx_user_created')
        op.drop_table('orders')

    if 'users' in existing_tables:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_users_id'))
            batch_op.drop_index(batch_op.f('ix_users_email'))
        op.drop_table('users')

    if 'stocks' in existing_tables:
        with op.batch_alter_table('stocks', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_stocks_symbol'))
            batch_op.drop_index(batch_op.f('ix_stocks_is_active'))
            batch_op.drop_index(batch_op.f('ix_stocks_id'))
            batch_op.drop_index('idx_active_symbol')
        op.drop_table('stocks')

    # Drop Postgres ENUM types
    if conn.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS orderside CASCADE")
        op.execute("DROP TYPE IF EXISTS orderstatus CASCADE")
