import uuid
from typing import Collection

import asyncclick as click
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon import structure
from btrfs_recon.parsing import find_nodes, parse_at
from btrfs_recon.persistence import Filesystem, models
from .base import db, pass_session
from ..types import HEX_DEC_INT


@db.group()
def fs():
    """Interact with the filesystem structures stored in the database"""


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


@fs.command(name='scan')
@click.option('-l', '--label', help='The unique label for the filesystem')
@click.option('-d', '--devid', type=int, multiple=True,
              help='Limit scan to device with specified devid')
@click.option('-a', '--alignment', type=int, default=0x10_000)
@click.option('-s', '--start', type=HEX_DEC_INT, default=None)
@click.option('--reverse/--forward', type=bool, default=True)
@pass_session
async def scan_fs(
    session: AsyncSession,
    label: str,
    alignment: int,
    start: int,
    reverse: bool,
    devid: Collection[int],
):
    """Scan a filesystem for aligned records"""
    q = sa.select(models.Filesystem).filter_by(label=label)
    fs: Filesystem = (await session.execute(q)).scalar_one()

    for device in fs.devices:
        # TODO: fix uint sqla type, so it actually returns an int :|
        if devid and int(device.devid) not in devid:
            continue

        with device.open(read=True) as fp:
            log, headers = find_nodes(
                fp,
                fsid=fs.fsid,
                alignment=alignment,
                start_loc=start,
                reversed=reverse,
            )
            for loc, header in headers:
                tree_node = parse_at(fp, loc, structure.TreeNode)

                try:
                    instance = tree_node.to_model(context={'device': device})
                except ValueError:
                    continue
                else:
                    session.add(instance)
                    await session.commit()
                    log(f'Saved: {instance.__class__.__name__} {instance.id}')

                    # Don't hold onto inserted rows, polluting session and leaking memory
                    session.expunge_all()

        print()
        print()

    await session.commit()
