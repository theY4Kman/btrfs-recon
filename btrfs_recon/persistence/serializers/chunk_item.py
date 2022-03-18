from btrfs_recon import structure
from btrfs_recon.persistence import ChunkItem, Stripe
from . import fields
from .base import StructSchema

__all__ = [
    'StripeSchema',
    'ChunkItemSchema',
]


class StripeSchema(StructSchema):
    class Meta:
        model = Stripe
        struct_class = structure.Stripe


class ChunkItemSchema(StructSchema):
    class Meta:
        model = ChunkItem
        struct_class = structure.ChunkItem
        key_type = structure.KeyType.ChunkItem

    stripes = fields.Nested(StripeSchema, many=True)
