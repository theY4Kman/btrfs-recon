from __future__ import annotations

import uuid

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.orm as orm

from btrfs_recon import structure
from .base import BaseStruct
from .. import fields


class ChunkItem(BaseStruct):
    length = sa.Column(fields.uint8, nullable=False)
    owner = sa.Column(fields.uint8, nullable=False)
    stripe_len = sa.Column(fields.uint8, nullable=False)
    ty = sa.Column(fields.uint8, nullable=False)
    io_align = sa.Column(fields.uint4, nullable=False)
    io_width = sa.Column(fields.uint4, nullable=False)
    sector_size = sa.Column(fields.uint4, nullable=False)
    num_stripes = sa.Column(fields.uint2, nullable=False)
    sub_stripes = sa.Column(fields.uint2, nullable=False)

    stripes: orm.Mapped[Stripe] = orm.relationship(
        'Stripe', back_populates='chunk_item', lazy='joined'
    )

    # Individual boolean columns for each flag value
    for _flag in structure.BlockGroupFlag:
        locals()[f'has_{_flag.name}_flag'] = sa.Column(
            sa.Computed(ty.op('&')(_flag.value) != 0), type_=sa.Boolean
        )
    del _flag


class Stripe(BaseStruct):
    chunk_item_id: orm.Mapped[int] = sa.Column(sa.ForeignKey(ChunkItem.id, ondelete='CASCADE'), nullable=False)
    chunk_item: orm.Mapped[ChunkItem] = orm.relationship(ChunkItem, back_populates='stripes')

    devid = sa.Column(fields.uint8, nullable=False)
    offset = sa.Column(fields.uint8, nullable=False)
    dev_uuid: orm.Mapped[uuid.UUID] = sa.Column(pg.UUID, nullable=False)
