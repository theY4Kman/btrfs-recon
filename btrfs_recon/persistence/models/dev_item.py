import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from .base import BaseStruct
from .. import fields

__all__ = ['DevItem']


class DevItem(BaseStruct):
    devid = sa.Column(fields.uint8, nullable=False)
    total_bytes = sa.Column(fields.uint8, nullable=False)
    bytes_used = sa.Column(fields.uint8, nullable=False)
    io_align = sa.Column(fields.uint4, nullable=False)
    io_width = sa.Column(fields.uint4, nullable=False)
    sector_size = sa.Column(fields.uint4, nullable=False)
    type = sa.Column(fields.uint8, nullable=False)
    generation = sa.Column(fields.uint8, nullable=False)
    start_offset = sa.Column(fields.uint8, nullable=False)
    dev_group = sa.Column(fields.uint4, nullable=False)
    seek_speed = sa.Column(fields.uint1, nullable=False)
    bandwidth = sa.Column(fields.uint1, nullable=False)
    uuid = sa.Column(pg.UUID, nullable=False)
    fsid = sa.Column(pg.UUID, nullable=False)
