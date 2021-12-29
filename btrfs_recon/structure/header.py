from uuid import UUID

import construct as cs

from btrfs_recon.constants import BTRFS_CSUM_SIZE

from . import fields
from .base import field, Struct

__all__ = ['Header']


class Header(Struct):
    csum: bytes = field(cs.Hex(cs.Bytes(BTRFS_CSUM_SIZE)))
    fsid: UUID = field(fields.FSID)
    bytenr: int = field(cs.Int64ul)
    flags: int = field(cs.Int64ul)
    chunk_tree_uuid: UUID = field(fields.UUID)
    generation: int = field(cs.Int64ul)
    owner: int = field(cs.Int64ul)
    nritems: int = field(cs.Int32ul)
    level: int = field(cs.Int8ul)
