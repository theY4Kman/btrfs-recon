import uuid
from typing import BinaryIO

import asyncclick as click
import asyncclick.decorators
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

import btrfs_recon.db
from btrfs_recon import structure
from btrfs_recon.parsing import parse_at
from btrfs_recon.persistence import models


@click.group()
def cli():
    pass


@cli.command()
@click.argument('devices', nargs=-1, type=click.File('rb'), metavar='<device/image>')
def list_superblocks(devices: tuple[BinaryIO]):
    for device in devices:
        click.echo(f'# {device.name}')

        superblock = parse_at(device, 0x10000, structure.Superblock)
        click.echo(str(superblock))

        click.echo('\n')


@cli.group()
@click.pass_context
async def db(ctx: click.Context):
    ctx.meta['session'] = await ctx.enter_async_context(btrfs_recon.db.Session())
    ctx.meta['sync_session'] = ctx.enter_context(btrfs_recon.db.SyncSession())


pass_session = asyncclick.decorators.pass_meta_key('session')
pass_sync_session = asyncclick.decorators.pass_meta_key('sync_session')


@db.command()
@pass_session
async def init(session: AsyncSession):
    conn = await session.connection()
    await conn.run_sync(models.BaseModel.metadata.create_all)
    await session.commit()


@db.group()
def fs():
    pass


async def _print_fs(fs: models.Filesystem):
    print(f'[{fs.id:>3}] fsid={fs.fsid} label={fs.label or "":<20}')
    for device in fs.devices:
        print(f' → [{device.id:>3}] devid={device.devid} label={device.label or "":<10}: {device.path}')


@fs.command(name='list')
@pass_session
async def list_fs(session: AsyncSession):
    """List all filesystems in the DB"""
    result = await session.execute(sa.select(models.Filesystem))
    rows = result.unique().scalars(0)
    for fs in rows:
        await _print_fs(fs)
        print()


@fs.command(name='create')
@click.option('-l', '--label', help='A unique label for the filesystem')
@click.argument('devices', nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False), metavar='<device/image>')
@pass_session
async def create_fs(session: AsyncSession, label: str, devices: list[str]):
    """Create a new filesystem from device/image paths"""
    fs = models.Filesystem.from_devices(*devices, label=label)
    session.add(fs)
    await session.commit()

    await _print_fs(fs)


@fs.command(name='sync')
@click.option('-l', '--label', help='The unique label for the filesystem')
@pass_session
async def sync_fs(session: AsyncSession, label: str):
    """Sync Superblock and Device records for a filesystem"""
    fs = (await session.execute(sa.select(models.Filesystem).filter_by(label=label))).scalar_one()

    encountered_fsids: set[uuid.UUID] = set()
    for device in fs.devices:
        struct_superblock: structure.Superblock = device.parse_superblock()
        device.update_from_superblock(struct_superblock)
        encountered_fsids.add(struct_superblock.fsid)

        superblock = struct_superblock.to_model(context={'device': device})
        session.add(superblock)

    if len(encountered_fsids) > 1:
        click.echo(
            f'Encountered {len(encountered_fsids)} unique FSIDs among the superblocks; '
            f'there should only be one!\n'
            f' - '
            + '\n - '.join(map(str, encountered_fsids))
        )
        raise click.exceptions.Exit(code=2)

    fs.fsid = next(iter(encountered_fsids))
    await session.commit()
