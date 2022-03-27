from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon import structure
from btrfs_recon.persistence import fields
from .base import BaseLeafItemData

if TYPE_CHECKING:
    from btrfs_recon.persistence.models import FileExtentItem


__all__ = [
    'InodeItem',
    'InodeRef',
]


class InodeItem(BaseLeafItemData):
    # NOTE: because InodeItems may be present in RootItems, their leaf_item may be null
    leaf_item_id = sa.Column(sa.ForeignKey('leaf_item.id'), nullable=True)
    leaf_item = orm.relationship('LeafItem', lazy='joined')

    root_item_id = sa.Column(sa.ForeignKey('root_item.id'), nullable=True)
    root_item = orm.relationship('RootItem', foreign_keys=[root_item_id], post_update=True)

    generation = sa.Column(fields.uint8, nullable=False, doc='nfs style generation number')
    transid = sa.Column(fields.uint8, nullable=False, doc='transid that last touched this inode')
    size = sa.Column(fields.uint8, nullable=False)
    nbytes = sa.Column(fields.uint8, nullable=False)
    block_group = sa.Column(fields.uint8, nullable=False)
    nlink = sa.Column(fields.uint4, nullable=False)
    uid = sa.Column(fields.uint4, nullable=False)
    gid = sa.Column(fields.uint4, nullable=False)
    mode = sa.Column(fields.uint4, nullable=False)
    rdev = sa.Column(fields.uint8, nullable=False)
    flags = sa.Column(fields.uint8, nullable=False)

    sequence = sa.Column(fields.uint8, nullable=False, doc='modification sequence number for NFS')

    atime = sa.Column(sa.DateTime)
    ctime = sa.Column(sa.DateTime)
    mtime = sa.Column(sa.DateTime)
    otime = sa.Column(sa.DateTime)

    # Individual boolean columns for each flag value
    for _flag in structure.InodeItemFlag:
        locals()[f'has_{_flag.name}_flag'] = sa.Column(
            sa.Computed(flags.op('&')(_flag.value) != 0), type_=sa.Boolean
        )
    del _flag

    async def get_file_extent_item(self, session: AsyncSession) -> FileExtentItem | None:
        from btrfs_recon.persistence.models import FileExtentItem, Key, LeafItem
        q = (
            sa.select(FileExtentItem)
            .join(LeafItem)
            .join(Key)
            .filter_by(objectid=self.objectid)
            .order_by(FileExtentItem.generation.desc())
        )
        res = await session.execute(q.limit(1))
        return res.scalar_one_or_none()

    async def read_bytes(self, session: AsyncSession) -> bytes | None:
        if fei := await self.get_file_extent_item(session):
            return await fei.read_bytes(session, size=self.nbytes)

    async def read_text(self, session: AsyncSession, *, encoding: str = 'utf8') -> str | None:
        if fei := await self.get_file_extent_item(session):
            return await fei.read_text(session, size=self.nbytes, encoding=encoding)


class InodeRef(BaseLeafItemData):
    index = sa.Column(fields.uint8, nullable=False)
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
        sa.Index('inoderef_name_like', name,
                 postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
        sa.Index('inoderef_ext', ext, postgresql_include=['name']),
    )
