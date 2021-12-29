from contextlib import nullcontext
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

import sqlalchemy as sa

from btrfs_recon import structure
from btrfs_recon.parsing import parse_at
from btrfs_recon.persistence import fields

from .base import BaseModel

if TYPE_CHECKING:
    from .superblock import Superblock

__all__ = ['Device']


class Device(BaseModel):
    """A device/image file containing a btrfs filesystem"""

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    path = sa.Column(sa.String, nullable=False, unique=True)
    label = sa.Column(sa.String)

    devid = sa.Column(fields.uint8)

    def __str__(self) -> str:
        if self.label:
            return f'{self.label} ({self.path})'
        else:
            return self.path

    def open(self, mode='rb', buffering=-1) -> BinaryIO:
        return Path(self.path).open(mode=mode, buffering=buffering)

    def parse_superblock(self, fp: BinaryIO | None = None, pos: int = 0x10_000) -> 'Superblock':
        from .superblock import Superblock

        with (self.open() if fp is None else nullcontext(fp)) as fp:
            sb = parse_at(fp, pos, structure.Superblock)

        return Superblock.from_struct(self, sb)

    def update_from_superblock(self, superblock: 'Superblock'):
        self.devid = superblock.dev_item.devid
