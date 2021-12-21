from pathlib import Path

from btrfs_recon.parsing import parse_fs

# class BtrfsVolume:
#     def __init__(self):

# _Container_str = cs.Container.__str__
#
# def _labeled_container_str(self) -> str:
#     orig_str = _Container_str(self)
#     try:
#         orig_str[:orig_str.index(':')] = self._label
#     except AttributeError:
#         pass
#     return orig_str
#
#
# cs.Container.__str__ = _labeled_container_str
# _Struct_name_registry = {}
#
#
#
#
# def _add_labels_to_structs():
#     for name, value in globals().items():
#         if isinstance(value, Struct):
#             value.subcons.append('_label' / cs.Consname
#
#
# _add_labels_to_structs()

if __name__ == '__main__':
    ssd = Path('/mnt/nas/Disk Image of SSD btrfs (2021-12-02 2142).img')
    nvme = Path('/home/they4kman/BTRFS-IMAGES/Disk Image of nvme0n1 (2021-12-02 2146).img')
    image_1 = Path('/home/they4kman/programming/personal/btrfs-recon/image_1')
    image_2 = Path('/home/they4kman/programming/personal/btrfs-recon/image_2')

    with nvme.open('rb') as nvme_fp, ssd.open('rb') as ssd_fp:
        superblock, tree = parse_fs(nvme_fp, ssd_fp)
        # print(superblock)
        #
        # possible_roots = [
        #     0xabfeaa0000,
        #     0xabf21a0000,
        #     # 0xabc1740000,  # wrong fsid — seems garble
        #     0x898f000000,
        #     0x8980210000,
        #     0x893ab30000,
        #     0x89299d0000,
        #     0x8920ae0000,
        #     0x891a890000,
        #     0x8918570000,
        #     0x8901a10000,
        #     0x743a7b0000,
        #     0x7411c40000,
        #     0x7407090000,
        #     0x58c2a00000,
        #     0x38724f0000,
        #     0x383a1a0000,
        #     0x3836be0000,
        # ]
        # root_items = {}
        # fs_roots = {}
        # for root_physical in reversed(possible_roots):
        #     root = root_items[root_physical] = parse_at(fp, root_physical, TreeNode)
        #     item_types = {f'{item.key.ty}({item.key.objectid})' for item in root['items']}
        #     print()
        #     print(
        #         f'[gen={root.header.generation:>7}]'
        #         f'[nritems={root.header.nritems:>3}] '
        #         f'logical {root.header.bytenr:>10x} => physical {root_physical:>10x} '
        #         f'{{ {", ".join(item_types)} }}'
        #     )
        #
        #     fs_root_item = next(
        #         item
        #         for item in root['items']
        #         if item.key.ty == KeyType.RootItem and item.key.objectid == ObjectId.FsTree
        #     )
        #     fs_root_phys = tree.offset(fs_root_item.data.bytenr)
        #     fs_root_header = parse_at(fp, fs_root_phys, Header)
        #
        #     if fs_root_header.nritems > 200:
        #         fs_root = fs_root_header
        #         print(fs_root)
        #     else:
        #         fs_root = parse_at(fp, fs_root_phys, TreeNode)
        #         walk_fs_tree(fs_root)
        #
        #     fs_roots[root_physical] = fs_root
        #
        #     print()
        #     print()

        #XXX######################################################################################
        # expected_fsid = uuid.UUID('bba692f7-5be7-4173-bc27-bb3e21644739')
        # valid_locs = []
        # # base = 0x74024E4000
        # invalid_locs: set[int] = set()
        #
        # invalid_locs_path = Path('invalid_locs.txt')
        # if invalid_locs_path.exists():
        #     invalid_locs.update(map(int, invalid_locs_path.read_text().strip().splitlines()))
        #
        # def _record_invalid_loc(loc):
        #     invalid_locs.add(loc)
        #     with invalid_locs_path.open('a') as fp:
        #         fp.write(f'{loc}\n')
        #
        # chunk_pbar = tqdm(sorted(tree.all_intervals, key=lambda ival: ival.begin), unit='chunk')
        # for ival in chunk_pbar:
        #     ival: Interval
        #     base = ival.data
        #     end = base + ival.length()
        #
        #     for loc in tqdm(range(base, end + 1, superblock.sector_size), unit='sector', position=1):
        #         if loc in invalid_locs:
        #             continue
        #
        #         try:
        #             header = parse_at(fp, loc, Header)
        #         except cs.ValidationError:
        #             _record_invalid_loc(loc)
        #             continue
        #         else:
        #             if header.fsid != expected_fsid:
        #                 _record_invalid_loc(loc)
        #                 continue
        #
        #         try:
        #             node = parse_at(fp, loc, TreeNode)
        #         except cs.ValidationError:
        #             _record_invalid_loc(loc)
        #             continue
        #
        #         chunk_pbar.write(str(node))
        #         valid_locs.append(loc)
        #         chunk_pbar.write('')
        #         chunk_pbar.write('')
        #
        # print()
        # print()
        # print('Valid locs:')
        # print('\n'.join(hex(v) for v in valid_locs))
        # print()
        # print('# valid locs:', len(valid_locs))
        #XXX######################################################################################

    print()
    print()
