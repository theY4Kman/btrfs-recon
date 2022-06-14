import alembic.command
import alembic.config
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon import settings
from btrfs_recon.persistence import models
from .base import db, pass_session


@db.command()
@pass_session
async def init(session: AsyncSession):
    """Initialize all tables in the database"""
    conn = await session.connection()
    await conn.run_sync(models.BaseModel.metadata.create_all)
    await session.commit()

    alembic_cfg = alembic.config.Config(str(settings.ALEMBIC_CFG_PATH))
    alembic.command.stamp(alembic_cfg, 'head')
