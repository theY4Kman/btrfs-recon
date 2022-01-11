from typing import Any

from marshmallow import post_load, pre_load
from marshmallow_sqlalchemy import auto_field

from btrfs_recon import structure
from btrfs_recon.persistence import models

from . import fields
from .base import StructSchema

__all__ = [
    'TreeNodeSchema',
    'KeyPtrSchema',
    'LeafItemSchema',
]


class TreeNodeSchema(StructSchema):
    class Meta:
        model = models.TreeNode
        struct_class = structure.TreeNode
        exclude = ('is_leaf',)

    leaf_items = fields.Nested('LeafItemSchema', many=True)
    key_ptrs = fields.Nested('KeyPtrSchema', many=True)

    @pre_load
    def before_load(self, data, **kwargs):
        data.update(data['header'])

        items_key = 'leaf_items' if data['header']['level'] == 0 else 'key_ptrs'
        data[items_key] = data['items']
        return data


class KeyPtrSchema(StructSchema):
    class Meta:
        model = models.KeyPtr
        struct_class = structure.KeyPtr

    parent = fields.ParentInstanceField()
    key = fields.Nested('KeySchema')


class LeafItemSchema(StructSchema):
    class Meta:
        model = models.LeafItem
        struct_class = structure.LeafItem
        exclude = ('struct_id', 'struct_type')

    parent = fields.ParentInstanceField()
    key = fields.Nested('KeySchema')
    struct = fields.Method(deserialize='load_struct', data_key='data')

    def load_struct(self, data: dict[str, Any]) -> models.BaseStruct | None:
        from btrfs_recon.persistence.serializers import registry

        key_type = self.processed_data['key']['ty']
        if entry := registry.find_by_key_type(key_type):
            field = fields.Nested(entry.schema)
            field._bind_to_schema('struct', self)
            return field._deserialize(data, None, None)

        return None
