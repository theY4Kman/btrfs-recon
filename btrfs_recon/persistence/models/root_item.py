from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.orm as orm
import sqlalchemy.dialects.postgresql as pg

from btrfs_recon import structure
from btrfs_recon.persistence import fields
from .base import BaseLeafItemData

if TYPE_CHECKING:
    from btrfs_recon.persistence.models import InodeItem


__all__ = [
    'RootItem',
]


class RootItem(BaseLeafItemData):
    inode_id = sa.Column(sa.ForeignKey('inode_item.id'), nullable=False)
    inode: orm.Mapped['InodeItem'] = orm.relationship(
        'InodeItem', foreign_keys=[inode_id], lazy='joined', innerjoin=True,
    )

    generation = sa.Column(fields.uint8, nullable=False,
                           doc='nfs style generation number')
    root_dirid = sa.Column(fields.uint8, nullable=False,
                           doc='For file trees, the objectid of the root directory in this tree '
                               '(always 256). Otherwise, 0.')
    last_snapshot = sa.Column(fields.uint8, nullable=False, doc='The last transid of the transaction that created a snapshot of this root.')
    flags = sa.Column(fields.uint8, nullable=False)
    refs = sa.Column(fields.uint4, nullable=False, doc='Originally indicated a reference count. In modern usage, it is only 0 or 1.')
    drop_progress_id = sa.Column(sa.ForeignKey('key.id'), doc='Contains key of last dropped item during subvolume removal or relocation. Zeroed otherwise.')
    drop_progress = orm.relationship('Key')
    drop_level = sa.Column(fields.uint8, nullable=False, doc='The tree level of the node described in drop_progress.')
    level = sa.Column(fields.uint8, nullable=False, doc='The height of the tree rooted at bytenr.')

    # The following fields depend on the subvol_uuids+subvol_times features
    generation_v2 = sa.Column(
        fields.uint8,
        doc='If equal to generation, indicates validity of the following fields. '
            'If the root is modified using an older kernel, this field and generation '
            'will become out of sync. This is normal and recoverable.',
    )
    uuid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, doc="This subvolume's UUID.")
    parent_uuid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, doc="The parent's UUID (for use with send/receive).")
    received_uuid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, doc="The received UUID (for used with send/receive).")
    ctransid = sa.Column(fields.uint8, doc='The transid of the last transaction that modified this tree, with some exceptions (like the internal caches or relocation).')
    otransid = sa.Column(fields.uint8, doc='The transid of the transaction that created this tree.')
    stransid = sa.Column(fields.uint8, doc='The transid for the transaction that sent this subvolume. Nonzero for received subvolume.')
    rtransid = sa.Column(fields.uint8, doc='The transid for the transaction that received this subvolume. Nonzero for received subvolume.')
    atime = sa.Column(sa.DateTime, doc='Timestamp for atransid')
    ctime = sa.Column(sa.DateTime, doc='Timestamp for ctransid')
    mtime = sa.Column(sa.DateTime, doc='Timestamp for mtransid')
    otime = sa.Column(sa.DateTime, doc='Timestamp for otransid')

    # Individual boolean columns for each flag value
    for _flag in structure.RootItemFlag:
        locals()[f'has_{_flag.name}_flag'] = sa.Column(
            sa.Computed(flags.op('&')(_flag.value) != 0), type_=sa.Boolean
        )
    del _flag
