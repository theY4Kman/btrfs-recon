import dataclasses
import typing

import marshmallow
from marshmallow import fields, post_load, pre_load
from marshmallow_sqlalchemy import auto_field, SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchemaMeta

from btrfs_recon.persistence import Address
from btrfs_recon.structure import Struct

__all__ = [
    'BaseSchema',
    'AddressSchema',
    'StructSchema',
]


class InheritableMetaSchemaMeta(SQLAlchemyAutoSchemaMeta):
    """Allow Meta options to be inherited from parent Schemas

    Currently, no special handling is performed for collection types; the last
    value wins.
    """

    def __new__(mcs, name, bases, attrs):
        if meta := attrs.get('Meta'):
            base_metas = {base.Meta for base in bases if hasattr(base, 'Meta')}
            inheriting_meta = type('Meta', (meta, *base_metas), {})
            attrs['Meta'] = inheriting_meta

        return super().__new__(mcs, name, bases, attrs)


class BaseSchema(SQLAlchemyAutoSchema, metaclass=InheritableMetaSchemaMeta):
    class Meta:
        # Don't bind Schema to a session
        transient = True
        # Produce model instance when calling load()
        load_instance = True
        # Don't yell when load() is passed fields not declared in Schema
        unknown = marshmallow.INCLUDE

    @pre_load
    def _dataclass_to_dict(self, data: dict | Struct, **kwargs) -> dict[str, typing.Any]:
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data)
        return data


class AddressSchema(BaseSchema):
    class Meta:
        model = Address
        exclude = ('struct_id', 'struct_type', 'struct')

    device = fields.Function(deserialize=lambda obj, ctx: ctx.get('device'))
    phys = fields.Integer(data_key='phys_start')
    phys_size = fields.Integer()


class StructSchema(BaseSchema, SQLAlchemyAutoSchema):
    address = fields.Nested(AddressSchema)

    @pre_load()
    def _pre_load(self, data, **kwargs):
        # Have our AddressSchema read its fields from our own struct
        data['address'] = data
        return data

    @post_load()
    def make_instance_post(self, instance, **kwargs):
        # Set our generic relationship on our Address FK
        instance.address.struct = instance
        return instance
