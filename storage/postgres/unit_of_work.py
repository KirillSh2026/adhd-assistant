"""Unit of Work pattern implementation for PostgreSQL storage.

UnitOfWork coordinates:
1. Single database connection lifecycle
2. Transaction boundaries (commit/rollback)
3. Multiple repositories working on same connection
4. Connection pooling (future)

This ensures:
- One connection per logical operation (not per repository call)
- All repositories see same connection and transaction state
- Automatic rollback on error
- No connection leaks
- Testable (can pass mock connection)
"""

import psycopg
from contextlib import contextmanager
from typing import Generator

from core.exceptions import StorageError
from storage.postgres.config import PostgresConfig
from storage.postgres.repositories import (
    ProjectRepository,
    ItemRepository,
    RelationRepository,
    MergeRepository,
)


class UnitOfWork:
    """Manages database connection and repositories for a transaction.

    Usage:
        config = PostgresConfig.from_settings(settings)
        with UnitOfWork(config) as uow:
            items = uow.items.find_by_project(conn, project_id)
            uow.relations.insert_suggestion(conn, from_id, to_id, rel_type)
            # Automatically commits on success, rollback on error
    """

    def __init__(self, config: PostgresConfig):
        """Initialize UnitOfWork.

        Args:
            config: PostgreSQL configuration
        """
        self.config = config
        self.connection: psycopg.Connection | None = None

        # Initialize repositories
        self.projects = ProjectRepository(config.dsn)
        self.items = ItemRepository(config.dsn)
        self.relations = RelationRepository(config.dsn)
        self.merges = MergeRepository(config.dsn)

    def __enter__(self) -> "UnitOfWork":
        """Enter context manager: acquire connection."""
        try:
            self.connection = psycopg.connect(self.config.dsn)
            return self
        except Exception as e:
            raise StorageError(f"Failed to connect to database: {str(e)}") from e

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager: commit or rollback connection."""
        if self.connection is None:
            return

        try:
            if exc_type is None:
                # No exception: commit
                self.connection.commit()
            else:
                # Exception occurred: rollback
                self.connection.rollback()
        except Exception as e:
            # Force close on commit/rollback error
            try:
                self.connection.close()
            except Exception:
                pass
            raise StorageError(f"Failed to finalize transaction: {str(e)}") from e
        finally:
            # Always close connection
            try:
                if self.connection:
                    self.connection.close()
            except Exception:
                pass
            self.connection = None

    @contextmanager
    def transaction(self) -> Generator[psycopg.Connection, None, None]:
        """Context manager for explicit transaction control.

        Usage:
            with uow.transaction() as conn:
                uow.items.insert(conn, ...)
                uow.relations.confirm(conn, ...)
                # Auto commit on exit, rollback on error

        Yields:
            Database connection (same as self.connection)

        Raises:
            StorageError: If no active connection
        """
        if self.connection is None:
            raise StorageError("No active database connection")

        try:
            # Start explicit transaction
            self.connection.transaction().__enter__()
            yield self.connection
        except Exception as e:
            # Transaction will auto-rollback
            raise e

    def ensure_project_id(self, project_name: str) -> str:
        """Get or create project ID.

        Args:
            project_name: Project name (usually from config)

        Returns:
            Project ID

        Raises:
            StorageError: If connection not active
        """
        if self.connection is None:
            raise StorageError("No active database connection")

        project = self.projects.find_or_create(
            self.connection,
            project_name,
        )
        return project.id

    def __repr__(self) -> str:
        """Return string representation."""
        status = "active" if self.connection else "inactive"
        return f"UnitOfWork({self.config.project_name!r}, {status})"
