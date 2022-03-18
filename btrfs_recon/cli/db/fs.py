import asyncio
import uuid
from typing import AsyncIterable, Collection

import asyncclick as click
import sqlalchemy as sa
from aiomultiprocess import Pool
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

import btrfs_recon.db
from btrfs_recon import structure
from btrfs_recon.parsing import FindNodesLogFunc, find_nodes, parse_at
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
@click.option('-e', '--end', type=HEX_DEC_INT, default=None)
@click.option('--reverse/--forward', type=bool, default=True)
@click.option('--parallel/--no-parallel', type=bool, default=True)
@click.option('--workers', type=int, default=None)
@click.option('--qsize', type=int, default=24)
@click.option('--scan-qsize', type=int, default=1_000)
@pass_session
async def scan_fs(
    session: AsyncSession,
    label: str,
    alignment: int,
    start: int | None,
    end: int | None,
    reverse: bool,
    devid: Collection[int],
    parallel: bool,
    workers: int | None,
    qsize: int,
    scan_qsize: int,
):
    """Scan a filesystem for aligned records"""
    q = sa.select(models.Filesystem).filter_by(label=label)
    fs: Filesystem = (await session.execute(q)).scalar_one()

    for device in fs.devices:
        if devid and device.devid not in devid:
            continue

        with device.open(read=True) as fp:
            log, headers = await find_nodes(
                fp,
                fsid=fs.fsid,
                alignment=alignment,
                start_loc=start,
                end_loc=end,
                reversed=reverse,
            )

            if parallel:
                await _scan_parallel(
                    device, log, headers,
                    workers=workers,
                    qsize=qsize,
                    scan_qsize=scan_qsize,
                )
            else:
                async for loc, header in headers:
                    tree_node = parse_at(fp, loc, structure.TreeNode)

                    if msg := await _process_loc(session, tree_node, device):
                        log(msg)
                        # Don't hold onto inserted rows, polluting session and leaking memory
                        session.expunge_all()

        print()
        print()

    await session.commit()


async def _scan_parallel(
    device: models.Device,
    log: FindNodesLogFunc,
    headers: AsyncIterable[tuple[int, structure.Header]],
    workers: int | None = None,
    qsize: int = 24,
    scan_qsize: int = 1_000,
):
    queue = asyncio.Queue(maxsize=scan_qsize)
    pending_queue = asyncio.Queue(maxsize=qsize)

    finished_scanning = asyncio.Event()

    queue_pbar = tqdm(position=1, unit='node', total=0)

    async with Pool(
        processes=workers,
        childconcurrency=1,
        maxtasksperchild=qsize,
    ) as pool:
        device_id = device.id

        async def _process_and_print(loc: int):
            if not pool.running:
                return

            args = (device.path, device_id, loc)
            if msg := await pool.apply(_multiprocess_loc, args=args):
                log(msg)
            queue_pbar.n += 1

            # Remove an item from the pending queue, freeing the queue master
            # to retrieve another item
            pending_queue.get_nowait()
            pending_queue.task_done()

        async def queue_master():
            wait_finished_scanning = asyncio.create_task(
                finished_scanning.wait(), name='wait until all aligned locations have been scanned'
            )

            while pool.running and (not queue.empty() or not finished_scanning.is_set()):
                queue_get = asyncio.create_task(queue.get(), name='get next valid loc from queue')
                done, pending = await asyncio.wait(
                    (queue_get, wait_finished_scanning), return_when=asyncio.FIRST_COMPLETED
                )
                if finished_scanning.is_set() and queue.empty():
                    break

                if queue_get in done:
                    loc = queue_get.result()
                    await pending_queue.put(loc)
                    asyncio.create_task(_process_and_print(loc))

            await pending_queue.join()

        processor = asyncio.create_task(queue_master(), name='queue processor')

        async for loc, header in headers:
            await queue.put(loc)
            queue_pbar.total += 1
        finished_scanning.set()

        await processor


async def _multiprocess_loc(image_path: str, device_id: int, loc: int):
    async with btrfs_recon.db.Session() as session:
        with open(image_path, 'rb') as fp:
            tree_node = parse_at(fp, loc, structure.TreeNode)

        try:
            return await _process_loc(session, tree_node=tree_node, device=device_id)
        finally:
            # Don't hold onto inserted rows, polluting session and leaking memory
            session.expunge_all()


async def _process_loc(
    session: AsyncSession, tree_node: structure.TreeNode, device: int | models.Device
):
    try:
        instance = tree_node.to_model(context={'device': device})
    except ValueError:
        return
    else:
        session.add(instance)
        await session.commit()

        phys = instance.address.phys
        return (
            f'Saved: {instance.__class__.__name__} {instance.id} '
            f'@ {hex(phys)} ({phys})'
        )
