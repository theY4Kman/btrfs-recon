import construct as cs
from construct_typed import TEnum

from . import fields
from .base import field, Struct

__all__ = [
    'CompressionType',
    'EncryptionType',
    'EncodingType',
    'ExtentDataType',
    'FileExtentItem',
]


class CompressionType(fields.EnumBase):
    NONE = 0
    ZLIB = 1
    LZO = 2


class EncryptionType(fields.EnumBase):
    NONE = 0


class EncodingType(fields.EnumBase):
    NONE = 0


class ExtentDataType(fields.EnumBase):
    INLINE = 0
    REGULAR = 1
    PREALLOC = 2


class ExtentDataRef(Struct):
    disk_bytenr: int = field(cs.Int64ul, 'logical address of extent. If this is zero, the extent is sparse and consists of all zeroes.')
    disk_num_bytes: int = field(cs.Int64ul, 'size of extent')
    offset: int = field(cs.Int64ul, 'offset within the extent')
    num_bytes: int = field(cs.Int64ul, 'logical number of bytes in file')


# ref: https://btrfs.wiki.kernel.org/index.php/Data_Structures#btrfs_file_extent_item
class FileExtentItem(Struct):
    # XXX: are these names canonical?
    generation: int = field(cs.Int64ul)
    ram_bytes: int = field(cs.Int64ul)
    compression: CompressionType = field(TEnum(cs.Int8ul, CompressionType))
    encryption: EncryptionType = field(TEnum(cs.Int8ul, EncryptionType))
    other_encoding: EncodingType = field(TEnum(cs.Int16ul, EncodingType))
    type: ExtentDataType = field(TEnum(cs.Int8ul, ExtentDataType))
    data: bytes | None = field(
        cs.If(cs.this.type == ExtentDataType.INLINE,
              cs.HexDump(cs.Bytes(cs.this.ram_bytes)))
    )
    ref: ExtentDataRef | None = field(
        cs.If(cs.this.type != ExtentDataType.INLINE,
              ExtentDataRef.as_struct())
    )
