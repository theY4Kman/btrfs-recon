from __future__ import annotations

import dataclasses
from typing import Any, Mapping, Type

import marshmallow.validate
import marshmallow as ma
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
from marshmallow import pre_load
from marshmallow_sqlalchemy import ModelConverter, SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchemaMeta, SQLAlchemyAutoSchemaOpts

from btrfs_recon.persistence import Address
from btrfs_recon.persistence.serializers import fields
from btrfs_recon.structure import Struct, KeyType

__all__ = [
    'BaseSchema',
    'AddressSchema',
    'StructSchema',
    'LeafItemDataSchema',
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


class PostgresModelConverter(ModelConverter):
    SQLA_TYPE_MAPPING = {
        **ModelConverter.SQLA_TYPE_MAPPING,
        sa.Enum: fields.Raw,
        pg.BYTEA: fields.Raw,
    }

    def _add_column_kwargs(self, kwargs, column):
        super()._add_column_kwargs(kwargs, column)

        if isinstance(column.type, sa.Enum) and (validators := kwargs.get('validate')):
            kwargs['validate'] = [v for v in validators if not isinstance(v, ma.validate.Length)]


class BaseSchema(SQLAlchemyAutoSchema, metaclass=InheritableMetaSchemaMeta):
    class Meta:
        # Don't bind Schema to a session
        transient = True
        # Produce model instance when calling load()
        load_instance = True
        # Don't yell when load() is passed fields not declared in Schema
        unknown = ma.INCLUDE
        # Autogenerate correct fields for other types of model columns
        model_converter = PostgresModelConverter

    # If this Schema invoked through a Nested field, this will be set to the parent Schema
    nesting_schema: BaseSchema | None = None
    # This will be set to the rootmost parent Schema
    root_schema: BaseSchema | None = None
    # This will be set to the name of the Nested field in the parent Schema
    nesting_name: str | None = None

    # While load() is executing, this will be filled with the data being deserialized.
    # When load(many=True) is used, this value will hold a single item from the collection
    # at any time.
    processed_data: Mapping[str, Any] | None = None

    def _deserialize(self, data, *, many: bool = False, **kwargs):
        if many:
            return super()._deserialize(data, many=many, **kwargs)

        self.processed_data = data

        # Support the passing of the entire data dict to fields declaring data_key='*'
        if data:
            data = {**data, '*': data}

        try:
            return super()._deserialize(data, many=many, **kwargs)
        finally:
            self.processed_data = None

    @pre_load
    def _dataclass_to_dict(self, data: dict | Struct, **kwargs) -> dict[str, Any]:
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data)
        return data


class AddressSchema(BaseSchema):
    class Meta:
        model = Address
        exclude = ('struct_id', 'struct_type')

    phys = fields.Integer(data_key='phys_start')
    phys_size = fields.Integer()

    struct = fields.ParentInstanceField()

    @ma.post_load
    def make_instance_post(self, instance: Address, **kwargs):
        instance.device = self.context['device']
        return instance


class StructSchemaOpts(SQLAlchemyAutoSchemaOpts):
    """Records info for translating between DB models and on-disk structures

    Adds the following option:
     - `struct_class`: The Construct BaseStruct class used to parse the on-disk structure
     - `version`: An integer to be incremented whenever the Schema class changes its output.
            This allows rows produced by the Schema to be re-parsed when the Schema changes.
     - `key_type`: The KeyType enum value this Schema handles the data of a leaf item for.

    """

    struct_class: Type[Struct] | None = None
    version: int = 0
    key_type: KeyType | None = None

    def __init__(self, meta, *args, **kwargs):
        super().__init__(meta, *args, **kwargs)
        self.struct_class = getattr(meta, 'struct_class', None)
        self.version = getattr(meta, 'version', self.version)
        self.key_type = getattr(meta, 'key_type', self.key_type)


class StructSchemaVersionField(fields.Field):
    """Simply returns the StructSchema's Meta.version"""

    def _bind_to_schema(self, field_name, schema):
        if not isinstance(schema, StructSchema):
            raise TypeError('This field can only be placed within StructSchema subclasses.')
        super()._bind_to_schema(field_name, schema)

    def deserialize(self, value, attr=None, data=None, **kwargs):
        return self.parent.opts.version


class StructSchema(BaseSchema, SQLAlchemyAutoSchema):
    OPTIONS_CLASS = StructSchemaOpts
    opts: StructSchemaOpts

    _version = StructSchemaVersionField()
    address = fields.Nested(AddressSchema, data_key='*')


class LeafItemDataSchema(StructSchema):
    leaf_item = fields.ParentInstanceField()
