"""Add TreeNode.generation pass-thru index

Revision ID: 0808385e46be
Revises: def933329547
Create Date: 2022-03-25 15:31:25.629121-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields


# revision identifiers, used by Alembic.
revision = '0808385e46be'
down_revision = 'def933329547'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('treenode_passthru_generation', 'tree_node', ['id', 'generation'], unique=False)


def downgrade():
    op.drop_index('treenode_passthru_generation', table_name='tree_node')
