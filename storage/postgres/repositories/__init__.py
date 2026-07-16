"""PostgreSQL repository layer.

Repositories provide a data access abstraction for specific entities:
- ProjectRepository: Project management
- ItemRepository: Item CRUD operations
- RelationRepository: Relationship/dependency management
- MergeRepository: Merge history and tracking

Each repository:
- Takes a connection as a parameter (managed by UnitOfWork)
- Returns and accepts typed DTOs
- Handles all SQL queries for its entity
- Provides high-level operations matching business needs

This pattern ensures:
- Single Responsibility Principle (each repo handles one entity type)
- Testability (mock repositories easily)
- Type Safety (no raw dict objects)
- No SQL in business logic (all in repositories)
"""

from storage.postgres.repositories.base_repository import BaseRepository
from storage.postgres.repositories.project_repository import ProjectRepository
from storage.postgres.repositories.item_repository import ItemRepository
from storage.postgres.repositories.relation_repository import RelationRepository
from storage.postgres.repositories.merge_repository import MergeRepository

__all__ = [
    "BaseRepository",
    "ProjectRepository",
    "ItemRepository",
    "RelationRepository",
    "MergeRepository",
]
