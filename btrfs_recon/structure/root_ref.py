import construct as cs

from .base import field, Struct

__all__ = ['RootRef']


class RootRef(Struct):
    dirid: int = field(cs.Int64ul, "ID of directory in [tree id] that contains the subtree")
    sequence: int = field(cs.Int64ul, "Sequence (index in tree) (even, starting at 2?)")
    name_len: int = field(cs.Int16ul)
    name: str = field(cs.PaddedString(cs.this.name_len, 'ascii'))
