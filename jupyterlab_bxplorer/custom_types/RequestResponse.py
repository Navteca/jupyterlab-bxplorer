from json import loads
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any


@dataclass
class Error:
    code: Optional[int] = None
    message: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    def as_json(self) -> Dict[str, Any]:
        data = asdict(self)
        data_cleaned = str({k: v for k, v in data.items() if v is not None})
        return loads(data_cleaned)


@dataclass(order=True)
class RequestResponse:
    status_code: Optional[int] = None
    data: Optional[str] = None
    error: Error = field(default_factory=Error)


    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}


    def as_json(self) -> Dict[str, Any]:
        data = asdict(self)
        data_cleaned = str({k: v for k, v in data.items() if v is not None})
        return loads(data_cleaned)
