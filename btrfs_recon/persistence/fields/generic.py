from __future__ import annotations

from collections import defaultdict
from typing import Callable, ClassVar, TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.event
import sqlalchemy.orm as orm
import sqlalchemy_utils.generic

if TYPE_CHECKING:
    from btrfs_recon.persistence import BaseModel

__all__ = [
    'generic_relationship',
]


class GenericAttributeImpl(sqlalchemy_utils.generic.GenericAttributeImpl):
    _FLUSHED_INSTANCES: ClassVar[set[BaseModel]] = set()
    _FLUSH_LISTENERS: ClassVar[
        dict[BaseModel, list[Callable[[orm.Session, orm.UOWTransaction], None]]]
    ] = defaultdict(list)

    @classmethod
    def after_flush(cls, session: orm.Session, flush_context: orm.UOWTransaction):
        cls._FLUSHED_INSTANCES |= set(cls._FLUSH_LISTENERS) & set(session.new)

    @classmethod
    def after_flush_postexec(cls, session: orm.Session, flush_context: orm.UOWTransaction):
        for instance in cls._FLUSHED_INSTANCES:
            listeners = cls._FLUSH_LISTENERS[instance]
            for listener in listeners:
                listener(session, flush_context)
            listeners.clear()

        cls._FLUSHED_INSTANCES.clear()

    def set(self, state, dict_, initiator,
            passive=orm.attributes.PASSIVE_OFF,
            check_old=None,
            pop=False):

        # Set us on the state.
        dict_[self.key] = initiator

        if initiator is None:
            # Nullify relationship args
            for id in self.parent_token.id:
                dict_[id.key] = None
            dict_[self.parent_token.discriminator.key] = None
        else:
            initiator_state: orm.InstanceState = orm.attributes.instance_state(initiator)
            if initiator_state.pending or initiator_state.transient:
                self._init_post_update(initiator, state)
            else:
                self._set_generic_columns(initiator, state)

    def _set_generic_columns(self, initiator, state):
        # Get the primary key of the initiator and ensure we
        # can support this assignment.
        class_ = type(initiator)
        mapper = orm.class_mapper(class_)
        instance = state.obj()

        pk = mapper.identity_key_from_instance(initiator)[1]

        # Set the identifier and the discriminator.
        discriminator = None if all(v is None for v in pk) else str(class_.__name__)

        for index, id in enumerate(self.parent_token.id):
            orm.attributes.set_attribute(instance, id.key, pk[index])
        orm.attributes.set_attribute(instance, self.parent_token.discriminator.key, discriminator)

    def _init_post_update(self, initiator, state):
        def on_initiator_persisted(session: orm.Session, flush_context: orm.UOWTransaction):
            self._set_generic_columns(initiator, state)

        self._FLUSH_LISTENERS[initiator].append(on_initiator_persisted)


sa.event.listen(orm.Session, 'after_flush', GenericAttributeImpl.after_flush)
sa.event.listen(orm.Session, 'after_flush_postexec', GenericAttributeImpl.after_flush_postexec)


class GenericRelationshipProperty(sqlalchemy_utils.generic.GenericRelationshipProperty):
    def instrument_class(self, mapper):
        orm.attributes.register_attribute(
            mapper.class_,
            self.key,
            comparator=self.Comparator(self, mapper),
            parententity=mapper,
            doc=self.doc,
            impl_class=GenericAttributeImpl,
            parent_token=self
        )


def generic_relationship(discriminator, id, doc=None):
    return GenericRelationshipProperty(discriminator, id, doc=doc)
