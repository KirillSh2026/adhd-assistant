"""Repository for item merge/history data access.

Handles all merge-related database operations: recording merges,
tracking merge history, reverting merges.
"""

import psycopg
from datetime import datetime
from typing import Optional

from core.exceptions import StorageError, StorageEntityNotFoundError
from storage.postgres.dtos import MergeRecord, merge_record_from_row
from storage.postgres.repositories.base_repository import BaseRepository


class MergeRepository(BaseRepository):
    """Manages item merge records and merge history."""

    def find_by_id(
        self,
        conn: psycopg.Connection,
        merge_id: str,
    ) -> MergeRecord | None:
        """Find merge record by ID.

        Args:
            conn: Database connection
            merge_id: Merge record ID

        Returns:
            MergeRecord or None if not found
        """
        row = self._execute_one(
            conn,
            """
            SELECT id, project_id, source_item_id, target_item_id, merge_reason,
                   merged_by, snapshot_data, status, created_at, reverted_at
            FROM item_merge WHERE id = %s LIMIT 1
            """,
            (merge_id,),
        )
        return merge_record_from_row(row) if row else None

    def list_for_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
        include_reverted: bool = False,
        limit: int = 100,
    ) -> list[MergeRecord]:
        """List merge records for a project.

        Args:
            conn: Database connection
            project_id: Project ID
            include_reverted: Include reverted merges (default: False)
            limit: Maximum records to return

        Returns:
            List of MergeRecord (most recent first)
        """
        status_filter = "" if include_reverted else "AND status = 'completed'"
        query = f"""
            SELECT id, project_id, source_item_id, target_item_id, merge_reason,
                   merged_by, snapshot_data, status, created_at, reverted_at
            FROM item_merge
            WHERE project_id = %s {status_filter}
            ORDER BY created_at DESC
            LIMIT %s
        """

        rows = self._execute(conn, query, (project_id, limit))
        return [merge_record_from_row(row) for row in rows]

    def find_latest_for_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> MergeRecord | None:
        """Find latest merge record for a project.

        Args:
            conn: Database connection
            project_id: Project ID

        Returns:
            MergeRecord or None if no merges exist
        """
        row = self._execute_one(
            conn,
            """
            SELECT id, project_id, source_item_id, target_item_id, merge_reason,
                   merged_by, snapshot_data, status, created_at, reverted_at
            FROM item_merge
            WHERE project_id = %s AND status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """,
            (project_id,),
        )
        return merge_record_from_row(row) if row else None

    def record_merge(
        self,
        conn: psycopg.Connection,
        project_id: str,
        source_item_id: str,
        target_item_id: str,
        merge_reason: str,
        snapshot_data: dict | None = None,
        merged_by: str = "cli",
    ) -> MergeRecord:
        """Record a merge operation.

        Args:
            conn: Database connection
            project_id: Project ID
            source_item_id: Item being merged from
            target_item_id: Item being merged into
            merge_reason: Reason for merge
            snapshot_data: JSON snapshot of merged items (for rollback)
            merged_by: User/source that performed merge

        Returns:
            Created MergeRecord

        Raises:
            StorageError: If insert fails
        """
        from psycopg.types.json import Jsonb

        row = self._execute_returning(
            conn,
            """
            INSERT INTO item_merge
                (project_id, source_item_id, target_item_id, merge_reason,
                 merged_by, snapshot_data, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'completed', CURRENT_TIMESTAMP)
            RETURNING id, project_id, source_item_id, target_item_id, merge_reason,
                      merged_by, snapshot_data, status, created_at, reverted_at
            """,
            (
                project_id,
                source_item_id,
                target_item_id,
                merge_reason,
                merged_by,
                Jsonb(snapshot_data) if snapshot_data else None,
            ),
        )

        if not row:
            raise StorageError("Failed to record merge")

        return merge_record_from_row(row)

    def mark_reverted(
        self,
        conn: psycopg.Connection,
        merge_id: str,
    ) -> MergeRecord:
        """Mark a merge as reverted.

        Args:
            conn: Database connection
            merge_id: Merge record ID

        Returns:
            Updated MergeRecord

        Raises:
            StorageEntityNotFoundError: If merge not found
            StorageError: If update fails
        """
        row = self._execute_returning(
            conn,
            """
            UPDATE item_merge
            SET status = 'reverted', reverted_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, project_id, source_item_id, target_item_id, merge_reason,
                      merged_by, snapshot_data, status, created_at, reverted_at
            """,
            (merge_id,),
        )

        if not row:
            raise StorageEntityNotFoundError(f"Merge {merge_id!r} not found")

        return merge_record_from_row(row)

    def find_merges_involving_item(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> list[MergeRecord]:
        """Find all merges involving an item (as source or target).

        Args:
            conn: Database connection
            item_id: Item ID

        Returns:
            List of MergeRecord (most recent first)
        """
        rows = self._execute(
            conn,
            """
            SELECT id, project_id, source_item_id, target_item_id, merge_reason,
                   merged_by, snapshot_data, status, created_at, reverted_at
            FROM item_merge
            WHERE source_item_id = %s OR target_item_id = %s
            ORDER BY created_at DESC
            """,
            (item_id, item_id),
        )
        return [merge_record_from_row(row) for row in rows]

    def delete_merges_for_item(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> int:
        """Delete all merge records involving an item.

        Args:
            conn: Database connection
            item_id: Item ID

        Returns:
            Number of deleted merge records
        """
        rowcount = self._execute_write(
            conn,
            "DELETE FROM item_merge WHERE source_item_id = %s OR target_item_id = %s",
            (item_id, item_id),
        )
        return rowcount

    def count_for_project(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> int:
        """Count merge records for a project.

        Args:
            conn: Database connection
            project_id: Project ID

        Returns:
            Number of merge records
        """
        row = self._execute_one(
            conn,
            "SELECT COUNT(*) FROM item_merge WHERE project_id = %s",
            (project_id,),
        )
        return row[0] if row else 0
