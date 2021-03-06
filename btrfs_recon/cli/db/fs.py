import asyncio
import uuid
from pathlib import Path
from typing import AsyncIterable, Collection

import aiomultiprocess
import asyncclick as click
import construct as cs
import sqlalchemy as sa
from aiomultiprocess import Pool
from aiomultiprocess.types import ProxyException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ddl
from tqdm import tqdm
from tui_progress import timed_subtask

import btrfs_recon.db
from btrfs_recon import structure
from btrfs_recon.parsing import FindNodesLogFunc, find_nodes, parse_at
from btrfs_recon.persistence import Filesystem, models, registry
from btrfs_recon.types import DevId, ImagePath, PhysicalAddress

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
    with timed_subtask('Grabbing filesystem'):
        fs = (await session.execute(sa.select(models.Filesystem).filter_by(label=label))).scalar_one()

    encountered_fsids: set[uuid.UUID] = set()
    for device in fs.devices:
        struct_superblocks: list[structure.Superblock] = []
        for pos in (0x10_000, 0x40_000_000, 0x4000000000):
            with timed_subtask(f'Parsing {device} superblock @ {hex(pos)}') as task:
                try:
                    struct_superblock = device.parse_superblock(pos=pos)
                except cs.ConstructError as e:
                    task.print_warn(str(e))
                    task.fail('INVALID')
                    continue

                struct_superblocks.append(struct_superblock)

                superblock = struct_superblock.to_model(context={'device': device}, session=session)
                session.add(superblock)

        primary_superblock = struct_superblocks[0]

        device.update_from_superblock(primary_superblock)
        encountered_fsids.add(primary_superblock.fsid)

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
@click.option('-r/-f', '--reverse/--forward', type=bool, default=False)
@click.option('--parallel/--no-parallel', type=bool, default=True)
@click.option('-w', '--workers', type=int, default=None)
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

        with device.open() as fp:
            log, headers = await find_nodes(
                fp,
                fsid=fs.fsid,
                alignment=alignment,
                start_loc=start,
                end_loc=end,
                reversed=reverse,
                tqdm_kwargs=dict(
                    desc=f'Scanning devid {device.devid}',
                    dynamic_ncols=True,
                    colour='blue',
                ),
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
    failures: list[tuple[ImagePath, DevId, PhysicalAddress, str]] = []

    finished_scanning = asyncio.Event()

    queue_pbar = tqdm(
        position=1,
        unit='node',
        total=0,
        dynamic_ncols=True,
        colour='green',
        desc='Parse found locs',
    )

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
            try:
                result = await pool.apply(_multiprocess_loc, args=args)
            except ProxyException as e:
                tb = e.args[0]
                failures.append(args + (tb,))
                log(f'Failed to process {args}:\n\n' + tb)
            else:
                if result:
                    log(result)

            queue_pbar.update(1)

            # Remove an item from the pending queue, freeing the queue master
            # to retrieve another item
            pending_queue.get_nowait()
            pending_queue.task_done()

        async def queue_master():
            wait_finished_scanning = asyncio.create_task(
                finished_scanning.wait(), name='wait until all locations have been scanned'
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

        if failures:
            print(f'Encountered {len(failures)} failure(s)\n\n')

            for (*args, tb) in failures:
                print(args, '\n', tb, '\n\n')

            print(f'Encountered {len(failures)} failure(s)\n\n')


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
        instance = tree_node.to_model(context={'device': device}, session=session)
    except ValueError:
        return
    else:
        await session.commit()

        phys = instance.address.phys
        return (
            f'Saved: {instance.__class__.__name__} {instance.id} '
            f'@ {hex(phys)} ({phys})'
        )


@fs.command(name='reparse')
@click.option('-l', '--label', help='The unique label for the filesystem')
@click.option('-k', '--key', multiple=True, type=click.Choice(structure.KeyType.__members__),
              help='Key types of leaf items to reparse')
@click.option('-A', '--all', 'all_', is_flag=True, help='Select all key types')
@click.option('--missing/--no-missing', default=True,
              help='Whether to parse leaf items with missing structs')
@click.option('--outdated/--no-outdated', default=True,
              help='Whether to parse leaf items with existing structs from outdated serializers')
# @click.option('--existing/--no-existing', default=False,
#               help='Whether to parse leaf items with existing, up-to-date structs')
@click.option('--parallel/--no-parallel', type=bool, default=True)
@click.option('-w', '--workers', type=int, default=None)
@click.option('--qsize', type=int, default=24)
@pass_session
async def reparse_fs(
    session: AsyncSession,
    label: str,
    key: list[str],
    all_: bool,
    missing: bool,
    outdated: bool,
    # existing: bool,
    parallel: bool,
    workers: int | None,
    qsize: int,
):
    """Reparse existing leaf items from disk images"""
    q = sa.select(models.Filesystem).filter_by(label=label)
    fs: Filesystem = (await session.execute(q)).scalar_one()
    device_ids = [d.id for d in fs.devices]

    if not (key or all_):
        return

    if not (missing or outdated):
        return

    if all_:
        key_types = list(structure.KeyType.__members__.values())
    else:
        key_types = [structure.KeyType(ty) for ty in key]

    q = (
        sa.select(models.LeafItem.id)
        .select_from(models.LeafItem)
        .join(models.Key)
        .join(models.Address)
        .join(models.Device)
        .filter(
            models.Device.id.in_(device_ids),
            models.Key.ty.in_(key_types),
        )
    )

    filters = []

    missing_filter = models.LeafItem.struct_id.is_(None)
    if not missing:
        missing_filter = ~missing_filter
    filters.append(missing_filter)

    key_type_registry_entries = {
        ty: registry.find_by_key_type(ty)
        for ty in key_types
    }
    schema_versions = [
        (sa.cast(ty, models.Key.ty.type), entry.schema.opts.version)
        for ty, entry in key_type_registry_entries.items()
        if entry
    ]
    outdated_values = sa.values(
        sa.column('ty', models.Key.ty.type),
        sa.column('current_version', sa.Integer),
        name='current_versions',
    ).data(schema_versions)

    q = q.join(outdated_values, onclause=models.Key.ty == outdated_values.c.ty, isouter=True)
    outdated_filter = models.LeafItem._version < outdated_values.c.current_version
    if not outdated:
        outdated_filter = ~outdated_filter
    filters.append(outdated_filter)

    q = q.filter(sa.or_(*filters))

    pbar = tqdm(
        unit='struct',
        maxinterval=2,
        dynamic_ncols=True,
    )
    pbar.n = 0

    if parallel:
        # Throw all IDs in a temp table, for simpler querying
        temp_items_table = sa.Table(
            'temp_reparse_items', models.Base.metadata,
            sa.Column('leaf_item_id', sa.Integer, primary_key=True),
            prefixes=['TEMPORARY'],
        )
        await session.execute(ddl.CreateTable(temp_items_table))
        await session.execute(
            sa.insert(temp_items_table)
            .from_select([temp_items_table.c.leaf_item_id], q)
        )

        aiomultiprocess.set_start_method('fork')

        async with Pool(
            processes=workers,
            childconcurrency=1,
            maxtasksperchild=qsize,
        ) as pool:
            queue = asyncio.Queue(maxsize=qsize)
            pending_queue = asyncio.Queue(maxsize=qsize)
            failures: list[tuple[int, str]] = []
            finished_submitting = asyncio.Event()

            async def _process_and_print(leaf_item_id: int):
                if not pool.running:
                    return

                args = (leaf_item_id,)
                try:
                    result = await pool.apply(_multiprocess_leaf_item, args=args)
                except ProxyException as e:
                    tb = e.args[0]
                    failures.append(args + (tb,))
                    pbar.write(f'Failed to process {args}:\n\n' + tb)
                else:
                    if result:
                        pbar.write(result)

                pbar.update(1)

                # Remove an item from the pending queue, freeing the queue master
                # to retrieve another item
                pending_queue.get_nowait()
                pending_queue.task_done()

            async def queue_master():
                wait_finished_submitting = asyncio.create_task(
                    finished_submitting.wait(), name='wait until all leaf items have been submitted'
                )

                while pool.running and (not queue.empty() or not finished_submitting.is_set()):
                    queue_get = asyncio.create_task(queue.get(), name='get leaf item from queue')
                    done, pending = await asyncio.wait(
                        (queue_get, wait_finished_submitting), return_when=asyncio.FIRST_COMPLETED
                    )
                    if finished_submitting.is_set() and queue.empty():
                        break

                    if queue_get in done:
                        leaf_item_id = queue_get.result()
                        await pending_queue.put(leaf_item_id)
                        asyncio.create_task(_process_and_print(leaf_item_id))

                await pending_queue.join()

            processor = asyncio.create_task(queue_master(), name='queue processor')

            async def calculate_total():
                total = (await session.execute(
                    sa.select(sa.func.count())
                    .select_from(temp_items_table)
                )).scalar()
                pbar.total = total

            asyncio.create_task(calculate_total())

            res = await session.execute(sa.select(temp_items_table.c.leaf_item_id))
            for leaf_item_id in res.scalars():
                await queue.put(leaf_item_id)
            finished_submitting.set()

            await processor

            if failures:
                print(f'Encountered {len(failures)} failure(s)\n\n')
                for (leaf_item_id, tb) in failures:
                    print(f'Leaf Item {leaf_item_id}', '\n', tb, '\n\n')
                print(f'Encountered {len(failures)} failure(s)\n\n')

    else:  # not parallel
        q = q.with_only_columns(models.LeafItem)
        pbar.iterable = (await session.execute(q)).scalars()
        for leaf_item in pbar:
            if result := await _process_leaf_item(session, leaf_item):
                pbar.write(result)


async def _multiprocess_leaf_item(leaf_item_id: int) -> str | None:
    async with btrfs_recon.db.Session() as session:
        q = sa.select(models.LeafItem).filter_by(id=leaf_item_id)
        res = await session.execute(q)
        leaf_item: models.LeafItem = res.scalar()

        return await _process_leaf_item(session, leaf_item)


async def _process_leaf_item(session: AsyncSession, leaf_item: models.LeafItem) -> str | None:
    leaf_item.reparse(session=session)
    await session.commit()
    return f'Reparsed {leaf_item}'
