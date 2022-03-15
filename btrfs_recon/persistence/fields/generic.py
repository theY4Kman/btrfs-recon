from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, ClassVar, Optional, TYPE_CHECKING

import sqlalchemy as sa
import sqlalchemy.event
import sqlalchemy.orm as orm
import sqlalchemy.orm.base
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

    def get_all_pending(self, state, dict_, passive=orm.base.PASSIVE_NO_INITIALIZE):
        return orm.attributes.ScalarObjectAttributeImpl.get_all_pending(
            self, state, dict_, passive=passive
        )

    def set(self, state, dict_, initiator,
            passive=orm.attributes.PASSIVE_OFF,
            check_old=None,
            pop=False):

        # Mark related model as "added", not "unchanged"
        old = dict_.get(self.key, orm.base.NO_VALUE)
        dict_[self.key] = initiator
        state._modified_event(dict_, self, old)

        if initiator is None:
            # Remove our value from state
            if self.key in dict_:
                del dict_[self.key]

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
    cascade = orm.CascadeOptions(('all', 'delete-orphan'))
    passive_deletes = False

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

    def cascade_iterator(
        self,
        type_,
        state,
        dict_,
        visited_states,
        halt_on=None,
    ) -> None:
        # only actively lazy load on the 'delete' cascade
        if type_ != "delete" or self.passive_deletes:
            passive = orm.attributes.PASSIVE_NO_INITIALIZE
        else:
            passive = orm.attributes.PASSIVE_OFF

        if type_ == "save-update":
            tuples = state.manager[self.key].impl.get_all_pending(state, dict_)

        else:
            tuples = self._value_as_iterable(
                state, dict_, self.key, passive=passive
            )

        skip_pending = (
            type_ == "refresh-expire" and "delete-orphan" not in self._cascade
        )

        for instance_state, c in tuples:
            if instance_state in visited_states:
                continue

            if c is None:
                # would like to emit a warning here, but
                # would not be consistent with collection.append(None)
                # current behavior of silently skipping.
                # see [ticket:2229]
                continue

            instance_dict = orm.attributes.instance_dict(c)

            if halt_on and halt_on(instance_state):
                continue

            if skip_pending and not instance_state.key:
                continue

            instance_mapper = instance_state.manager.mapper

            visited_states.add(instance_state)

            yield c, instance_mapper, instance_state, instance_dict

    def _value_as_iterable(self, state, dict_, key, passive=orm.attributes.PASSIVE_OFF):
        """Return a list of tuples (state, obj) for the given
        key.

        returns an empty list if the value is None/empty/PASSIVE_NO_RESULT
        """

        impl = state.manager[key].impl
        x = impl.get(state, dict_, passive=passive)
        if x is orm.attributes.PASSIVE_NO_RESULT or x is None:
            return []
        elif hasattr(impl, "get_collection"):
            return [
                (orm.attributes.instance_state(o), o)
                for o in impl.get_collection(state, dict_, x, passive=passive)
            ]
        else:
            return [(orm.attributes.instance_state(x), x)]


def generic_relationship(discriminator, id, doc=None):
    return GenericRelationshipProperty(discriminator, id, doc=doc)
