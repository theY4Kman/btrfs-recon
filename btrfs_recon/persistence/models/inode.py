from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import func

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
