"""Add RootItem model

Revision ID: 9c3931e75ff4
Revises: 0808385e46be
Create Date: 2022-03-25 20:33:27.325836-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9c3931e75ff4'
down_revision = '0808385e46be'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('root_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('_version', sa.Integer(), server_default='0', nullable=True),
        sa.Column('inode_id', sa.Integer(), nullable=False),
        sa.Column('generation', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('root_dirid', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('last_snapshot', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('flags', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('refs', btrfs_recon.persistence.fields.uint4(), nullable=False),
        sa.Column('drop_progress_id', sa.Integer(), nullable=True),
        sa.Column('drop_level', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('level', btrfs_recon.persistence.fields.uint8(), nullable=False),
        sa.Column('generation_v2', btrfs_recon.persistence.fields.uint8(), nullable=True),
        sa.Column('uuid', postgresql.UUID(), nullable=True),
        sa.Column('parent_uuid', postgresql.UUID(), nullable=True),
        sa.Column('received_uuid', postgresql.UUID(), nullable=True),
        sa.Column('ctransid', btrfs_recon.persistence.fields.uint8(), nullable=True),
        sa.Column('otransid', btrfs_recon.persistence.fields.uint8(), nullable=True),
        sa.Column('stransid', btrfs_recon.persistence.fields.uint8(), nullable=True),
        sa.Column('rtransid', btrfs_recon.persistence.fields.uint8(), nullable=True),
        sa.Column('atime', sa.DateTime(), nullable=True),
        sa.Column('ctime', sa.DateTime(), nullable=True),
        sa.Column('mtime', sa.DateTime(), nullable=True),
        sa.Column('otime', sa.DateTime(), nullable=True),
        sa.Column('has_SUBVOL_RDONLY_flag', sa.Boolean(), sa.Computed('(flags & CAST(1 AS uint8)) != CAST(0 AS uint8)', ), nullable=True),
        sa.Column('leaf_item_id', sa.Integer(), nullable=False),
        sa.Column('address_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['address_id'], ['address.id'], ),
        sa.ForeignKeyConstraint(['drop_progress_id'], ['key.id'], ),
        sa.ForeignKeyConstraint(['inode_id'], ['inode_item.id'], ),
        sa.ForeignKeyConstraint(['leaf_item_id'], ['leaf_item.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column('inode_item', sa.Column('root_item_id', sa.Integer(), nullable=True))
    op.alter_column('inode_item', 'leaf_item_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.create_foreign_key(None, 'inode_item', 'root_item', ['root_item_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    op.alter_column('inode_item', 'leaf_item_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('inode_item', 'root_item_id')
    op.drop_table('root_item')
