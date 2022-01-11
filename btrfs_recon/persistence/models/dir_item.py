from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as orm

from btrfs_recon.persistence import fields
from btrfs_recon.structure import DirEntryType
from .base import BaseLeafItemData
from .key import Key

__all__ = ['DirItem']


class DirItem(BaseLeafItemData):
    location_id: orm.Mapped[int] = sa.Column(sa.ForeignKey(Key.id), nullable=False)
    location: orm.Mapped[Key] = orm.relationship(Key, lazy='joined')

    transid = sa.Column(fields.uint8, nullable=False)
    data_len = sa.Column(fields.uint2, nullable=False)
    name_len = sa.Column(fields.uint2, nullable=False)
    ty = sa.Column(sa.Enum(DirEntryType), nullable=False)
    name = sa.Column(sa.String, nullable=False)
