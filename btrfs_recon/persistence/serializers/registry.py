from dataclasses import dataclass
from typing import Type

from btrfs_recon import persistence, structure
from .base import StructSchema

__all__ = [
    'register_schema',
    'autoregister',
    'find_by_schema',
    'find_by_model',
    'find_by_struct',
]

StructSchemaType = Type[StructSchema]
StructModelType = Type[persistence.BaseStruct]
StructType = Type[structure.Struct]


@dataclass(slots=True, frozen=True)
class RegistryEntry:
    schema: StructSchemaType
    model: StructModelType
    struct: StructType


_registry: dict[StructSchemaType, RegistryEntry] = {}
_struct_index: dict[StructType, RegistryEntry] = {}
_model_index: dict[StructModelType, RegistryEntry] = {}
_key_type_index: dict[structure.KeyType, RegistryEntry]


def register_schema(schema_cls: StructSchemaType) -> None:
    if schema_cls in _registry:
        raise ValueError(f'{schema_cls} is already registered')

    model_cls = schema_cls.opts.model
    struct_cls = schema_cls.opts.struct_class
    key_type = schema_cls.opts.key_type

    if model_cls in _model_index:
        assoc_model_schema = _model_index[model_cls]
        raise ValueError(f'{model_cls} is already registered to {assoc_model_schema}')

    if struct_cls in _struct_index:
        assoc_struct_schema = _struct_index[struct_cls]
        raise ValueError(f'{struct_cls} is already registered to {assoc_struct_schema}')

    if key_type is not None and key_type in _key_type_index:
        assoc_key_type_schema = _struct_index[struct_cls]
        raise ValueError(f'{key_type} is already registered to {assoc_key_type_schema}')

    entry = RegistryEntry(schema=schema_cls, model=model_cls, struct=struct_cls)
    _registry[schema_cls] = _model_index[model_cls] = _struct_index[struct_cls] = entry

    if key_type is not None:
        _key_type_index[key_type] = entry


def autoregister() -> None:
    """Automatically register any StructSchema subclasses"""
    from .base import StructSchema

    for schema_cls in StructSchema.__subclasses__():
        register_schema(schema_cls)


def find_by_schema(schema_cls: StructSchemaType) -> RegistryEntry | None:
    return _registry.get(schema_cls)


def find_by_model(model_cls: StructModelType) -> RegistryEntry | None:
    return _model_index.get(model_cls)


def find_by_struct(struct_cls: StructType) -> RegistryEntry | None:
    return _struct_index.get(struct_cls)


def find_by_key_type(key_type: structure.KeyType) -> RegistryEntry | None:
    return _key_type_index.get(key_type)
