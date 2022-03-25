from __future__ import annotations

from io import BytesIO
from typing import Iterable

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy.ext.asyncio import AsyncSession

from btrfs_recon.persistence import fields
from btrfs_recon.structure import CompressionType, EncodingType, EncryptionType, ExtentDataType
from btrfs_recon.types import DevId, PhysicalAddress
from .base import BaseLeafItemData

__all__ = ['FileExtentItem']


class FileExtentItem(BaseLeafItemData):
    generation = sa.Column(fields.uint8, nullable=False)
    ram_bytes = sa.Column(fields.uint8, nullable=False)
    compression = sa.Column(sa.Enum(CompressionType), nullable=False)
    encryption = sa.Column(sa.Enum(EncryptionType), nullable=False)
    other_encoding = sa.Column(sa.Enum(EncodingType), nullable=False)
    type = sa.Column(sa.Enum(ExtentDataType), nullable=False)

    # if type == INLINE
    data = sa.Column(pg.BYTEA)

    # if type == REGULAR
    disk_bytenr = sa.Column(fields.uint8)
    disk_num_bytes = sa.Column(fields.uint8)
    offset = sa.Column(fields.uint8)
    num_bytes = sa.Column(fields.uint8)

    __table_args__ = (
        sa.CheckConstraint(
            ((type != ExtentDataType.INLINE)
             | (
                 data.is_not(None)
                 & disk_bytenr.is_(None)
                 & disk_num_bytes.is_(None)
                 & offset.is_(None)
                 & num_bytes.is_(None)
             )),
            name='file_extent_item_inline_data',
        ),
        sa.CheckConstraint(
            ((type != ExtentDataType.REGULAR)
             | (
                 data.is_(None)
                 & disk_bytenr.is_not(None)
                 & disk_num_bytes.is_not(None)
                 & offset.is_not(None)
                 & num_bytes.is_not(None)
             )),
            name='file_extent_item_data_ref',
        ),
    )

    async def calculate_phys(
        self, session: AsyncSession, *, size: int | None = None
    ) -> Iterable[tuple[DevId, PhysicalAddress, int]]:
        from btrfs_recon.persistence import ChunkTree

        assert self.type == ExtentDataType.REGULAR, \
            f'Can only calculate physical addresses of REGULAR files. Found: {self.type}'

        await ChunkTree.refresh_cache(session)
        return ChunkTree.cache.offsets(
            self.disk_bytenr, size if size is not None else self.disk_num_bytes
        )

    async def read_bytes(self, session: AsyncSession, *, size: int | None = None) -> bytes:
        from btrfs_recon.persistence.models import Device

        if self.type == ExtentDataType.INLINE:
            return self.data

        if self.type != ExtentDataType.REGULAR:
            raise NotImplementedError(f'Cannot read bytes of {self.type} type files')

        phys_locs = await self.calculate_phys(session, size=size)

        # TODO: limit to only devids from same Filesystem
        # TODO: limit to only devids encountered in phys_locs
        devid_map = await Device.devid_map(session)
        devid_fps = {devid: device.open() for devid, device in devid_map.items()}

        try:
            buf = BytesIO()
            for devid, phys, num_bytes in phys_locs:
                fp = devid_fps[devid]
                fp.seek(phys)
                chunk = fp.read(num_bytes)
                buf.write(chunk)

            return buf.getvalue()

        finally:
            for fp in devid_fps.values():
                fp.close()

    async def read_text(
        self, session: AsyncSession, *, size: int | None = None, encoding: str = 'utf8'
    ) -> str:
        data = await self.read_bytes(session, size=size)
        return data.decode(encoding)
