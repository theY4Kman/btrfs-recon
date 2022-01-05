import dataclasses
import typing

import marshmallow
from marshmallow import fields, post_load, pre_load
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchemaMeta, SQLAlchemyAutoSchemaOpts

from btrfs_recon.persistence import Address, BaseStruct
from btrfs_recon.structure import Struct, KeyType

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


class StructSchemaOpts(SQLAlchemyAutoSchemaOpts):
    """Records info for translating between DB models and on-disk structures

    Adds the following option:
     - `struct_class`: The Construct BaseStruct class used to parse the on-disk structure
     - `version`: An integer to be incremented whenever the Schema class changes its output.
            This allows rows produced by the Schema to be re-parsed when the Schema changes.
     - `key_type`: The KeyType enum value this Schema handles the data of a leaf item for.

    """

    struct_class: typing.Type[Struct] | None = None
    version: int = 0
    key_type: KeyType | None = None

    def __init__(self, meta, *args, **kwargs):
        super().__init__(meta, *args, **kwargs)
        self.struct_class = getattr(meta, 'struct_class', None)
        self.version = getattr(meta, 'version', self.version)
        self.key_type = getattr(meta, 'key_type', self.key_type)


class StructSchema(BaseSchema, SQLAlchemyAutoSchema):
    OPTIONS_CLASS = StructSchemaOpts
    opts: StructSchemaOpts

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
