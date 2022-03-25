from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy import func

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

    ext = sa.Column(
        sa.Computed(
            sa.case(
                (func.strpos(name, '.') == 0, None),
                else_=func.split_part(name, '.', -1),
            ),
            persisted=True,
        ),
        type_=sa.String,
    )

    __table_args__ = (
        sa.Index('diritem_name_like', name,
                 postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
        sa.Index('diritem_ext', ext, postgresql_include=['name']),
    )
