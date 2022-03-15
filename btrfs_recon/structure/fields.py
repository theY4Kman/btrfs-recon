import uuid
from datetime import datetime

import construct as cs

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
        return obj.bytes if context.swapped else obj.bytes_le


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
