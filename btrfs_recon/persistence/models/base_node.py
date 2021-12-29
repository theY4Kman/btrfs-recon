from typing import Any, Type, TYPE_CHECKING, TypeVar

import construct as cs
import inflection
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import declared_attr

from btrfs_recon.persistence import fields

from .base import BaseModel

if TYPE_CHECKING:
    from .physical import Device

__all__ = ['Address', 'BaseNode']


class Address(BaseModel):
    """Base model for all nodes found on a physical device"""
    address_id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)

    device_id = sa.Column(sa.Integer, sa.ForeignKey('device.id'), nullable=False)
    phys = sa.Column(fields.uint8, nullable=False)
    size = sa.Column(fields.uint8, nullable=False)
    bytenr = sa.Column(fields.uint8)

    # Used to support joined-table inheritance
    node_type = sa.Column(sa.String, nullable=False)

    device = orm.relationship('Device')
    filesystem = orm.relationship('Filesystem')

    __table_args__ = (
        sa.UniqueConstraint(device_id, phys, name='uniq_physically_addressed'),
    )
    __mapper_args__ = {
        'polymorphic_on': node_type,
        'polymorphic_identity': 'base_node'
    }


NodeT = TypeVar('NodeT', bound='BaseNode')


class BaseNode(Address):
    __abstract__ = True

    id = sa.Column(primary_key=True, autoincrement=True)

    @declared_attr
    def __mapper_args__(cls):
        return {
            'polymorphic_identity': inflection.underscore(cls.__name__),
        }

    @declared_attr
    def base_node_id(cls):
        return sa.Column(sa.ForeignKey(Address.address_id), nullable=False)

    @classmethod
    def parse_struct(cls, device: 'Device', value: cs.Container, /) -> dict[str, Any]:
        """Extract any DB fields from a construct Container"""
        return {
            'phys': value.LOC,
        }

    @classmethod
    def from_struct(cls: Type[NodeT], device: 'Device', value: cs.Container, /, **extra_attrs) -> NodeT:
        """Transform a construct Container to its DB model representation"""
        attrs = {
            **cls.parse_struct(device, value),
            **extra_attrs,
        }
        return cls(**attrs)
