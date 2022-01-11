from __future__ import annotations

import sqlalchemy as sa

from btrfs_recon import structure
from btrfs_recon.persistence import fields
from .base import BaseLeafItemData

__all__ = [
    'InodeItem',
    'InodeRef',
]


class InodeItem(BaseLeafItemData):
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

    atime = sa.Column(sa.DateTime, nullable=False)
    ctime = sa.Column(sa.DateTime, nullable=False)
    mtime = sa.Column(sa.DateTime, nullable=False)
    otime = sa.Column(sa.DateTime, nullable=False)

    # Individual boolean columns for each flag value
    for _flag in structure.InodeItemFlag:
        locals()[f'has_{_flag.name}_flag'] = sa.Column(
            sa.Computed(flags.op('&')(_flag.value) != 0), type_=sa.Boolean
        )
    del _flag


class InodeRef(BaseLeafItemData):
    index = sa.Column(fields.uint8, nullable=False)
    name = sa.Column(sa.String, nullable=False)
