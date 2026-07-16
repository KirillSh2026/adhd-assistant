"""Base repository class for all PostgreSQL data access objects.

Provides common functionality: connection management, cursor handling,
error translation, and transaction support.
"""

import psycopg
from typing import Optional

from core.exceptions import StorageError, StorageEntityNotFoundError


class BaseRepository:
    """Base class for all repositories.

    Repositories handle SQL operations and DTO construction. They receive
    a connection as a parameter (managed by UnitOfWork) rather than
    creating their own connections.

    This pattern ensures:
    - Single connection per transaction (no connection duplication)
    - Clear ownership of connection lifecycle (UnitOfWork)
    - Testable (can pass mock connection)
    - Transaction-safe (all repos use same connection within UoW)
    """

    def __init__(self, dsn: str):
        """Initialize repository with database connection string.

        Args:
            dsn: PostgreSQL connection string
        """
        self.dsn = dsn

    def _with_connection(self, fn):
        """Helper: Execute function with a new connection.

        Used by repositories when creating their own connection context
        (for simple operations that don't need coordination).

        Args:
            fn: Callable(connection: psycopg.Connection) -> T

        Returns:
            Result of fn

        Raises:
            StorageError: If connection fails
        """
        try:
            with psycopg.connect(self.dsn) as conn:
                return fn(conn)
        except Exception as e:
            raise StorageError(f"Database error: {str(e)}") from e

    def _execute(
        self,
        conn: psycopg.Connection,
        query: str,
        params: tuple = (),
    ) -> list[tuple]:
        """Execute SELECT query and return rows.

        Args:
            conn: Database connection
            query: SQL query (parameterized)
            params: Query parameters

        Returns:
            List of rows (tuples)

        Raises:
            StorageError: If query fails
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
        except Exception as e:
            raise StorageError(f"Query execution failed: {str(e)}") from e

    def _execute_one(
        self,
        conn: psycopg.Connection,
        query: str,
        params: tuple = (),
    ) -> Optional[tuple]:
        """Execute SELECT query and return first row.

        Args:
            conn: Database connection
            query: SQL query (parameterized)
            params: Query parameters

        Returns:
            First row tuple or None if not found

        Raises:
            StorageError: If query fails
        """
        rows = self._execute(conn, query, params)
        return rows[0] if rows else None

    def _execute_one_required(
        self,
        conn: psycopg.Connection,
        query: str,
        params: tuple = (),
        entity_name: str = "Entity",
    ) -> tuple:
        """Execute SELECT query and return first row (must exist).

        Args:
            conn: Database connection
            query: SQL query (parameterized)
            params: Query parameters
            entity_name: Name of entity for error message

        Returns:
            First row tuple

        Raises:
            StorageEntityNotFoundError: If no rows found
            StorageError: If query fails
        """
        row = self._execute_one(conn, query, params)
        if not row:
            raise StorageEntityNotFoundError(f"{entity_name} not found")
        return row

    def _execute_write(
        self,
        conn: psycopg.Connection,
        query: str,
        params: tuple = (),
    ) -> int:
        """Execute INSERT/UPDATE/DELETE query and return affected row count.

        Args:
            conn: Database connection
            query: SQL query (parameterized)
            params: Query parameters

        Returns:
            Number of rows affected

        Raises:
            StorageError: If query fails
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.rowcount
        except Exception as e:
            raise StorageError(f"Write operation failed: {str(e)}") from e

    def _execute_returning(
        self,
        conn: psycopg.Connection,
        query: str,
        params: tuple = (),
    ) -> Optional[tuple]:
        """Execute INSERT/UPDATE query with RETURNING and return result row.

        Args:
            conn: Database connection
            query: SQL query with RETURNING clause (parameterized)
            params: Query parameters

        Returns:
            Returned row tuple or None

        Raises:
            StorageError: If query fails
        """
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        except Exception as e:
            raise StorageError(f"Write operation failed: {str(e)}") from e

    def _assert_project_id(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> None:
        """Verify that project exists.

        Args:
            conn: Database connection
            project_id: Project ID to verify

        Raises:
            StorageEntityNotFoundError: If project not found
        """
        row = self._execute_one(
            conn,
            "SELECT id FROM project WHERE id = %s LIMIT 1",
            (project_id,),
        )
        if not row:
            raise StorageEntityNotFoundError(f"Project {project_id!r} not found")

    def _assert_item_exists(
        self,
        conn: psycopg.Connection,
        item_id: str,
        project_id: str,
    ) -> None:
        """Verify that item exists and belongs to project.

        Args:
            conn: Database connection
            item_id: Item ID to verify
            project_id: Project ID to verify

        Raises:
            StorageEntityNotFoundError: If item not found or belongs to different project
        """
        row = self._execute_one(
            conn,
            "SELECT id FROM item WHERE id = %s AND project_id = %s LIMIT 1",
            (item_id, project_id),
        )
        if not row:
            raise StorageEntityNotFoundError(
                f"Item {item_id!r} not found in project {project_id!r}"
            )

    def _assert_items_in_project(
        self,
        conn: psycopg.Connection,
        item_ids: list[str],
        project_id: str,
    ) -> None:
        """Verify that all items exist and belong to project.

        Args:
            conn: Database connection
            item_ids: Item IDs to verify
            project_id: Project ID to verify

        Raises:
            StorageEntityNotFoundError: If any item not found or belongs to different project
        """
        if not item_ids:
            return

        placeholders = ",".join(["%s"] * len(item_ids))
        query = f"""
            SELECT COUNT(*) FROM item
            WHERE project_id = %s AND id = ANY(ARRAY[{placeholders}])
        """
        params = (project_id, *item_ids)
        row = self._execute_one(conn, query, params)
        count = row[0] if row else 0

        if count != len(item_ids):
            missing = len(item_ids) - count
            raise StorageEntityNotFoundError(
                f"{missing} of {len(item_ids)} items not found in project {project_id!r}"
            )
