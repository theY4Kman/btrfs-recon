from __future__ import annotations

from typing import Awaitable, Iterable

import sqlalchemy.dialects.postgresql as pg
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon import structure
from btrfs_recon.types import DevId, PhysicalAddress
from btrfs_recon.util.properties import classproperty
from btrfs_recon.util.chunk_cache import ChunkTreeCache
from . import fields
from ._views import MaterializedView

__all__ = ['ChunkTree']


class ChunkTree(MaterializedView):
    id = sa.Column(sa.Integer, sa.ForeignKey('chunk_item.id'), primary_key=True)
    generation = sa.Column(fields.uint8)
    log_start = sa.Column(fields.uint8)
    log_end = sa.Column(fields.uint8)
    length = sa.Column(fields.uint8)
    stripe_len = sa.Column(fields.uint8)
    num_stripes = sa.Column(fields.uint2)
    stripes: orm.Mapped[tuple[tuple[DevId, PhysicalAddress], ...]] = sa.Column(
        sa.ARRAY(fields.uint8, dimensions=2, as_tuple=True)
    )

    # Individual boolean columns for each flag value
    locals().update({
        f'has_{_flag.name}_flag': sa.Column(sa.Boolean)
        for _flag in structure.BlockGroupFlag
    })

    @orm.declared_attr
    def __query__(cls) -> sa.sql.Select:
        from . import Address, ChunkItem, TreeNode, Key, Stripe, LeafItem

        log_start = Key.offset.label('log_start')
        log_end = (Key.offset + ChunkItem.length).label('log_end')
        stripes = sa.func.array_agg(
            aggregate_order_by(
                pg.array([Stripe.devid, Stripe.offset]),
                Address.phys.asc(),
            )
        )

        flag_fields = [
            col
            for col in sa.inspect(ChunkItem).attrs
            if col.key.startswith('has_') and col.key.endswith('_flag')
        ]

        return (
            sa.select(
                ChunkItem.id,
                TreeNode.generation,
                log_start,
                log_end,
                ChunkItem.length,
                ChunkItem.stripe_len,
                ChunkItem.num_stripes,
                stripes.label('stripes'),
                *flag_fields,
            )
            .select_from(LeafItem)
            .join(TreeNode)
            .join(Key)
            .join(ChunkItem, onclause=(
                (LeafItem.struct_type == ChunkItem.__name__) & (ChunkItem.id == LeafItem.struct_id)
            ))
            .join(Stripe)
            .join(Address, onclause=Address.id == Stripe.address_id)
            .group_by(
                ChunkItem.id,
                TreeNode.generation,
                log_start,
                log_end,
                ChunkItem.stripe_len,
                ChunkItem.num_stripes,
            )
            .order_by(log_start)
        )

    _cache: ChunkTreeCache | None = None

    @classproperty
    def cache(cls) -> ChunkTreeCache:
        if cls._cache is None:
            raise RuntimeError(
                'ChunkTreeCache not yet loaded. Please call refresh_cache to load it.'
            )
        return cls._cache

    @classmethod
    def refresh_cache(
        cls, session: AsyncSession | orm.Session, *, force: bool = False
    ) -> Awaitable[None] | None:
        if isinstance(session, AsyncSession):
            return cls._refresh_cache_async(session, force=force)

        if cls._cache and not force:
            return

        res = session.execute(sa.select(ChunkTree))
        chunks = res.scalars()
        cls.fill_cache(chunks)

    @classmethod
    async def _refresh_cache_async(cls, session: AsyncSession, *, force: bool = False) -> None:
        if cls._cache and not force:
            return

        res = await session.execute(sa.select(ChunkTree))
        chunks = res.scalars()
        cls.fill_cache(chunks)

    @classmethod
    def fill_cache(cls, chunks: Iterable[ChunkTree]) -> None:
        cls._cache = ChunkTreeCache()
        for chunk in chunks:
            cls._cache.insert(
                chunk.log_start,
                chunk.log_end,
                chunk.stripe_len,
                chunk.stripes
            )
