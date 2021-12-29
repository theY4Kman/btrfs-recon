import construct as cs

from .base import field, Struct
from .header import Header
from .item import Item
from .key import KeyPtr


class TreeNode(Struct):
    header: Header = field(Header)
    items: list[Item] | list[KeyPtr] = field(
        cs.IfThenElse(
            cs.this.header.level == 0,
            Item[cs.this.header.nritems],
            KeyPtr[cs.this.header.nritems],
        ),
    )
