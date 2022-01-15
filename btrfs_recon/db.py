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

engine = create_async_engine('postgresql+psycopg://btrfs_recon:btrfs_recon@127.0.0.1:5436/btrfs_recon')
Session = orm.sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

sync_engine = sa.create_engine('postgresql+psycopg://btrfs_recon:btrfs_recon@127.0.0.1:5436/btrfs_recon')
SyncSession = orm.sessionmaker(sync_engine, expire_on_commit=False)


def _init_uint_types():
    with sync_engine.raw_connection() as dbapi_conn:
        from btrfs_recon.persistence.fields import uint
        uint.init_dbapi_types(dbapi_conn)
