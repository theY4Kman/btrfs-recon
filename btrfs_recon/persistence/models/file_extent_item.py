from __future__ import annotations

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from btrfs_recon.persistence import fields
from btrfs_recon.structure import CompressionType, EncodingType, EncryptionType, ExtentDataType
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
