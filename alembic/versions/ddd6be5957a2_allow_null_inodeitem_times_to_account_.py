"""Allow null InodeItem times, to account for malformed times

Revision ID: ddd6be5957a2
Revises: f380aa51b36a
Create Date: 2022-03-14 05:56:02.028240-04:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ddd6be5957a2'
down_revision = 'f380aa51b36a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('inode_item', 'atime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('inode_item', 'ctime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('inode_item', 'mtime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('inode_item', 'otime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('inode_item', 'otime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('inode_item', 'mtime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('inode_item', 'ctime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('inode_item', 'atime',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    # ### end Alembic commands ###
