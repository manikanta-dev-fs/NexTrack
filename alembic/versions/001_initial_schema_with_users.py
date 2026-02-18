"""Initial schema with users and transactions

Revision ID: 001
Revises: 
Create Date: 2026-01-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table first
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    
    # Create transactions table with user_id
    op.create_table(
        'transactions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('payment_method', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for transactions
    op.create_index('ix_transactions_description', 'transactions', ['description'])
    op.create_index('ix_transactions_category', 'transactions', ['category'])
    op.create_index('ix_transactions_status', 'transactions', ['status'])
    op.create_index('ix_transactions_created_at', 'transactions', ['created_at'])
    op.create_index('ix_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('idx_transaction_user_date', 'transactions', ['user_id', 'created_at'])
    op.create_index('idx_transaction_category_date', 'transactions', ['category', 'created_at'])
    op.create_index('idx_transaction_status_date', 'transactions', ['status', 'created_at'])
    
    # Create payment_details table
    op.create_table(
        'payment_details',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('transaction_id', sa.String(36), nullable=False),
        sa.Column('payment_type', sa.String(20), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ondelete='CASCADE')
    )
    op.create_index('ix_payment_details_transaction_id', 'payment_details', ['transaction_id'])


def downgrade() -> None:
    op.drop_table('payment_details')
    op.drop_table('transactions')
    op.drop_table('users')
