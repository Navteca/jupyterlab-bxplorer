from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Union, Dict, Any, List


@dataclass(frozen=True, order=True)
class ChonkyFileData:
    id: str
    name: str
    ext: Optional[str] = None
    isDir: Optional[bool] = None
    isHidden: Optional[bool] = None
    isSymlink: Optional[bool] = None
    isEncrypted: Optional[bool] = None
    openable: Optional[bool] = None
    selectable: Optional[bool] = None
    draggable: Optional[bool] = None
    droppable: Optional[bool] = None
    dndOpenable: Optional[bool] = None
    size: Optional[int] = None
    modDate: Optional[Union[str, datetime]] = None
    childrenCount: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    thumbnailUrl: Optional[str] = None
    folderChainIcon: Optional[str] = None
    additionalInfo: Optional[List[Dict[str, str]]] = None

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
