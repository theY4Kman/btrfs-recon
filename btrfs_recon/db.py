from contextlib import closing

import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Load our models
import btrfs_recon.persistence  # type: ignore

__all__ = [
    'engine',
    'Session',
    'sync_engine',
    'SyncSession',
]

engine = create_async_engine('postgresql+psycopg://btrfs_recon:btrfs_recon@127.0.0.1:5436/btrfs_recon',
                             pool_size=20, max_overflow=0)
Session = orm.sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = sa.create_engine('postgresql+psycopg://btrfs_recon:btrfs_recon@127.0.0.1:5436/btrfs_recon')
SyncSession = orm.sessionmaker(sync_engine, expire_on_commit=False)


from btrfs_recon.persistence.fields import uint  # noqa
with closing(sync_engine.raw_connection()) as conn:
    uint.init_uint_types(conn, engine.dialect, sync_engine.dialect)
