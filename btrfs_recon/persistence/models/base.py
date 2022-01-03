from datetime import datetime
from typing import Type, TYPE_CHECKING

import inflection
import sqlalchemy as sa
from sqlalchemy import orm as orm
from sqlalchemy.orm import declarative_base, declared_attr

from btrfs_recon import structure

if TYPE_CHECKING:
    from btrfs_recon.persistence import serializers
    from .address import Address

__all__ = ['Base', 'BaseModel', 'BaseStruct']

Base = declarative_base()


class BaseModel(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls) -> str:
        return inflection.underscore(cls.__name__)

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    created_at = sa.Column(sa.DateTime, default=datetime.utcnow, server_default=sa.func.now(), nullable=False)
    updated_at = sa.Column(sa.DateTime, default=datetime.utcnow, server_default=sa.func.now(), server_onupdate=sa.func.now(), nullable=False)


class BaseStruct(BaseModel):
    """Base model for all addressable structures"""
    __abstract__ = True

    address_id = declared_attr(lambda cls: sa.Column(sa.ForeignKey('address.id'), nullable=False))
    address = declared_attr(lambda cls: orm.relationship('Address', lazy='joined'))

    @classmethod
    def get_schema_class(cls) -> Type['serializers.StructSchema']:
        """Return the marshmallow Schema used for deserialization of this struct type"""
        raise NotImplementedError

    @classmethod
    def get_struct_class(cls) -> Type[structure.Struct]:
        """Return the Construct Struct used to parse the structure on disk"""
        raise NotImplementedError


class BaseItem(BaseStruct):
    """Base model for all items of tree nodes"""
    __abstract__ = True

    # Key.ty value of the structure this model handles
    ITEM_TY: structure.KeyType

    header_id = declared_attr(lambda cls: sa.Column(sa.ForeignKey('header.id'), nullable=False))
    header = declared_attr(lambda cls: orm.relationship('Header', lazy='joined'))
