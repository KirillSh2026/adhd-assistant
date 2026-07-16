"""Repository for item relationship/dependency data access.

Handles all relation-related database operations: suggestions, confirmations,
linking, querying.
"""

import psycopg
from datetime import datetime

from core.exceptions import StorageError, StorageEntityNotFoundError
from storage.postgres.dtos import RelationRecord, relation_record_from_row
from storage.postgres.repositories.base_repository import BaseRepository


class RelationRepository(BaseRepository):
    """Manages item relationship records (item_dependency table)."""

    def find_by_id(
        self,
        conn: psycopg.Connection,
        relation_id: str,
    ) -> RelationRecord | None:
        """Find relation by ID.

        Args:
            conn: Database connection
            relation_id: Relation ID

        Returns:
            RelationRecord or None if not found
        """
        row = self._execute_one(
            conn,
            """
            SELECT id, from_item_id, to_item_id, relationship_type, reason,
                   is_confirmed, confirmed_at, created_at, updated_at
            FROM item_dependency WHERE id = %s LIMIT 1
            """,
            (relation_id,),
        )
        return relation_record_from_row(row) if row else None

    def find_relation(
        self,
        conn: psycopg.Connection,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
    ) -> RelationRecord | None:
        """Find relation between two items of specific type.

        Args:
            conn: Database connection
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship

        Returns:
            RelationRecord or None if not found
        """
        row = self._execute_one(
            conn,
            """
            SELECT id, from_item_id, to_item_id, relationship_type, reason,
                   is_confirmed, confirmed_at, created_at, updated_at
            FROM item_dependency
            WHERE from_item_id = %s AND to_item_id = %s AND relationship_type = %s
            LIMIT 1
            """,
            (from_item_id, to_item_id, relationship_type),
        )
        return relation_record_from_row(row) if row else None

    def list_for_item(
        self,
        conn: psycopg.Connection,
        item_id: str,
        confirmed_only: bool = False,
    ) -> list[RelationRecord]:
        """List all relations involving an item (as source or target).

        Args:
            conn: Database connection
            item_id: Item ID
            confirmed_only: Only return confirmed relations (default: False)

        Returns:
            List of RelationRecord
        """
        confirmed_filter = "AND is_confirmed = TRUE" if confirmed_only else ""
        query = f"""
            SELECT id, from_item_id, to_item_id, relationship_type, reason,
                   is_confirmed, confirmed_at, created_at, updated_at
            FROM item_dependency
            WHERE (from_item_id = %s OR to_item_id = %s) {confirmed_filter}
            ORDER BY created_at ASC
        """

        rows = self._execute(conn, query, (item_id, item_id))
        return [relation_record_from_row(row) for row in rows]

    def list_all(
        self,
        conn: psycopg.Connection,
        confirmed_only: bool = False,
    ) -> list[RelationRecord]:
        """List all relations in database.

        Args:
            conn: Database connection
            confirmed_only: Only return confirmed relations (default: False)

        Returns:
            List of RelationRecord
        """
        confirmed_filter = "WHERE is_confirmed = TRUE" if confirmed_only else ""
        query = f"""
            SELECT id, from_item_id, to_item_id, relationship_type, reason,
                   is_confirmed, confirmed_at, created_at, updated_at
            FROM item_dependency {confirmed_filter}
            ORDER BY created_at ASC
        """

        rows = self._execute(conn, query)
        return [relation_record_from_row(row) for row in rows]

    def insert_suggestion(
        self,
        conn: psycopg.Connection,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str | None = None,
    ) -> RelationRecord:
        """Insert new relation suggestion (unconfirmed).

        Args:
            conn: Database connection
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship
            reason: Reason for suggestion

        Returns:
            Inserted RelationRecord

        Raises:
            StorageError: If insert fails
        """
        row = self._execute_returning(
            conn,
            """
            INSERT INTO item_dependency
                (from_item_id, to_item_id, relationship_type, reason, is_confirmed, created_at, updated_at)
            VALUES (%s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (from_item_id, to_item_id, relationship_type)
            DO UPDATE SET
                reason = EXCLUDED.reason,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, from_item_id, to_item_id, relationship_type, reason,
                      is_confirmed, confirmed_at, created_at, updated_at
            """,
            (from_item_id, to_item_id, relationship_type, reason),
        )

        if not row:
            raise StorageError("Failed to insert relation suggestion")

        return relation_record_from_row(row)

    def upsert_relation(
        self,
        conn: psycopg.Connection,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
        reason: str | None = None,
        is_confirmed: bool = False,
    ) -> RelationRecord:
        """Insert or update relation.

        Args:
            conn: Database connection
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship
            reason: Relation reason/description
            is_confirmed: Whether relation is confirmed

        Returns:
            Inserted or updated RelationRecord

        Raises:
            StorageError: If operation fails
        """
        row = self._execute_returning(
            conn,
            """
            INSERT INTO item_dependency
                (from_item_id, to_item_id, relationship_type, reason, is_confirmed,
                 confirmed_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s,
                    CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (from_item_id, to_item_id, relationship_type)
            DO UPDATE SET
                reason = EXCLUDED.reason,
                is_confirmed = item_dependency.is_confirmed OR EXCLUDED.is_confirmed,
                confirmed_at = CASE
                    WHEN item_dependency.is_confirmed OR EXCLUDED.is_confirmed
                        THEN COALESCE(item_dependency.confirmed_at, CURRENT_TIMESTAMP)
                    ELSE item_dependency.confirmed_at
                END,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id, from_item_id, to_item_id, relationship_type, reason,
                      is_confirmed, confirmed_at, created_at, updated_at
            """,
            (from_item_id, to_item_id, relationship_type, reason, is_confirmed, is_confirmed),
        )

        if not row:
            raise StorageError("Failed to upsert relation")

        return relation_record_from_row(row)

    def confirm(
        self,
        conn: psycopg.Connection,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
    ) -> RelationRecord:
        """Confirm an unconfirmed relation suggestion.

        Args:
            conn: Database connection
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship

        Returns:
            Updated RelationRecord

        Raises:
            StorageEntityNotFoundError: If relation not found
            StorageError: If update fails
        """
        row = self._execute_returning(
            conn,
            """
            UPDATE item_dependency
            SET is_confirmed = TRUE,
                confirmed_at = COALESCE(confirmed_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP
            WHERE from_item_id = %s AND to_item_id = %s AND relationship_type = %s
            RETURNING id, from_item_id, to_item_id, relationship_type, reason,
                      is_confirmed, confirmed_at, created_at, updated_at
            """,
            (from_item_id, to_item_id, relationship_type),
        )

        if not row:
            raise StorageEntityNotFoundError("Relation not found")

        return relation_record_from_row(row)

    def reject_suggestion(
        self,
        conn: psycopg.Connection,
        from_item_id: str,
        to_item_id: str,
        relationship_type: str,
    ) -> None:
        """Reject an unconfirmed relation suggestion (delete it).

        Args:
            conn: Database connection
            from_item_id: Source item ID
            to_item_id: Target item ID
            relationship_type: Type of relationship

        Raises:
            StorageEntityNotFoundError: If unconfirmed suggestion not found
        """
        rowcount = self._execute_write(
            conn,
            """
            DELETE FROM item_dependency
            WHERE from_item_id = %s AND to_item_id = %s AND relationship_type = %s
                  AND is_confirmed = FALSE
            """,
            (from_item_id, to_item_id, relationship_type),
        )

        if rowcount == 0:
            raise StorageEntityNotFoundError("Unconfirmed relation suggestion not found")

    def delete_for_item(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> int:
        """Delete all relations involving an item.

        Args:
            conn: Database connection
            item_id: Item ID

        Returns:
            Number of deleted relations
        """
        rowcount = self._execute_write(
            conn,
            "DELETE FROM item_dependency WHERE from_item_id = %s OR to_item_id = %s",
            (item_id, item_id),
        )
        return rowcount

    def count_for_item(
        self,
        conn: psycopg.Connection,
        item_id: str,
    ) -> int:
        """Count relations involving an item.

        Args:
            conn: Database connection
            item_id: Item ID

        Returns:
            Number of relations
        """
        row = self._execute_one(
            conn,
            "SELECT COUNT(*) FROM item_dependency WHERE from_item_id = %s OR to_item_id = %s",
            (item_id, item_id),
        )
        return row[0] if row else 0
