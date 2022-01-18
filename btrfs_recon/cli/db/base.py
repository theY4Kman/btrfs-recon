import asyncclick as click
import asyncclick.decorators

import btrfs_recon.db
from ..base import cli

__all__ = [
    'db',
    'pass_session',
    'pass_sync_session',
]


@cli.group()
@click.pass_context
async def db(ctx: click.Context):
    """Interact with the structures stored in the database"""
    ctx.meta['session'] = await ctx.enter_async_context(btrfs_recon.db.Session())
    ctx.meta['sync_session'] = ctx.enter_context(btrfs_recon.db.SyncSession())


pass_session = asyncclick.decorators.pass_meta_key('session')
pass_sync_session = asyncclick.decorators.pass_meta_key('sync_session')
