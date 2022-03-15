import asyncclick as click

__all__ = ['HEX_DEC_INT']


class HexDecIntParamType(click.ParamType):
    name = 'integer'

    def convert(self, value, param, ctx):
        if isinstance(value, int):
            return value

        try:
            if value[:2].lower() == '0x':
                return int(value[2:], 16)
            return int(value, 10)
        except ValueError:
            self.fail(f'{value!r} is not a valid integer', param, ctx)


HEX_DEC_INT = HexDecIntParamType()
