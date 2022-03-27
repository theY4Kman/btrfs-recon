import dataclasses
from pathlib import Path
from uuid import UUID

from pytest_assert_utils import assert_model_attrs
from pytest_lambda import lambda_fixture

from btrfs_recon.structure import Superblock

PARENT_DIR = Path(__file__).parent
RAW_SUPERBLOCK_PATH = PARENT_DIR / 'superblock.bin'


raw_superblock = lambda_fixture(lambda: RAW_SUPERBLOCK_PATH.read_bytes(), scope='module')

SUPERBLOCK_VALUES = dict(
    fsid=UUID('bba692f7-5be7-4173-bc27-bb3e21644739'),
    bytenr=65536,
    generation=2907003,
    root=257423802368,
    chunk_root=4585107275776,
    log_root=512871186432,
    log_root_transid=0,
    total_bytes=2000407977984,
    bytes_used=1885622980608,
    root_dir_objectid=6,
    num_devices=2,
    sector_size=4096,
    node_size=1013284864,
    leafsize=13,
    stripesize=4096,
    sys_chunk_array_size=97,
    chunk_root_generation=2905409,
    compat_flags=0,
    compat_ro_flags=0,
    incompat_flags=353,
    csum_type=0,
    root_level=1,
    chunk_root_level=1,
    log_root_level=0,
    label='yakbtrfs',
    cache_generation=2907003,
    uuid_tree_generation=2907003,
    metadata_uuid=UUID('00000000-0000-0000-0000-000000000000'),
    magic=b'_BHRfS_M',
    csum=b'\x03\x0f\xe6\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
         b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
)


def test_superblock_parse_correctness(raw_superblock):
    sb = Superblock.parse(raw_superblock)
    assert_model_attrs(sb, SUPERBLOCK_VALUES)


def test_superblock_reversible_parse(raw_superblock):
    expected = raw_superblock
    actual = Superblock.build(Superblock.parse(raw_superblock))
    assert expected == actual


def test_superblock_changes(raw_superblock):
    changed_sb = Superblock.parse(raw_superblock)
    changed_sb.chunk_root_generation = 2906220

    raw_changed = Superblock.build(changed_sb)
    reparsed_sb = Superblock.parse(raw_changed)

    changed_fields = dict(SUPERBLOCK_VALUES)
    del changed_fields['csum']
    changed_fields['chunk_root_generation'] = 2906220
    assert_model_attrs(reparsed_sb, changed_fields)
