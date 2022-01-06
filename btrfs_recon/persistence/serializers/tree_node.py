from marshmallow import fields, pre_load

from btrfs_recon import structure
from btrfs_recon.persistence import models
from .base import StructSchema

__all__ = [
    'TreeNodeSchema',
    'KeyPtrSchema',
]


class TreeNodeSchema(StructSchema):
    class Meta:
        model = models.TreeNode
        struct_class = structure.TreeNode
        exclude = ('is_leaf',)

    leaf_items = fields.Nested('LeafItemSchema', many=True)
    key_ptrs = fields.Nested('LeafItemSchema', many=True)

    @pre_load
    def before_load(self, data, **kwargs):
        items_key = 'leaf_items' if data['level'] == 0 else 'key_ptrs'
        data[items_key] = data['items']


class KeyPtrSchema(StructSchema):
    class Meta:
        model = models.KeyPtr
        struct_class = structure.KeyPtr


class LeafItemSchema(StructSchema):
    class Meta:
        model = models.LeafItem
        struct_class = structure.LeafItem
        exclude = ('struct_id', 'struct_type', 'struct')

    struct = fields.Method(deserialize='load_struct', data_key='data')

    def load_struct(self, struct: structure.Struct) -> models.BaseStruct | None:
        from . import registry
        if entry := registry.find_by_struct(struct.__class__):
            return entry.schema().load(struct)
        return None
