import asyncio
from typing import Any, Optional

import psycopg
import sqlalchemy as sa
from psycopg import adapt
from psycopg.types import TypeInfo
from psycopg.types.numeric import _NumberDumper, IntLoader
from sqlalchemy.dialects.postgresql.psycopg import _PGInteger
from sqlalchemy.engine import Dialect
from sqlalchemy.ext.compiler import compiles

__all__ = [
    'uint1',
    'uint2',
    'uint4',
    'uint8',
]


def _register_uint_dbapi_type(dbapi_conn: psycopg.Connection, t: TypeInfo):
    class UintDumper(_NumberDumper):
        oid = t.oid

    adapters_map = dbapi_conn.adapters
    t.register(adapters_map)

    adapters_map.register_dumper(int, UintDumper)
    adapters_map.register_loader(t.oid, IntLoader)


def register_uint_dbapi_types(dbapi_conn: psycopg.Connection, type_infos: dict[str, TypeInfo | None]):
    for typename, t in type_infos.items():
        if t is None:
            raise RuntimeError(
                f'Unable to fetch {typename} type from Postgres. '
                f'Has the pguint extension been installed?'
            )

        _register_uint_dbapi_type(dbapi_conn, t)


def get_uint_type_infos(dbapi_conn: psycopg.Connection) -> dict[str, TypeInfo | None]:
    return {
        typename: TypeInfo.fetch(dbapi_conn, typename)
        for typename in ('uint1', 'uint2', 'uint4', 'uint8')
    }


class PGUnsignedInteger(_PGInteger):
    render_bind_cast = True


class uint(sa.TypeDecorator):
    impl = PGUnsignedInteger

    def bind_expression(self, bindparam: Any) -> Any:
        return sa.cast(bindparam, self.__class__)

    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[int]:
        if value is not None:
            return int(value)


class uint1(uint):
    __visit_name__ = 'uint1'  # type: ignore[misc]
    cache_ok = True


class uint2(uint):
    __visit_name__ = 'uint2'  # type: ignore[misc]
    cache_ok = True


class uint4(uint):
    __visit_name__ = 'uint4'  # type: ignore[misc]
    cache_ok = True


class uint8(uint):
    __visit_name__ = 'uint8'  # type: ignore[misc]
    cache_ok = True


@compiles(uint, 'postgresql')
@compiles(uint1, 'postgresql')
@compiles(uint2, 'postgresql')
@compiles(uint4, 'postgresql')
@compiles(uint8, 'postgresql')
def compile_pg_uint(element, compiler, **kwargs):
    return element.__visit_name__
