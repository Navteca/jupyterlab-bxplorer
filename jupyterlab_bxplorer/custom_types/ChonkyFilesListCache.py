from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from .ChonkyFileData import ChonkyFileData

@dataclass
class ChonkyFileListCache:
    expires_on: datetime = datetime(1955, 5, 10)
    files_list: List[Dict[str, Any]] = field(default_factory=lambda: [ChonkyFileData(id='', name='').as_dict()])