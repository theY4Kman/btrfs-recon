from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon import structure
from btrfs_recon.parsing import parse_at
from btrfs_recon.persistence import fields
from btrfs_recon.types import DevId
from .base import BaseModel

if TYPE_CHECKING:
    from _typeshed import OpenBinaryMode

__all__ = ['Device']


class Device(BaseModel):
    """A device/image file containing a btrfs filesystem"""

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    path: orm.Mapped[str] = sa.Column(sa.String, nullable=False, unique=True)
    label = sa.Column(sa.String)

    devid = sa.Column(fields.uint8)

    @classmethod
    async def devid_map(cls, session: AsyncSession) -> dict[DevId, Device]:
        q = sa.select(cls)
        res = await session.execute(q)
        devices = res.scalars()
        return {d.devid: d for d in devices}

    def __str__(self) -> str:
        if self.label:
            return f'{self.label} ({self.path})'
        else:
            return self.path

    def open(self, read: bool = True, write: bool = False, buffering=-1) -> BinaryIO:
        mode: OpenBinaryMode

        match read, write:
            case True, False:
                mode = 'rb'
            case True, True:
                mode = 'r+b'
            case False, True:
                mode = 'wb'
            case _:
                raise ValueError('One of "read" or "write" must be True')

        return Path(self.path).open(mode=mode, buffering=buffering)

    def parse_superblock(
        self, fp: BinaryIO | None = None, pos: int = 0x10_000
    ) -> structure.Superblock:
        with (self.open() if fp is None else nullcontext(fp)) as fp:
            return parse_at(fp, pos, structure.Superblock)

    def update_from_superblock(self, superblock: structure.Superblock):
        self.devid = superblock.dev_item.devid
