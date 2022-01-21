from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.resolve()
ALEMBIC_CFG_PATH = PROJECT_ROOT / 'alembic.ini'

DB_SHELL_EXTRA_IMPORTS = [
    {'sa': 'sqlalchemy'},
    ('sqlalchemy', 'orm'),
    ('btrfs_recon', ('structure',)),
    ('btrfs_recon.persistence.serializers.registry', '*'),
]

DB_SHELL_SQLPARSE_FORMAT_KWARGS: dict[str, Any] = {
    'reindent_aligned': True,
    'truncate_strings': 500,
}
