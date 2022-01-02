import sqlalchemy.orm as orm
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy_utils import generic_relationship

from .base import BaseStruct
from .key import Keyed
from .. import fields

__all__ = ['TreeNode']


class TreeNode(BaseStruct):
    csum = sa.Column(pg.BYTEA, nullable=False)
    fsid = sa.Column(pg.UUID, nullable=False)
    flags = sa.Column(fields.uint8, nullable=False)
    chunk_tree_uuid = sa.Column(pg.UUID, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)
    nritems = sa.Column(fields.uint4, nullable=False)
    level = sa.Column(fields.uint1, nullable=False)

    is_leaf = sa.Column(sa.Computed(level == 0), nullable=False)

    leaf_items = orm.relationship('LeafItem', back_populates='parent')
    key_ptrs = orm.relationship('KeyPtr', foreign_keys='KeyPtr.parent_id', back_populates='parent')
    parent_key_ptrs = orm.relationship('KeyPtr', foreign_keys='KeyPtr.ref_node_id', viewonly=True)


class KeyPtr(Keyed, BaseStruct):
    parent_id = sa.Column(sa.ForeignKey(TreeNode.id), nullable=False)
    parent = orm.relationship(TreeNode, foreign_keys=parent_id)

    blockptr = sa.Column(fields.uint8, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)

    ref_node_id = sa.Column(sa.ForeignKey(TreeNode.id))
    ref_node = orm.relationship(TreeNode, foreign_keys=ref_node_id)


class LeafItem(Keyed, BaseStruct):
    parent_id = sa.Column(sa.ForeignKey(TreeNode.id), nullable=False)
    parent = orm.relationship(TreeNode)

    offset = sa.Column(fields.uint4, nullable=False)
    size = sa.Column(fields.uint4, nullable=False)

    struct_type = sa.Column(sa.String, nullable=False)
    struct_id = sa.Column(sa.Integer, nullable=False)
    struct = generic_relationship(struct_type, struct_id)
