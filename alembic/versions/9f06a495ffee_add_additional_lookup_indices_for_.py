"""Add additional lookup indices for DirItem and Key.offset

Revision ID: 9f06a495ffee
Revises: 9605133964e8
Create Date: 2022-03-23 16:22:32.851313-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields


# revision identifiers, used by Alembic.
revision = '9f06a495ffee'
down_revision = '9605133964e8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dir_item', sa.Column('ext', sa.String(), sa.Computed("CASE WHEN (strpos(name, '.') = 0) THEN NULL ELSE split_part(name, '.', -1) END", persisted=True), nullable=True))
    op.create_index('diritem_ext', 'dir_item', ['ext'], unique=False, postgresql_include=['name'])
    op.create_index('diritem_name_like', 'dir_item', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('key_lookup_offset', 'key', ['offset'], unique=False)


def downgrade():
    op.drop_index('key_lookup_offset', table_name='key')
    op.drop_index('diritem_name_like', table_name='dir_item', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_index('diritem_ext', table_name='dir_item', postgresql_include=['name'])
    op.drop_column('dir_item', 'ext')
