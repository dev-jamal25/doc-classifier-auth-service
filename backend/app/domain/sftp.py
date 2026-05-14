from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class FileInfo:
    name: str
    path: str
    size: int
    mtime: datetime
