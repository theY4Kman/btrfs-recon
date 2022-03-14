from __future__ import annotations

import typing
from typing import TYPE_CHECKING

import marshmallow as ma
from marshmallow.decorators import POST_LOAD
from marshmallow.fields import *

if TYPE_CHECKING:
    from .base import BaseSchema


class Nested(ma.fields.Nested):  # type: ignore[no-redef]
    """Nested Schema field supporting accessing the nesting Schema"""

    _schema: BaseSchema | None  # type: ignore[assignment]

    @property
    def schema(self):
        if not self._schema:
            schema: BaseSchema = super().schema
            schema.nesting_schema = self.parent
            schema.root_schema = getattr(self.parent, 'root_schema', None) or self.parent
            schema.nesting_name = self.name
            schema._session = self.parent.session
        return self._schema


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
        #
        # XXX (zkanzler): HACKS BE HERE!!!!!
        #
        #  In order to make this field work, we need three things: the Schema that has nested our
        #  parent Schema, the name of the Nested field in the nesting Schema, and, finally, the
        #  loaded SQLAlchemy model instance after it's post_loaded by marshmallow-sqlalchemy.
        #  The first two are handled by some added base Schema fields and an altered Nested field to
        #  set them, but the last one requires adding a post_load hook to the nesting Schema,
        #  to be invoked *after* ma-sqla's make_instance hook.
        #
        #  To fulfill the last requirement of a post_load hook, we must mutate the hooks of the
        #  nesting Schema, which is just a little weird.
        #

        # This is named to be lexicographically ordered after marshmallow-sqlalchemy's make_instance
        # post_load hook, which creates the SQLAlchemy model instance.
        hook_name = f'make_instance_post_set_{self.parent.nesting_name}__{self.name}'

        if not hasattr(self.parent.nesting_schema, hook_name):
            setattr(self.parent.nesting_schema, hook_name, self.set_parent_instance)

        nesting_post_loads = self.parent.nesting_schema._hooks[POST_LOAD, False]
        if hook_name not in nesting_post_loads:
            nesting_post_loads.append(hook_name)

        return super().deserialize(value=value, attr=attr, data=data, **kwargs)

    @ma.post_load()
    def set_parent_instance(self, instance, *, many: bool = False, **kwargs):
        # XXX (zkanzler): does this need to account for a load name other than the field name?
        child_instance = getattr(instance, self.parent.nesting_name)
        setattr(child_instance, self.name, instance)
        return instance
