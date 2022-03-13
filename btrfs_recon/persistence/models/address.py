from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm as orm

from .. import fields
from .base import BaseModel

if TYPE_CHECKING:
    from .physical import Device

__all__ = ['Address']


class Address(BaseModel):
    """Base model for all nodes found on a physical device"""

    device_id = sa.Column(sa.Integer, sa.ForeignKey('device.id'), nullable=False)
    phys = sa.Column(fields.uint8, nullable=False)
    phys_size = sa.Column(fields.uint8, nullable=False)
    bytenr = sa.Column(fields.uint8)

    struct_type = sa.Column(sa.String)
    struct_id = sa.Column(sa.Integer)
    struct = fields.generic_relationship(struct_type, struct_id)

    device: orm.Mapped[Device] = orm.relationship('Device')

    # TODO
    # filesystem = orm.relationship('Filesystem')

    __table_args__ = (
        sa.UniqueConstraint(
            device_id, phys, phys_size,
            name='uniq_physically_addressed',
        ),
        sa.CheckConstraint(
            (struct_type.is_(None) & struct_id.is_(None))
            | (~struct_type.is_(None) & ~struct_type.is_(None)),
            name='address_enforce_struct_ref_completeness',
        ),
        sa.UniqueConstraint(
            struct_type, struct_id,
            name='address_uniq_struct_ref',
        ),
    )
