"""PostgreSQL storage configuration.

Reads from central settings and provides configuration to storage layer.
This ensures a single source of truth for database connection and project details.
"""

from config.settings import AppSettings


class PostgresConfig:
    """Configuration for PostgreSQL storage backend.

    This class decouples storage from settings, making it easier to test
    and configure. It validates configuration on creation.
    """

    def __init__(
        self,
        dsn: str,
        project_name: str = "Inbox",
    ):
        """Initialize PostgreSQL configuration.

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://...")
            project_name: Project name to use for isolation (default: "Inbox")

        Raises:
            ValueError: If dsn is empty or invalid
        """
        if not dsn or not dsn.strip():
            raise ValueError("PostgreSQL DSN (database_url) is required")

        if not project_name or not project_name.strip():
            raise ValueError("project_name is required")

        self.dsn = dsn.strip()
        self.project_name = project_name.strip()

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "PostgresConfig":
        """Create PostgresConfig from application settings.

        Args:
            settings: Application settings (pydantic-settings instance)

        Returns:
            PostgresConfig instance

        Raises:
            ValueError: If required settings are missing or invalid
        """
        return cls(
            dsn=settings.database_url,
            project_name=settings.adhd_project_name,
        )

    def __repr__(self) -> str:
        """Return string representation (without exposing DSN)."""
        return f"PostgresConfig(project_name={self.project_name!r})"
