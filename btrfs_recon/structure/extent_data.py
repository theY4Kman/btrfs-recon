import construct as cs
from construct_typed import EnumBase, TEnum

from .base import field, Struct

__all__ = [
    'CompressionType',
    'EncryptionType',
    'EncodingType',
    'ExtentDataType',
    'ExtentData',
]


class CompressionType(EnumBase):
    none = 0
    zlib = 1
    LZO = 2


class EncryptionType(EnumBase):
    none = 0


class EncodingType(EnumBase):
    none = 0


class ExtentDataType(EnumBase):
    inline = 0
    regular = 1
    prealloc = 2


class ExtentDataRef(Struct):
    bytenr: int = field(cs.Int64ul,
                        'logical address of extent. If this is zero, the extent is sparse and consists of all zeroes.')
    size: int = field(cs.Int64ul, 'size of extent')
    offset: int = field(cs.Int64ul, 'offset within the extent')
    data_len: int = field(cs.Int64ul, 'logical number of bytes in file')


# ref: https://btrfs.wiki.kernel.org/index.php/On-disk_Format#EXTENT_DATA_.286c.29
class ExtentData(Struct):
    # XXX: are these names canonical?
    generation: int = field(cs.Int64ul)
    size: int = field(cs.Int64ul)
    compression: CompressionType = field(TEnum(cs.Int8ul, CompressionType))
    encryption: EncryptionType = field(TEnum(cs.Int8ul, EncryptionType))
    encoding: EncodingType = field(TEnum(cs.Int16ul, EncodingType))
    type: ExtentDataType = field(TEnum(cs.Int8ul, ExtentDataType))
    data: bytes | None = field(
        cs.If(cs.this.type == ExtentDataType.inline, cs.HexDump(cs.Bytes(cs.this.size))))
    ref: ExtentDataRef | None = field(
        cs.If(cs.this.type != ExtentDataType.inline, ExtentDataRef.as_struct()))
