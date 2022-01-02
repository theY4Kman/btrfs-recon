from marshmallow import fields

from btrfs_recon.persistence import ChunkItem, Stripe
from .base import StructSchema

__all__ = [
    'StripeSchema',
    'ChunkItemSchema',
]


class StripeSchema(StructSchema):
    class Meta:
        model = Stripe


class ChunkItemSchema(StructSchema):
    class Meta:
        model = ChunkItem

    stripes = fields.Nested(StripeSchema, many=True)
