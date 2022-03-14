from typing import Any

import psycopg
import sqlalchemy as sa
from psycopg import postgres
from psycopg.types import TypeInfo
from psycopg.types.numeric import _NumberDumper, IntLoader
from sqlalchemy.dialects.postgresql.psycopg import _PGInteger
from sqlalchemy.ext.compiler import compiles

__all__ = [
    'uint1',
    'uint2',
    'uint4',
    'uint8',
]


def init_dbapi_types(dbapi_conn: psycopg.Connection):
    for typename in 'uint1', 'uint2', 'uint4', 'uint8':
        t = TypeInfo.fetch(dbapi_conn, typename)
        if t is None:
            raise RuntimeError(
                f'Unable to fetch {typename} type from Postgres. '
                f'Has the pguint extension been installed?'
            )

        class UintDumper(_NumberDumper):
            oid = t.oid

        postgres.adapters.register_dumper(int, UintDumper)
        postgres.adapters.register_loader(t.oid, IntLoader)


class PGUnsignedInteger(_PGInteger):
    render_bind_cast = False


class uint(sa.TypeDecorator):
    impl = PGUnsignedInteger

    def bind_expression(self, bindparam: Any) -> Any:
        return sa.cast(bindparam, self.__class__)

    # TODO: these fields should coerce to Python ints!


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
