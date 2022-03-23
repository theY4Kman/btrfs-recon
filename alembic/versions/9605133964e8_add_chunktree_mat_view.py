"""Add ChunkTree mat view

Revision ID: 9605133964e8
Revises: 301555ab7694
Create Date: 2022-03-23 03:33:09.505291-04:00

"""
from alembic import op
import sqlalchemy as sa
import btrfs_recon.persistence.fields


# revision identifiers, used by Alembic.
revision = '9605133964e8'
down_revision = '301555ab7694'
branch_labels = None
depends_on = None


def upgrade():
    # language=postgresql
    op.execute('''
        CREATE MATERIALIZED VIEW chunk_tree AS
        SELECT
            chunk_item.id,
            tree_node.generation,
            key."offset" AS log_start,
            key."offset" + chunk_item.length AS log_end,
            chunk_item.stripe_len AS stripe_len,
            chunk_item.num_stripes AS num_stripes,
            array_agg(ARRAY[stripe.devid, stripe."offset"] ORDER BY address.phys) AS stripes
        FROM leaf_item
        JOIN tree_node ON leaf_item.parent_id = tree_node.id
        JOIN key on leaf_item.key_id = key.id
        JOIN chunk_item ON leaf_item.struct_type = 'ChunkItem' AND leaf_item.struct_id = chunk_item.id
        JOIN stripe on chunk_item.id = stripe.chunk_item_id
        JOIN address on address.id = stripe.address_id
        GROUP BY chunk_item.id, generation, log_start, log_end, stripe_len, num_stripes
        ORDER BY log_start;
    ''')


def downgrade():
    # language=postgresql
    op.execute('DROP MATERIALIZED VIEW IF EXISTS chunk_tree;')
