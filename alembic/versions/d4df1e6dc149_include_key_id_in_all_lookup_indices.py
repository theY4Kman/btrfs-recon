"""Include key.id in all lookup indices

Revision ID: d4df1e6dc149
Revises: 9c3931e75ff4
Create Date: 2022-03-26 15:16:45.905080-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields


# revision identifiers, used by Alembic.
revision = 'd4df1e6dc149'
down_revision = '9c3931e75ff4'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('key_lookup_objectid', table_name='key')
    op.drop_index('key_lookup_offset', table_name='key')
    op.drop_index('key_lookup_struct', table_name='key')
    op.drop_index('key_lookup_ty', table_name='key')
    op.create_index('key_lookup_objectid', 'key', ['objectid'], unique=False, postgresql_include=['id'])
    op.create_index('key_lookup_offset', 'key', ['offset'], unique=False, postgresql_include=['id'])
    op.create_index('key_lookup_struct', 'key', ['struct_type', 'struct_id'], unique=False, postgresql_include=['id'])
    op.create_index('key_lookup_ty', 'key', ['ty'], unique=False, postgresql_include=['id'])


def downgrade():
    op.drop_index('key_lookup_objectid', table_name='key')
    op.drop_index('key_lookup_offset', table_name='key')
    op.drop_index('key_lookup_struct', table_name='key')
    op.drop_index('key_lookup_ty', table_name='key')
    op.create_index('key_lookup_ty', 'key', ['ty'], unique=False)
    op.create_index('key_lookup_struct', 'key', ['struct_type', 'struct_id'], unique=False)
    op.create_index('key_lookup_offset', 'key', ['offset'], unique=False)
    op.create_index('key_lookup_objectid', 'key', ['objectid'], unique=False)
