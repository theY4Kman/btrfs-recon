from __future__ import annotations

import typing
from typing import TYPE_CHECKING

import marshmallow as ma
from construct_typed import EnumBase
from marshmallow.fields import *

if TYPE_CHECKING:
    from .base import BaseSchema


class Nested(ma.fields.Nested):  # type: ignore[no-redef]
    """Nested Schema field supporting accessing the nesting Schema"""

    _schema: BaseSchema | None  # type: ignore[assignment]

    @property
    def schema(self):
        schema: BaseSchema = super().schema
        schema.nesting_schema = self.parent
        schema.root_schema = getattr(self.parent, 'root_schema', None) or self.parent
        schema.nesting_name = self.name
        schema._session = self.parent.session
        return schema


class ParentInstanceField(Field):
    """Resolves to the instance made for the Schema which references our owning Schema by Nested"""

    parent: BaseSchema  # type: ignore[assignment]

    def deserialize(
        self,
        value,
        attr: str | None = None,
        data: typing.Mapping[str, typing.Any] | None = None,
        **kwargs,
    ):
        # If a ParentInstanceField is declared, but we're the root schema, there's no parent
        # instance to pull from
        if nesting_schema := self.parent.nesting_schema:
            # XXX: could we possibly do something other than *nothing* here?
            nesting_schema._parent_instance_fields.append((self.parent.nesting_name, self.name))

        return super().deserialize(value=value, attr=attr, data=data, **kwargs)


class NamedEnum(Str):
    def _deserialize(self, value, attr, data, **kwargs) -> typing.Any:
        if isinstance(value, EnumBase):
            value = value.name
        return super()._deserialize(value, attr, data, **kwargs)
