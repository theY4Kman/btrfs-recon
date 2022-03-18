"""Add unique/check constraints for LeafItem structs

Revision ID: eece6c9f11c6
Revises: 275168ff8072
Create Date: 2022-03-13 23:27:56.035366-04:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eece6c9f11c6'
down_revision = '275168ff8072'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('leaf_item', 'struct_type',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('leaf_item', 'struct_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.create_unique_constraint('leaf_uniq_struct_ref', 'leaf_item', ['struct_type', 'struct_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('leaf_uniq_struct_ref', 'leaf_item', type_='unique')
    op.alter_column('leaf_item', 'struct_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('leaf_item', 'struct_type',
               existing_type=sa.VARCHAR(),
               nullable=False)
    # ### end Alembic commands ###