"""Add lookup indices for Key, Address, and LeafItem

Revision ID: 070b2ea975f0
Revises: a596ebed6540
Create Date: 2022-03-20 22:38:20.745657-04:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '070b2ea975f0'
down_revision = 'a596ebed6540'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('address_lookup_logical', 'address', ['bytenr'], unique=False)
    op.create_index('address_lookup_struct', 'address', ['struct_id', 'struct_type'], unique=False)
    op.create_index('inoderef_ext', 'inode_ref', ['ext'], unique=False, postgresql_include=['name'])
    op.create_index('inoderef_name_like', 'inode_ref', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('key_lookup_objectid', 'key', ['objectid'], unique=False)
    op.create_index('key_lookup_struct', 'key', ['struct_type', 'struct_id'], unique=False)
    op.create_index('key_lookup_ty', 'key', ['ty'], unique=False)
    op.create_index('leaf_lookup_struct', 'leaf_item', ['struct_id', 'struct_type'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('leaf_lookup_struct', table_name='leaf_item')
    op.drop_index('key_lookup_ty', table_name='key')
    op.drop_index('key_lookup_struct', table_name='key')
    op.drop_index('key_lookup_objectid', table_name='key')
    op.drop_index('inoderef_name_like', table_name='inode_ref')
    op.drop_index('inoderef_ext', table_name='inode_ref')
    op.drop_index('address_lookup_struct', table_name='address')
    op.drop_index('address_lookup_logical', table_name='address')
    # ### end Alembic commands ###
