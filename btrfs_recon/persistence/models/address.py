import sqlalchemy as sa
from sqlalchemy import orm as orm
from sqlalchemy_utils import generic_relationship

from .. import fields
from .base import BaseModel

__all__ = ['Address']


class Address(BaseModel):
    """Base model for all nodes found on a physical device"""

    device_id = sa.Column(sa.Integer, sa.ForeignKey('device.id'), nullable=False)
    phys = sa.Column(fields.uint8, nullable=False)
    phys_size = sa.Column(fields.uint8, nullable=False)
    bytenr = sa.Column(fields.uint8)

    struct_type = sa.Column(sa.String, nullable=False)
    struct_id = sa.Column(sa.Integer, nullable=False)
    struct = generic_relationship(struct_type, struct_id)

    device = orm.relationship('Device')

    # TODO
    # filesystem = orm.relationship('Filesystem')

    __table_args__ = (
        sa.UniqueConstraint(device_id, phys, name='uniq_physically_addressed'),
    )
