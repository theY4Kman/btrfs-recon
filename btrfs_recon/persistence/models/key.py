from __future__ import annotations

import sqlalchemy.orm as orm
import sqlalchemy as sa
from sqlalchemy.orm import declarative_mixin, declared_attr

from btrfs_recon.structure import KeyType
from . import fields
from .base import BaseStruct

__all__ = [
    'Key',
    'Keyed',
]


class Key(BaseStruct):
    objectid = sa.Column(fields.uint8, nullable=False)
    ty = sa.Column(sa.Enum(KeyType), nullable=False)
    offset = sa.Column(fields.uint8, nullable=False)

    struct_type = sa.Column(sa.String)
    struct_id = sa.Column(sa.Integer)
    struct = fields.generic_relationship(struct_type, struct_id)

    __table_args__ = (
        # Enforce a one-to-one rel between a key and the struct it's attached to
        sa.UniqueConstraint(struct_type, struct_id, name='key_struct_ref_uniq'),

        # Lookup indices
        sa.Index('key_lookup_struct', struct_type, struct_id),
        sa.Index('key_lookup_ty', ty),
        sa.Index('key_lookup_objectid', objectid),
        sa.Index('key_lookup_offset', offset),
    )


@declarative_mixin
class Keyed:
    key_id: declared_attr[int] = declared_attr(lambda cls: sa.Column(sa.ForeignKey(Key.id), nullable=False))
    key: declared_attr[Key] = declared_attr(lambda cls: orm.relationship(Key, lazy='joined'))
