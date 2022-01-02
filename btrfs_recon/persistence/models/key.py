import sqlalchemy.orm as orm
import sqlalchemy as sa
from sqlalchemy.orm import declarative_mixin, declared_attr
from sqlalchemy_utils import generic_relationship

from . import fields
from .base import BaseStruct

__all__ = [
    'Key',
    'Keyed',
]


class Key(BaseStruct):
    id = sa.Column(primary_key=True, autoincrement=True)

    objectid = sa.Column(fields.uint8, nullable=False)
    ty = sa.Column(fields.uint2, nullable=False)
    offset = sa.Column(fields.uint8, nullable=False)

    struct_type = sa.Column(sa.String)
    struct_id = sa.Column(sa.Integer)
    struct = generic_relationship(struct_type, struct_id)

    __table_args__ = (
        # Enforce a one-to-one rel between a key and the struct it's attached to
        sa.UniqueConstraint(struct_type, struct_id, name='key_struct_ref_uniq'),
    )


@declarative_mixin
class Keyed:
    key_id = declared_attr(lambda cls: sa.Column(sa.ForeignKey(Key.id), nullable=False))
    key = declared_attr(lambda cls: orm.relationship(Key, lazy='joined'))
