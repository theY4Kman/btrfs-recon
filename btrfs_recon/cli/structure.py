from typing import BinaryIO

import asyncclick as click

from btrfs_recon import structure
from btrfs_recon.parsing import parse_at
from .base import cli


@cli.command()
@click.argument('devices', nargs=-1, type=click.File('rb'), metavar='<device/image>')
def list_superblocks(devices: tuple[BinaryIO]):
    """Print the first superblock (at 0x10000) on a device/image"""
    for device in devices:
        click.echo(f'# {device.name}')

        superblock = parse_at(device, 0x10000, structure.Superblock)
        click.echo(str(superblock))

        click.echo('\n')
