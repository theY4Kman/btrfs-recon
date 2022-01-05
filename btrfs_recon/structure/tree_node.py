import construct as cs

from .base import field, Struct
from .header import Header
from .key import KeyPtr
from .leaf_item import LeafItem


class TreeNode(Struct):
    header: Header = field(Header)
    items: list[LeafItem] | list[KeyPtr] = field(
        cs.IfThenElse(
            cs.this.header.level == 0,
            LeafItem[cs.this.header.nritems],
            KeyPtr[cs.this.header.nritems],
        ),
    )
