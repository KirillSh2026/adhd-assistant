"""PostgreSQL storage implementation with repository pattern.

Architecture layers:
1. DTOs (dtos.py) - Typed data transfer objects for DB records
2. Config (config.py) - PostgreSQL configuration management
3. Repositories (repositories/) - Data access layer
   - BaseRepository - Common functionality
   - ProjectRepository - Project operations
   - ItemRepository - Item CRUD
   - RelationRepository - Relations/dependencies
   - MergeRepository - Merge history
4. Domain Rules (domain_rules.py) - Business logic validation
5. Snapshot Service (snapshot_service.py) - Merge rollback support
6. Unit of Work (unit_of_work.py) - Transaction coordination
7. PostgresStorage (../postgres_storage.py) - Main entry point (refactored)

Key Principles:
- Repositories work with DTOs, not domain models
- All SQL queries isolated in repositories
- UnitOfWork manages connection lifecycle and transactions
- Domain rules separate from SQL
- No connection duplication
- 100% backwards compatible with existing interface
"""

from storage.postgres.config import PostgresConfig
from storage.postgres.dtos import (
    ProjectRecord,
    ItemRecord,
    RelationRecord,
    MergeRecord,
    RelationSuggestionRecord,
)
from storage.postgres.repositories import (
    BaseRepository,
    ProjectRepository,
    ItemRepository,
    RelationRepository,
    MergeRepository,
)

__all__ = [
    "PostgresConfig",
    "ProjectRecord",
    "ItemRecord",
    "RelationRecord",
    "MergeRecord",
    "RelationSuggestionRecord",
    "BaseRepository",
    "ProjectRepository",
    "ItemRepository",
    "RelationRepository",
    "MergeRepository",
]
