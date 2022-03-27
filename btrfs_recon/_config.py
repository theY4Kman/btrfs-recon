import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.resolve()
ALEMBIC_CFG_PATH = PROJECT_ROOT / 'alembic.ini'

DB_SHELL_EXTRA_IMPORTS = [
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

_MODEL_REPR = {s.strip() for s in os.getenv('MODEL_REPR', '').split(',')}
MODEL_REPR_PRETTY = 'pretty' in _MODEL_REPR
MODEL_REPR_ID = 'id' in _MODEL_REPR
