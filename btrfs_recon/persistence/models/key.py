import sqlalchemy as sa
from sqlalchemy.orm import declarative_mixin

__all__ = ['Keyed']


@declarative_mixin
class Keyed:
    objectid = sa.Column(sa.BigInteger, nullable=False)
    ty = sa.Column(sa.SmallInteger, nullable=False)
    offset = sa.Column(sa.BigInteger, nullable=False)
