from typing import Type

from btrfs_recon import persistence, structure
from .base import StructSchema

__all__ = [
    'register_schema',
    'autoregister',
    'schema_for_struct',
    'schema_for_model',
    'struct_for_schema',
    'model_for_schema',
    'model_for_struct',
    'struct_for_model',
]

StructSchemaType = Type[StructSchema]
StructModelType = Type[persistence.BaseStruct]
StructType = Type[structure.Struct]

_schema_registry: dict[StructSchemaType, tuple[StructModelType, StructType]] = {}
_struct_to_schema: dict[StructType, StructSchemaType] = {}
_model_to_schema: dict[StructModelType, StructSchemaType] = {}


def register_schema(schema_cls: StructSchemaType) -> None:
    if schema_cls in _schema_registry:
        raise ValueError(f'{schema_cls} already registered')

    model_cls, struct_cls = schema_cls.opts.model, schema_cls.opts.struct_class

    if model_cls in _model_to_schema:
        assoc_model_schema = _model_to_schema[model_cls]
        raise ValueError(f'{model_cls} is already registered to {assoc_model_schema}')

    if struct_cls in _struct_to_schema:
        assoc_struct_schema = _struct_to_schema[struct_cls]
        raise ValueError(f'{model_cls} is already registered to {assoc_struct_schema}')

    _schema_registry[schema_cls] = (model_cls, struct_cls)
    _model_to_schema[model_cls] = schema_cls
    _struct_to_schema[struct_cls] = schema_cls


def autoregister() -> None:
    """Automatically register any StructSchema subclasses"""
    from .base import StructSchema

    for schema_cls in StructSchema.__subclasses__():
        register_schema(schema_cls)


def struct_for_schema(schema_cls: StructSchemaType) -> StructType | None:
    if schema_cls in _schema_registry:
        model_cls, struct_cls = _schema_registry[schema_cls]
        return struct_cls


def model_for_schema(schema_cls: StructSchemaType) -> StructModelType | None:
    if schema_cls in _schema_registry:
        model_cls, struct_cls = _schema_registry[schema_cls]
        return model_cls


def schema_for_struct(struct_cls: StructType) -> StructSchemaType | None:
    return _struct_to_schema.get(struct_cls)


def schema_for_model(model_cls: StructModelType) -> StructSchemaType | None:
    return _model_to_schema.get(model_cls)


def model_for_struct(struct_cls: StructType) -> StructModelType | None:
    if schema_cls := schema_for_struct(struct_cls):
        return model_for_schema(schema_cls)


def struct_for_model(model_cls: StructModelType) -> StructType | None:
    if schema_cls := schema_for_model(model_cls):
        return struct_for_schema(schema_cls)
