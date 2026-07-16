"""Repository for project data access.

Handles all project-related database operations.
"""

import psycopg

from storage.postgres.dtos import ProjectRecord, project_record_from_row
from storage.postgres.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository):
    """Manages project records in the database."""

    def find_by_name(
        self,
        conn: psycopg.Connection,
        name: str,
    ) -> ProjectRecord | None:
        """Find project by name.

        Args:
            conn: Database connection
            name: Project name

        Returns:
            ProjectRecord or None if not found
        """
        row = self._execute_one(
            conn,
            "SELECT id, name, description, status, created_at, updated_at FROM project WHERE name = %s LIMIT 1",
            (name,),
        )
        return project_record_from_row(row) if row else None

    def find_by_id(
        self,
        conn: psycopg.Connection,
        project_id: str,
    ) -> ProjectRecord | None:
        """Find project by ID.

        Args:
            conn: Database connection
            project_id: Project ID

        Returns:
            ProjectRecord or None if not found
        """
        row = self._execute_one(
            conn,
            "SELECT id, name, description, status, created_at, updated_at FROM project WHERE id = %s LIMIT 1",
            (project_id,),
        )
        return project_record_from_row(row) if row else None

    def find_or_create(
        self,
        conn: psycopg.Connection,
        name: str,
        description: str = "Created by CLI storage backend",
    ) -> ProjectRecord:
        """Find project by name or create if not exists.

        Args:
            conn: Database connection
            name: Project name
            description: Project description (used only if creating)

        Returns:
            ProjectRecord (existing or newly created)

        Raises:
            StorageError: If database operation fails
        """
        existing = self.find_by_name(conn, name)
        if existing:
            return existing

        row = self._execute_returning(
            conn,
            """
            INSERT INTO project (name, description, status, created_at, updated_at)
            VALUES (%s, %s, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id, name, description, status, created_at, updated_at
            """,
            (name, description),
        )

        if not row:
            raise StorageError("Failed to create project")

        return project_record_from_row(row)

    def list_all(
        self,
        conn: psycopg.Connection,
    ) -> list[ProjectRecord]:
        """List all projects.

        Args:
            conn: Database connection

        Returns:
            List of ProjectRecord
        """
        rows = self._execute(
            conn,
            "SELECT id, name, description, status, created_at, updated_at FROM project ORDER BY created_at ASC",
        )
        return [project_record_from_row(row) for row in rows]


# Add missing import at top
from core.exceptions import StorageError
