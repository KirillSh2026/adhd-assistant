from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Item:
    id: str
    type: str
    project_id: str | None
    parent_id: str | None

    text: str

    tags: list[str] = field(default_factory=list)

    source: str = "cli"

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)