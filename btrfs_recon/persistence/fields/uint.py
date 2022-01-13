import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

__all__ = [
    'uint1',
    'uint2',
    'uint4',
    'uint8',
]


class uint(sa.TypeDecorator):
    impl = sa.Integer


class uint1(uint):
    __visit_name__ = 'uint1'  # type: ignore[misc]


class uint2(uint):
    __visit_name__ = 'uint2'  # type: ignore[misc]


class uint4(uint):
    __visit_name__ = 'uint4'  # type: ignore[misc]


class uint8(uint):
    __visit_name__ = 'uint8'  # type: ignore[misc]


@compiles(uint, 'postgresql')
@compiles(uint1, 'postgresql')
@compiles(uint2, 'postgresql')
@compiles(uint4, 'postgresql')
@compiles(uint8, 'postgresql')
def compile_pg_uint(element, compiler, **kwargs):
    return element.__visit_name__
