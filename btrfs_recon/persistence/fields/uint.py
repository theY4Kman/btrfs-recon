from typing import Any

import psycopg
import sqlalchemy as sa
from psycopg import adapt
from psycopg.types import TypeInfo
from psycopg.types.numeric import IntLoader
from sqlalchemy.dialects.postgresql.base import ischema_names
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg, _PGInteger
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.compiler import compiles

__all__ = [
    'uint1',
    'uint2',
    'uint4',
    'uint8',
]


def _register_uint_dbapi_type(adapters_map: adapt.AdaptersMap, t: TypeInfo):
    t.register(adapters_map)
    adapters_map.register_loader(t.oid, IntLoader)


def register_uint_dbapi_types(adapters_map: adapt.AdaptersMap, type_infos: dict[str, TypeInfo | None]):
    for typename, t in type_infos.items():
        if t is None:
            raise RuntimeError(
                f'Unable to fetch {typename} type from Postgres. '
                f'Has the pguint extension been installed?'
            )

        _register_uint_dbapi_type(adapters_map, t)


def get_uint_type_infos(dbapi_conn: psycopg.Connection) -> dict[str, TypeInfo | None]:
    return {
        typename: TypeInfo.fetch(dbapi_conn, typename)
        for typename in ('uint1', 'uint2', 'uint4', 'uint8')
    }


_uint_type_infos: dict[str, TypeInfo | None] = {}


def init_uint_types(dbapi_conn: psycopg.Connection, *dialects: PGDialect_psycopg):
    _uint_type_infos.update(get_uint_type_infos(dbapi_conn))

    for dialect in dialects:
        register_uint_dbapi_types(dialect._psycopg_adapters_map, _uint_type_infos)


class PGUnsignedInteger(_PGInteger):
    __visit_name__ = 'uint'
    sqltype = 'uint'

    def _compiler_dispatch(self, visitor, **kw):
        """Look for an attribute named "visit_<visit_name>" on the
        visitor, and call it with the same kw params.

        """
        try:
            return visitor.visit_uint(self, **kw)
        except AttributeError:
            return self.sqltype

    def result_processor(self, dialect: Dialect, coltype: Any):

        def process(value):
            if value is not None:
                return int(value)

        return process

    def bind_expression(self, bindvalue: Any) -> Any:
        return sa.cast(bindvalue, self)


class uint1(PGUnsignedInteger):
    sqltype = 'uint1'


class uint2(PGUnsignedInteger):
    sqltype = 'uint2'


class uint4(PGUnsignedInteger):
    sqltype = 'uint4'


class uint8(PGUnsignedInteger):
    sqltype = 'uint8'


ischema_names.update({
    'uint1': uint1,
    'uint2': uint2,
    'uint4': uint4,
    'uint8': uint8,
})


@compiles(PGUnsignedInteger, 'postgresql')
def compile_pg_uint(element, compiler, **kwargs):
    return element.sqltype
