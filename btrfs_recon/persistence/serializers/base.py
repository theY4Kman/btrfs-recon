from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from typing import Any, Mapping, TYPE_CHECKING, Type

import marshmallow as ma
import marshmallow.validate
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import sqlalchemy.event
import sqlalchemy.orm as orm
from marshmallow_sqlalchemy import ModelConverter, SQLAlchemyAutoSchema
from marshmallow_sqlalchemy.schema import SQLAlchemyAutoSchemaMeta, SQLAlchemyAutoSchemaOpts

from btrfs_recon.persistence import Address
from btrfs_recon.persistence.fields import uint8
from btrfs_recon.persistence.serializers import fields
from btrfs_recon.structure import KeyType, Struct

if TYPE_CHECKING:
    from btrfs_recon.persistence import BaseStruct

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
        sa.Enum: fields.NamedEnum,
        pg.BYTEA: fields.Raw,
        # NOTE: date/time fields are already converted to datetime objects
        sa.DateTime: fields.Raw,
        sa.Date: fields.Raw,
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
    nesting_schema: BaseSchema | None
    # This will be set to the rootmost parent Schema
    root_schema: BaseSchema | None
    # This will be set to the name of the Nested field in the parent Schema
    nesting_name: str | None

    # While load() is executing, this will be filled with the data being deserialized.
    # When load(many=True) is used, this value will hold a single item from the collection
    # at any time.
    processed_data: Mapping[str, Any] | None

    # Set of (nested_field_name, field_in_nested_schema, is_many) filled by ParentInstanceFields
    # inside the schema of a Nested field within the current schema. After the make_instance hook
    # runs, we enumerate these items and set `instance.nested_field_name.field_in_nested_schema`
    # to our new instance.
    #
    # If is_many, we assume `instance.nested_field_name` will be a list, and we'll perform the
    # assignment on every nested instance in the list.
    #
    _parent_instance_fields: set[tuple[str, str, bool]]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nesting_schema = None
        self.root_schema = None
        self.nesting_name = None
        self.processed_data = None
        self._parent_instance_fields = set()

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

    @ma.pre_load
    def _dataclass_to_dict(self, data: dict | Struct, **kwargs) -> dict[str, Any]:
        if dataclasses.is_dataclass(data):
            data = dataclasses.asdict(data)
        return data

    @ma.post_load(pass_many=True)
    def ensure_nested_instance_for_many(self, outputs: list[dict[str, Any]], many: bool, **kwargs):
        if self.many and self.instance:
            for i, value in enumerate(outputs):
                value['__i'] = i
        return outputs

    @ma.post_load
    def make_instance(self, data, **kwargs):
        if not self.many:
            return super().make_instance(data, **kwargs)

        instances = self.instance
        if self.instance and '__i' in data:
            self.instance = instances[data.pop('__i')]

        try:
            return super().make_instance(data, **kwargs)
        finally:
            self.instance = instances

    @ma.post_load
    def make_instance_post_fulfill_parent_instance_fields(self, instance, **kwargs):
        for field, child_field, is_many in self._parent_instance_fields:
            if nested_instance := getattr(instance, field):
                if is_many and not isinstance(nested_instance, Iterable):
                    raise TypeError(f'Expected {field} to be a list, found: {nested_instance}')

                children = nested_instance if is_many else (nested_instance,)
                for child in children:
                    setattr(child, child_field, instance)

        return instance

    @ma.post_load
    def make_instance_session_add(self, instance, **kwargs):
        if not self.transient and self.session:
            self.session.add(instance)
        return instance


class AddressSchema(BaseSchema):
    class Meta:
        model = Address
        exclude = ('struct_id', 'struct_type')

    phys = fields.Integer(data_key='phys_start')
    phys_size = fields.Integer()

    struct = fields.ParentInstanceField()

    @ma.post_load
    def make_instance_post(self, instance: Address, **kwargs):
        from btrfs_recon.persistence.models import Device

        ctx_device = self.context['device']
        if isinstance(ctx_device, Device):
            instance.device = ctx_device
            instance.device_id = instance.device.id
        else:
            instance.device_id = ctx_device

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
    address = fields.Nested(AddressSchema, data_key='*', attribute='address')

    @ma.post_load()
    def post_make_instance_upsert_address(self, instance, *, many: bool = False, **kwargs):
        _TRACKED_STRUCTS.append(instance)
        return instance


_TRACKED_STRUCTS: list[BaseStruct] = []


@sa.event.listens_for(orm.Session, 'before_flush')
def before_flush(session, flush_context, instances):
    if not _TRACKED_STRUCTS:
        return

    # 1. Grab all Addresses of tracked structs
    address_key = lambda addr: (
        addr.device_id or addr.device.id,
        addr.phys,
        addr.phys_size,
    )
    address_struct_map = {
        address_key(struct.address): struct
        for struct in reversed(_TRACKED_STRUCTS)
    }
    _TRACKED_STRUCTS.clear()

    # 2. Construct query to select all address rows with matching contents
    values = sa.values(
        sa.column('device_id', sa.Integer),
        sa.column('phys', uint8),
        sa.column('phys_size', uint8),
        name='address_input',
    ).data(address_struct_map.keys())
    q = (
        sa.select(
            Address.id,
            Address.device_id,
            Address.phys,
            Address.phys_size,
            Address.struct_type,
            Address.struct_id,
        )
        .join(values, onclause=(
            (Address.device_id == values.c.device_id)
            & (Address.phys == values.c.phys)
            & (Address.phys_size == values.c.phys_size)
        ))
    )
    matching_addresses = session.execute(q)

    to_delete = []
    for address in matching_addresses:
        if not (struct := address_struct_map.get(address_key(address))):
            continue

        # If existing Address row has same struct_type, use the existing Address in the matching
        # Struct, and change the Struct's INSERT to an UPDATE
        if type(struct).__name__ == address.struct_type:
            # Since we'll be using the exact same existing address row, with no updates,
            # we completely remove and stop tracking our proposed Address instance
            session.expunge(struct.address)

            # We still want to track our Struct, as it may have changes requiring updates,
            # but it should no longer be considered "new", and instead should just be marked
            # dirty.
            session._new.pop(orm.attributes.instance_state(struct), None)
            orm.attributes.flag_dirty(struct)

            orm.attributes.set_committed_value(struct, 'id', address.struct_id)
            orm.attributes.set_committed_value(struct, 'address', None)
            orm.attributes.set_committed_value(struct, 'address_id', address.id)

        # If the existing Address row has a differing struct_type, we're superseding it, not
        # updating. So, delete the existing Address row, which will CASCADE to its referring Struct
        else:
            to_delete.append(address.id)
            session.expunge(address)

    session.execute(sa.delete(Address).filter(Address.id.in_(to_delete)))


class LeafItemDataSchema(StructSchema):
    leaf_item = fields.ParentInstanceField()
