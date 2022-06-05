import binascii
import typing
import uuid
from datetime import datetime

import construct as cs
import construct_typed as cst

from btrfs_recon.constants import BTRFS_UUID_SIZE, BTRFS_FSID_SIZE

from .base import Struct, field

__all__ = [
    'UUID',
    'FSID',
    'HexDecInt',
    'Timespec',
]


class UUIDAdapter(cs.Adapter):
    def _decode(self, obj, context, path) -> uuid.UUID:
        return uuid.UUID(bytes=bytes(obj))

    def _encode(self, obj: uuid.UUID, context, path) -> bytes:
        return obj.bytes_le if getattr(context, 'swapped', False) else obj.bytes


UUID = UUIDAdapter(cs.Int8ul[BTRFS_UUID_SIZE])
FSID = UUIDAdapter(cs.Int8ul[BTRFS_FSID_SIZE])


class HexAndDecDisplayedInteger(int):
    _num_bytes: int
    _uppercase: bool

    def __new__(cls, *args, num_bytes: int, uppercase: bool = False):
        obj = super().__new__(cls, *args)
        obj._num_bytes = num_bytes
        obj._uppercase = uppercase
        return obj

    def __str__(self) -> str:
        return f'0x{self:0{self._num_bytes}{"X" if self._uppercase else "x"}} ({self:d})'

    def __copy__(self) -> 'HexAndDecDisplayedInteger':
        return HexAndDecDisplayedInteger(self, num_bytes=self._num_bytes, uppercase=self._uppercase)

    def __deepcopy__(self, memo: dict) -> 'HexAndDecDisplayedInteger':
        copy = self.__copy__()
        memo[id(self)] = copy
        return copy


class HexDecInt(cs.Hex):
    def _decode(self, obj, context, path):
        if isinstance(obj, int):
            return HexAndDecDisplayedInteger(obj, num_bytes=self.subcon._sizeof(context, path))
        return obj


class TimespecStruct(Struct):
    sec: int = field(cs.Int64ul)
    nsec: int = field(cs.Int32ul)


class TimespecDatetimeAdapter(cs.Adapter):
    def _decode(self, obj, context, path):
        try:
            return datetime.utcfromtimestamp(obj.sec).replace(microsecond=int(obj.nsec / 1000))
        except (ValueError, OverflowError, OSError):
            return None


Timespec = TimespecDatetimeAdapter(TimespecStruct.as_struct())


class EnumBase(cst.EnumBase):
    @classmethod
    def _missing_(cls, value: typing.Any) -> typing.Optional[cst.EnumBase]:
        if isinstance(value, str):
            return cls.__members__[value]
        return super()._missing_(value)


class Checksum(cs.Checksum):
    """Checksum field allowing dynamic building of checksums and invalid checksums to be parsed"""

    def __init__(self, checksumfield, hashfunc, bytesfunc, allow_invalid: bool = True):
        super().__init__(checksumfield, hashfunc, bytesfunc)
        self.allow_invalid = allow_invalid

    def _parse(self, stream, context, path):
        hash1 = self.checksumfield._parsereport(stream, context, path)
        if not self.allow_invalid:
            hash2 = self.hashfunc(self.bytesfunc(context))
            if hash1 != hash2:
                hash1_repr = hash1 if not isinstance(hash1, bytes) else binascii.hexlify(hash1)
                hash2_repr = hash2 if not isinstance(hash2, bytes) else binascii.hexlify(hash2)
                raise cs.ChecksumError(
                    f'wrong checksum, read {hash1_repr!r}, computed {hash2_repr!r}',
                    path=path,
                )
        return hash1


class Reparse(cs.Rebuild):
    """Field which defers to subcon for parsing _and_ building"""

    def __init__(self, subcon):
        super().__init__(subcon, None)

    def _build(self, obj, stream, context, path):
        return self.subcon._parsereport(stream, context, path)
