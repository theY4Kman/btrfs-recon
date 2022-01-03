from marshmallow import fields

from btrfs_recon import structure
from btrfs_recon.persistence import ChunkItem, Stripe
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

    stripes = fields.Nested(StripeSchema, many=True)
