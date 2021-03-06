from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, BinaryIO, Callable, Optional, Type, TYPE_CHECKING, TypeVar

import construct as cs
from construct_typed import Construct, Context, csfield, DataclassMixin, DataclassStruct
from construct_typed.generic_wrapper import ParsedType

from . import fields

if TYPE_CHECKING:
    from btrfs_recon.persistence import models, serializers

__all__ = ['Struct', 'field']


class _StructMeta(type):
    """Automatically applies @dataclass to subclasses, and adds standard addressing fields"""

    def __new__(mcs, name, bases, attrs, **kwargs):
        annotations = attrs['__annotations__']
        is_base_struct = bases == (DataclassMixin,)

        if is_base_struct:
            #
            # Subclasses of dataclasses will place their parents' fields before
            # their own declared fields. For regular dataclasses, this matters
            # not very much, but for these dataclass-based Construct Structs,
            # ordering is very important.
            #
            # Here, we remove the phys_start and phys_end fields declared on the
            # Struct base class, so that they may be defined in the proper
            # order dynamically for each subclass.
            #
            del annotations['phys_start']
            del annotations['phys_end']
            del annotations['phys_size']

        else:
            phys_field = partial(csfield, fields.HexDecInt(cs.Tell))
            phys_type = int

            attrs = {
                # Add our beginning and end physical location fields
                'phys_start': phys_field(),
                **attrs,
                'phys_end': phys_field(),
                'phys_size': csfield(cs.Computed(cs.this.phys_end - cs.this.phys_start)),

                # And add annotations for them
                '__annotations__': {
                    'phys_start': phys_type,
                    **annotations,
                    'phys_end': phys_type,
                    'phys_size': phys_type,
                },
            }

        cls = super().__new__(mcs, name, bases, attrs, **kwargs)
        cls = dataclass(cls)
        return cls


_TYPED_STRUCT_AS_STRUCT_KEY = '__struct'

StructT = TypeVar('StructT', bound='Struct')


class Struct(DataclassMixin, metaclass=_StructMeta):
    phys_start: int
    # NOTE: this field is moved to last position by _StructMeta
    phys_end: int
    phys_size: int

    @classmethod
    def as_struct(cls) -> cs.Struct:
        if not hasattr(cls, _TYPED_STRUCT_AS_STRUCT_KEY):
            setattr(cls, _TYPED_STRUCT_AS_STRUCT_KEY, DataclassStruct(cls))
        return getattr(cls, _TYPED_STRUCT_AS_STRUCT_KEY)

    @classmethod
    def build(cls: Type[StructT], obj: StructT, **contextkw) -> bytes:
        return cls.as_struct().build(obj, **contextkw)

    @classmethod
    def build_stream(cls: Type[StructT], obj: StructT, stream: BinaryIO, **contextkw) -> None:
        cls.as_struct().build_stream(obj, stream, **contextkw)

    @classmethod
    def parse(cls: Type[StructT], data: bytes, **contextkw) -> StructT:
        return cls.as_struct().parse(data, **contextkw)

    @classmethod
    def parse_stream(cls: Type[StructT], stream: BinaryIO, **contextkw) -> StructT:
        return cls.as_struct().parse_stream(stream, **contextkw)

    def __class_getitem__(cls, count) -> Construct:
        return cls.as_struct()[count]

    @classmethod
    def sizeof(cls, **contextkw) -> int:
        return cls.as_struct().sizeof(**contextkw)

    @classmethod
    def get_schema_class(cls) -> Type[serializers.StructSchema] | None:
        from btrfs_recon.persistence import serializers
        if entry := serializers.registry.find_by_struct(cls):
            return entry.schema

    def to_model(
        self, *, session=None, instance=None, context: dict | None = None
    ) -> models.BaseStruct:
        schema_cls = self.get_schema_class()
        if not schema_cls:
            raise ValueError(f'No schema class configured for {self.__class__.__name__}')

        schema = schema_cls(
            context=context, session=session, transient=not session, instance=instance
        )
        return schema.load(self)


def field(
    subcon: Construct[ParsedType, Any] | Type[Struct],
    doc: Optional[str] = None,
    parsed: Optional[Callable[[Any, Context], None]] = None,
):
    if isinstance(subcon, type) and issubclass(subcon, Struct):
        subcon = subcon.as_struct()
    return csfield(subcon, doc, parsed)
