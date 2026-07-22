from __future__ import annotations

from core.exceptions import StorageError


class PostgresConfig:
    def __init__(self, dsn: str, project_name: str = "Inbox"):
        if not dsn or not dsn.strip():
            raise ValueError("DSN")
        self.dsn = dsn.strip()
        if not project_name or not project_name.strip():
            raise ValueError("project_name")
        self.project_name = project_name.strip()
