from pathlib import Path
from typing import Collection, Literal

DevId = int
ImagePath = str | Path
PhysicalAddress = int


AliasedItems = dict[str, str]
ImportAtom = str | AliasedItems
FromModuleSingleItem = tuple[str, ImportAtom]
FromModuleMultipleItems = tuple[str, Collection[ImportAtom]]
FromModuleAllItems = tuple[str, Literal["*"]]
ImportModuleItem = ImportAtom
ImportItem = FromModuleSingleItem | FromModuleMultipleItems | FromModuleAllItems | ImportModuleItem
