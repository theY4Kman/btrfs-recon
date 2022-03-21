"""Reenable FileExtentItem CHECK constraints

Revision ID: 301555ab7694
Revises: 070b2ea975f0
Create Date: 2022-03-21 12:33:55.748121-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields


# revision identifiers, used by Alembic.
revision = '301555ab7694'
down_revision = '070b2ea975f0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_check_constraint(
        'file_extent_item_inline_data',
        'file_extent_item',
        #language=postgresql
        '''
        type <> 'INLINE' OR (
            data IS NOT NULL
            AND disk_bytenr IS NULL
            AND disk_num_bytes IS NULL
            AND "offset" IS NULL
            AND num_bytes IS NULL
        )
        ''',
    )
    op.create_check_constraint(
        'file_extent_item_data_ref',
        'file_extent_item',
        #language=postgresql
        '''
        type <> 'REGULAR' OR (
            data IS NULL
            AND disk_bytenr IS NOT NULL
            AND disk_num_bytes IS NOT NULL
            AND "offset" IS NOT NULL
            AND num_bytes IS NOT NULL
        )
        ''',
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('file_extent_item_data_ref', 'file_extent_item', 'check')
    op.drop_constraint('file_extent_item_inline_data', 'file_extent_item', 'check')
    # ### end Alembic commands ###
