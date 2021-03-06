from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
from typing import Any, BinaryIO, Generator, TYPE_CHECKING, Type

import inflection
import sqlalchemy as sa
import sqlalchemy.orm as orm
import sqlalchemy.orm.base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy_repr import PrettyRepr, Repr

from btrfs_recon import settings, structure
from btrfs_recon.parsing import parse_at

if TYPE_CHECKING:
    from btrfs_recon.persistence.serializers import StructSchema, registry
    from .address import Address
    from .key import Key
    from .tree_node import LeafItem

__all__ = [
    'Base',
    'BaseModel',
    'BaseStruct',
    'BaseLeafItemData',
]

repr_cls = PrettyRepr if settings.MODEL_REPR_PRETTY else Repr

if settings.MODEL_REPR_ID:
    class IncludeIdRepr(repr_cls):
        def _iter_attrs(self, obj) -> Generator[tuple[str, Any], None, None]:
            yield '_id', id(obj)
            yield from super()._iter_attrs(obj)

    repr_cls = IncludeIdRepr

_shared_repr = repr_cls()


class RepresentableBase:
    def __repr__(self) -> str:
        return _shared_repr.repr(self)

    @declared_attr
    def __tablename__(cls) -> str:
        return inflection.underscore(cls.__name__)


Base = declarative_base(cls=RepresentableBase)


_SESSION_NOT_SET = object()


class BaseModel(Base):
    __abstract__ = True
    __table__: sa.Table

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    created_at = sa.Column(sa.DateTime, server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime, server_default=sa.func.now(), onupdate=datetime.utcnow, nullable=False)


class BaseStruct(BaseModel):
    """Base model for all addressable structures"""
    __abstract__ = True

    _version = sa.Column(sa.Integer, server_default='0', doc="Version number of this model's serializer at time of parsing")

    address_id: declared_attr[int] = declared_attr(
        lambda cls: sa.Column(sa.ForeignKey('address.id'), nullable=False)
    )
    address: declared_attr[Address] = declared_attr(
        lambda cls: orm.relationship('Address', lazy='joined', innerjoin=True)
    )

    @classmethod
    def get_registry_entry(cls) -> registry.RegistryEntry:
        from btrfs_recon.persistence.serializers import registry
        if entry := registry.find_by_model(cls):
            return entry
        else:
            raise KeyError(f'Model {cls.__name__} was not found in registry')

    @classmethod
    def get_schema_class(cls) -> Type[StructSchema]:
        entry = cls.get_registry_entry()
        return entry.schema

    @classmethod
    def get_struct_class(cls) -> Type[structure.Struct]:
        entry = cls.get_registry_entry()
        return entry.struct

    # TODO: add get_default_contextkw, to streamline fulfilment of required Struct deets

    def parse_disk(self, *, fp: BinaryIO = None, **contextkw) -> structure.Struct:
        """Parse the on-disk structure, using stored address info"""
        struct_cls = self.get_struct_class()

        address = self.address
        phys = address.phys
        device = address.device

        if fp is None:
            ctx = device.open()
        else:
            ctx = nullcontext(fp)

        with ctx as stream:
            return parse_at(stream, phys, struct_cls, **contextkw)

    def reparse(
        self, *, fp: BinaryIO = None, session: orm.Session | None = _SESSION_NOT_SET, **contextkw
    ) -> structure.Struct:
        """Update the current instance with info parsed from the on-disk structure"""
        struct = self.parse_disk(fp=fp, **contextkw)
        self.update_from_struct(struct, session=session)
        return struct

    def update_from_struct(
        self, struct: structure.Struct, *, session: orm.Session | None = _SESSION_NOT_SET
    ) -> None:
        """Update the current instance with info from a struct"""
        if session is _SESSION_NOT_SET:
            session = orm.base.instance_state(self).session

        struct.to_model(instance=self, session=session, context={'device': self.address.device})

    def write_disk(
        self,
        struct: structure.Struct,
        *,
        fp: BinaryIO = None,
        update_model: bool = True,
        session: orm.Session | None = _SESSION_NOT_SET,
        **contextkw,
    ) -> int:
        """Write the structure back to disk"""
        address = self.address
        phys = address.phys
        device = address.device

        #: We build the bytes in memory, to provide a final count of written bytes
        raw_bytes = struct.build(struct, **contextkw)

        if fp is None:
            ctx = device.open(write=True)
        else:
            ctx = nullcontext(fp)

        with ctx as stream:
            stream.seek(phys)
            bytes_written = stream.write(raw_bytes)

        if update_model:
            self.update_from_struct(struct, session=session)

        return bytes_written


class BaseLeafItemData(BaseStruct):
    """Base model for all items specified in leaf nodes"""
    __abstract__ = True

    leaf_item_id: declared_attr[int] = declared_attr(
        lambda cls: sa.Column(sa.ForeignKey('leaf_item.id'), nullable=False)
    )
    leaf_item: declared_attr[LeafItem] = declared_attr(
        lambda cls: orm.relationship('LeafItem', lazy='joined', innerjoin=True)
    )

    @hybrid_property
    def key(self) -> Key:
        return self.leaf_item.key

    @key.expression
    def key(cls):
        from btrfs_recon.persistence import Key
        # XXX: does this make any sense?
        return Key

    @hybrid_property
    def objectid(self) -> int:
        return self.key.objectid

    @objectid.expression
    def objectid(cls):
        return cls.key.objectid

    @hybrid_property
    def offset(self) -> int:
        return self.key.offset

    @offset.expression
    def offset(cls):
        return cls.key.offset
