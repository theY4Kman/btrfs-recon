from typing import BinaryIO

import click

from btrfs_recon.parsing import parse_at
from btrfs_recon.structure import Superblock


@click.group()
def cli():
    pass


@cli.command()
@click.argument('devices', nargs=-1, type=click.File('rb'), metavar='<device/image>')
def list_superblocks(devices: tuple[BinaryIO]):
    for device in devices:
        click.echo(f'# {device.name}')

        superblock = parse_at(device, 0x10000, Superblock)
        click.echo(str(superblock))

        click.echo('\n')
