import sqlalchemy as sa

__all__ = [
    'uint1',
    'uint2',
    'uint4',
    'uint8',
]


class uint(sa.TypeDecorator):
    impl = sa.Integer


class uint1(uint):
    __visit_name__ = 'uint1'


class uint2(uint):
    __visit_name__ = 'uint2'


class uint4(uint):
    __visit_name__ = 'uint4'


class uint8(uint):
    __visit_name__ = 'uint8'
