"""Repository for item data access.

Handles all item-related database operations: CRUD, filtering, archiving.
"""

import psycopg
from datetime import datetime

from core.exceptions import StorageError, StorageEntityNotFoundError
from storage.postgres.dtos import ItemRecord, item_record_from_row
from storage.postgres.repositories.base_repository import BaseRepository


class ItemRepository(BaseRepository):
    """Manages item records in the database."""

    def find_by_id(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> ItemRecord | None:
        """Find item by ID (any project).

        Args:
            conn: Database connection
            item_id: Item ID

        Returns:
            ItemRecord or None if not found
        """
        row = self._execute_one(
            conn,
            """
            SELECT id, project_id, type, text, status, source, created_at, updated_at
            FROM item WHERE id = %s LIMIT 1
            """,
            (item_id,),
        )
        return item_record_from_row(row) if row else None

    def find_by_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
        include_archived: bool = False,
    ) -> list[ItemRecord]:
        """Find all items in a project.

        Args:
            conn: Database connection
            project_id: Project ID
            include_archived: Include archived items (default: False)

        Returns:
            List of ItemRecord
        """
        archived_filter = "" if include_archived else "AND status <> 'archived'"
        query = f"""
            SELECT id, project_id, type, text, status, source, created_at, updated_at
            FROM item
            WHERE project_id = %s {archived_filter}
            ORDER BY created_at ASC, id ASC
        """

        rows = self._execute(conn, query, (project_id,))
        return [item_record_from_row(row) for row in rows]

    def insert(
        self,
        conn: psycopg.Connection,
        project_id: str,
        type_: str,
        text: str,
        status: str = "active",
        source: str = "cli",
        created_at: datetime | None = None,
    ) -> ItemRecord:
        """Insert new item.

        Args:
            conn: Database connection
            project_id: Project ID
            type_: Item type (task, note, idea)
            text: Item text
            status: Item status (default: active)
            source: Item source (default: cli)
            created_at: Creation timestamp (default: now)

        Returns:
            Inserted ItemRecord

        Raises:
            StorageError: If insert fails
        """
        created_at = created_at or datetime.now()

        row = self._execute_returning(
            conn,
            """
            INSERT INTO item (project_id, type, text, status, source, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, project_id, type, text, status, source, created_at, updated_at
            """,
            (project_id, type_, text, status, source, created_at, created_at),
        )

        if not row:
            raise StorageError("Failed to insert item")

        return item_record_from_row(row)

    def update(
        self,
        conn: psycopg.Connection,
        item_id: str,
        text: str | None = None,
        type_: str | None = None,
        status: str | None = None,
    ) -> ItemRecord:
        """Update item fields.

        Args:
            conn: Database connection
            item_id: Item ID
            text: New text (if provided)
            type_: New type (if provided)
            status: New status (if provided)

        Returns:
            Updated ItemRecord

        Raises:
            StorageEntityNotFoundError: If item not found
            StorageError: If update fails
        """
        updates = []
        params = []

        if text is not None:
            updates.append("text = %s")
            params.append(text)

        if type_ is not None:
            updates.append("type = %s")
            params.append(type_)

        if status is not None:
            updates.append("status = %s")
            params.append(status)

        if not updates:
            return self.find_by_id(conn, item_id) or None  # No updates

        params.append(datetime.now())
        params.append(item_id)

        set_clause = ", ".join(updates)
        query = f"""
            UPDATE item
            SET {set_clause}, updated_at = %s
            WHERE id = %s
            RETURNING id, project_id, type, text, status, source, created_at, updated_at
        """

        row = self._execute_returning(conn, query, tuple(params))

        if not row:
            raise StorageEntityNotFoundError(f"Item {item_id!r} not found")

        return item_record_from_row(row)

    def delete(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> None:
        """Delete item by ID.

        Args:
            conn: Database connection
            item_id: Item ID

        Raises:
            StorageEntityNotFoundError: If item not found
        """
        rowcount = self._execute_write(
            conn,
            "DELETE FROM item WHERE id = %s",
            (item_id,),
        )

        if rowcount == 0:
            raise StorageEntityNotFoundError(f"Item {item_id!r} not found")

    def archive_items_for_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> int:
        """Archive all items in a project.

        Args:
            conn: Database connection
            project_id: Project ID

        Returns:
            Number of archived items
        """
        rowcount = self._execute_write(
            conn,
            "UPDATE item SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE project_id = %s AND status <> 'archived'",
            (project_id,),
        )
        return rowcount

    def clear_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> int:
        """Delete all items in a project.

        Args:
            conn: Database connection
            project_id: Project ID

        Returns:
            Number of deleted items
        """
        rowcount = self._execute_write(
            conn,
            "DELETE FROM item WHERE project_id = %s",
            (project_id,),
        )
        return rowcount

    def count_in_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
        include_archived: bool = False,
    ) -> int:
        """Count items in project.

        Args:
            conn: Database connection
            project_id: Project ID
            include_archived: Include archived items (default: False)

        Returns:
            Number of items
        """
        archived_filter = "" if include_archived else "AND status <> 'archived'"
        query = f"SELECT COUNT(*) FROM item WHERE project_id = %s {archived_filter}"

        row = self._execute_one(conn, query, (project_id,))
        return row[0] if row else 0
