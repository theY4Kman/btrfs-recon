from __future__ import annotations

import uuid
from typing import BinaryIO

import sqlalchemy.orm as orm
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from btrfs_recon import structure
from .base import BaseStruct
from .key import Keyed
from .. import fields

__all__ = [
    'TreeNode',
    'KeyPtr',
    'LeafItem',
]


class TreeNode(BaseStruct):
    csum = sa.Column(pg.BYTEA, nullable=False)
    fsid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, nullable=False)
    flags = sa.Column(fields.uint8, nullable=False)
    chunk_tree_uuid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)
    nritems = sa.Column(fields.uint4, nullable=False)
    level = sa.Column(fields.uint1, nullable=False)

    is_leaf: orm.Mapped[bool] = sa.Column(sa.Computed(level == 0), type_=sa.Boolean, nullable=False)

    leaf_items: orm.Mapped[LeafItem] = orm.relationship('LeafItem', back_populates='parent', uselist=True)
    key_ptrs: orm.Mapped[KeyPtr] = orm.relationship('KeyPtr', foreign_keys='KeyPtr.parent_id', back_populates='parent', uselist=True)
    parent_key_ptrs: orm.Mapped[KeyPtr] = orm.relationship('KeyPtr', foreign_keys='KeyPtr.ref_node_id', viewonly=True, uselist=True)

    __table_args__ = (
        # Used to order LeafItems by generation with Index-Only Scans
        sa.Index('treenode_passthru_generation', 'id', generation),
    )


class KeyPtr(Keyed, BaseStruct):
    parent_id: orm.Mapped[int] = sa.Column(sa.ForeignKey(TreeNode.id), nullable=False)
    parent: orm.Mapped[TreeNode] = orm.relationship(TreeNode, foreign_keys=parent_id)

    blockptr = sa.Column(fields.uint8, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)

    ref_node_id: orm.Mapped[int] = sa.Column(sa.ForeignKey(TreeNode.id))
    ref_node: orm.Mapped[TreeNode] = orm.relationship(TreeNode, foreign_keys=ref_node_id)


class LeafItem(Keyed, BaseStruct):
    parent_id: orm.Mapped[int] = sa.Column(sa.ForeignKey(TreeNode.id), nullable=False)
    parent: orm.Mapped[TreeNode] = orm.relationship(TreeNode, lazy='selectin')

    offset = sa.Column(fields.uint4, nullable=False)
    size = sa.Column(fields.uint4, nullable=False)

    struct_type = sa.Column(sa.String)
    struct_id = sa.Column(sa.Integer)
    struct = fields.generic_relationship(struct_type, struct_id)

    __table_args__ = (
        sa.CheckConstraint(
            (struct_type.is_(None) & struct_id.is_(None))
            | (~struct_type.is_(None) & ~struct_type.is_(None)),
            name='leaf_enforce_struct_ref_completeness',
        ),
        sa.UniqueConstraint(
            struct_type, struct_id,
            name='leaf_uniq_struct_ref',
        ),

        # Lookup indices
        sa.Index('leaf_lookup_struct', struct_id, struct_type),
    )

    def parse_disk(self, *, fp: BinaryIO = None, **contextkw) -> structure.Struct:
        address = self.parent.address
        contextkw.setdefault('header', {})
        contextkw['header'].setdefault('phys_end', address.phys + address.phys_size)

        return super().parse_disk(fp=fp, **contextkw)
