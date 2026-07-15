from __future__ import annotations

from datetime import datetime

import psycopg

from models.item import Item


class PostgresStorage:
    def __init__(self, dsn: str, project_name: str = "Inbox"):
        self.dsn = dsn
        self.project_name = project_name

    def _ensure_project_id(self, conn: psycopg.Connection) -> str:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM project WHERE name = %s LIMIT 1", (self.project_name,))
            row = cur.fetchone()
            if row:
                return str(row[0])

            cur.execute(
                """
                INSERT INTO project (name, description, status)
                VALUES (%s, %s, 'active')
                RETURNING id
                """,
                (self.project_name, "Created by CLI storage backend"),
            )
            created = cur.fetchone()
            if not created:
                raise RuntimeError("Failed to create default project")
            return str(created[0])

    def load_items(self) -> list[Item]:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        type,
                        text,
                        to_char(created_at, 'YYYY-MM-DD HH24:MI:SS') AS datetime
                    FROM item
                    WHERE project_id = %s
                    ORDER BY created_at ASC, id ASC
                    """,
                    (project_id,),
                )
                rows = cur.fetchall()
        return [Item(type=row[0], text=row[1], datetime=row[2]) for row in rows]

    def add_item(self, item: Item) -> None:
        created_at = datetime.strptime(item.datetime, "%Y-%m-%d %H:%M:%S") if item.datetime else datetime.now()
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO item (project_id, type, text, source, created_at, updated_at)
                    VALUES (%s, %s, %s, 'cli', %s, %s)
                    """,
                    (project_id, item.type, item.text, created_at, created_at),
                )
            conn.commit()

    def clear_items(self) -> None:
        with psycopg.connect(self.dsn) as conn:
            project_id = self._ensure_project_id(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM item WHERE project_id = %s", (project_id,))
            conn.commit()
