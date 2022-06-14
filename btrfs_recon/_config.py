from pathlib import Path
from typing import Any

from pydantic import AnyUrl, BaseSettings, Field, root_validator

from btrfs_recon.types import ImportItem


class PostgresPsycopgDsn(AnyUrl):
    allowed_schemes = {'postgresql+psycopg'}
    user_required = True


class BtrfsReconSettings(BaseSettings):
    PROJECT_ROOT: Path = Field(Path(__file__).parent.resolve(), const=True)
    ALEMBIC_CFG_PATH: Path = Field(PROJECT_ROOT.default / 'alembic.ini', const=True)

    DATABASE_URL: PostgresPsycopgDsn

    DB_SHELL_EXTRA_IMPORTS: list[ImportItem] = [
        {'sa': 'sqlalchemy'},
        ('sqlalchemy', ('orm', 'func')),
        {'pg': 'sqlalchemy.dialects.postgresql'},
        ('btrfs_recon', ('structure', 'parsing')),
        ('btrfs_recon.persistence', 'fields'),
        ('btrfs_recon.persistence.serializers.registry', '*'),
    ]

    DB_SHELL_SQLPARSE_FORMAT_KWARGS: dict[str, Any] = {
        'reindent_aligned': True,
        'truncate_strings': 500,
    }

    @root_validator(pre=True)
    def _expand_model_repr(cls, values):
        repr_opts = {s.strip() for s in values.get('MODEL_REPR', '').split(',')}
        for opt in repr_opts:
            if opt:
                values[f'MODEL_REPR_{opt.upper()}'] = True
        return values

    MODEL_REPR_PRETTY: bool = False
    MODEL_REPR_ID: bool = False
