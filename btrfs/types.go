package btrfs

import (
	"encoding/binary"
	uuidlib "github.com/google/uuid"
)

type char byte
type u8 uint8
type u16 uint16
type u32 uint32
type u64 uint64

type UUID struct {
	uuidlib.UUID
}

func (uuid UUID) Unpack(buf []byte, order binary.ByteOrder) ([]byte, error) {
	err := uuid.UnmarshalBinary(buf[:BTRFS_UUID_SIZE])
	if err != nil {
		return nil, err
	}
	return buf[BTRFS_UUID_SIZE:], nil
}

type Superblock struct {
	csum   [BTRFS_CSUM_SIZE]u8
	fsid   UUID
	bytenr u64
	flags  u64
	magic  string `struct:"char[0x8]"`
}

/**
struct btrfs_super_block {
  u8 csum[BTRFS_CSUM_SIZE];
  u128 fsid [[format("format_uuid_u128")]];
  /// Physical address of this block
  u64 bytenr;
  u64 flags;
  char magic[0x8];
  u64 generation;
  /// Logical address of the root tree root
  u64 root;
  /// Logical address of the chunk tree root
  btrfs_tree_node *chunk_root : u64;
  /// Logical address of the log tree root
  u64 log_root;
  u64 log_root_transid;
  u64 total_bytes;
  u64 bytes_used;
  u64 root_dir_objectid;
  u64 num_devices;
  u32 sector_size;
  u32 node_size;
  /// Unused and must be equal to `nodesize`
  u32 leafsize;
  u32 stripesize;
  u32 sys_chunk_array_size;
  u64 chunk_root_generation;
  u64 compat_flags;
  u64 compat_ro_flags;
  u64 incompat_flags;
  u16 csum_type;
  u8 root_level;
  u8 chunk_root_level;
  u8 log_root_level;
  btrfs_dev_item dev_item;
  char label[BTRFS_LABEL_SIZE];
  u64 cache_generation;
  u64 uuid_tree_generation;
  u128 metadata_uuid [[format("format_uuid_u128")]];
  /// Future expansion
  u64 _reserved[28] [[hidden]];
  union_sys_chunk sys_chunks;
//  btrfs_root_backup root_backups[4];
};
*/
