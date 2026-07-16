"""Data Transfer Objects for PostgreSQL storage layer.

These DTOs represent database records and are used to exchange data between
repositories. They are immutable, typed, and fully independent of the
domain Item model.

Pattern: Repository ↔ DTO ↔ PostgresStorage → Services
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class ProjectRecord:
    """Represents a row in the project table."""

    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"  # active, archived
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class ItemRecord:
    """Represents a row in the item table."""

    id: str
    project_id: str
    type: str  # task, note, idea (from ItemType Enum)
    text: str
    status: str = "active"  # active, archived, deleted (from ItemStatus Enum)
    source: str = "cli"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class RelationRecord:
    """Represents a row in the item_dependency table."""

    id: str
    from_item_id: str
    to_item_id: str
    relationship_type: str  # related_to, depends_on, duplicate_of
    reason: Optional[str] = None
    is_confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class MergeRecord:
    """Represents a row in the item_merge table."""

    id: str
    project_id: str
    source_item_id: str
    target_item_id: str
    merge_reason: str
    merged_by: str = "cli"
    snapshot_data: Optional[dict] = None  # JSON snapshot of merged items
    status: str = "completed"  # completed, reverted
    created_at: Optional[datetime] = None
    reverted_at: Optional[datetime] = None


@dataclass(frozen=True)
class RelationSuggestionRecord:
    """Represents a row in the relation_suggestion table (if exists)."""

    id: str
    from_item_id: str
    to_item_id: str
    relationship_type: str
    confidence: float = 0.0  # 0.0-1.0
    reason: Optional[str] = None
    created_at: Optional[datetime] = None


# ============================================================================
# DTO CONSTRUCTION HELPERS
# ============================================================================


def item_record_from_row(row: tuple) -> ItemRecord:
    """Construct ItemRecord from database cursor row.

    Assumes row format from item table SELECT:
    (id, project_id, type, text, status, source, created_at, updated_at)
    """
    return ItemRecord(
        id=str(row[0]),
        project_id=str(row[1]),
        type=row[2],
        text=row[3],
        status=row[4],
        source=row[5],
        created_at=row[6],
        updated_at=row[7],
    )


def relation_record_from_row(row: tuple) -> RelationRecord:
    """Construct RelationRecord from database cursor row.

    Assumes row format from item_dependency table SELECT:
    (id, from_item_id, to_item_id, relationship_type, reason,
     is_confirmed, confirmed_at, created_at, updated_at)
    """
    return RelationRecord(
        id=str(row[0]),
        from_item_id=str(row[1]),
        to_item_id=str(row[2]),
        relationship_type=row[3],
        reason=row[4],
        is_confirmed=bool(row[5]),
        confirmed_at=row[6],
        created_at=row[7],
        updated_at=row[8],
    )


def merge_record_from_row(row: tuple) -> MergeRecord:
    """Construct MergeRecord from database cursor row.

    Assumes row format from item_merge table SELECT:
    (id, project_id, source_item_id, target_item_id, merge_reason,
     merged_by, snapshot_data, status, created_at, reverted_at)
    """
    return MergeRecord(
        id=str(row[0]),
        project_id=str(row[1]),
        source_item_id=str(row[2]),
        target_item_id=str(row[3]),
        merge_reason=row[4],
        merged_by=row[5],
        snapshot_data=row[6],  # Already JSONB from psycopg
        status=row[7],
        created_at=row[8],
        reverted_at=row[9],
    )


def project_record_from_row(row: tuple) -> ProjectRecord:
    """Construct ProjectRecord from database cursor row.

    Assumes row format from project table SELECT:
    (id, name, description, status, created_at, updated_at)
    """
    return ProjectRecord(
        id=str(row[0]),
        name=row[1],
        description=row[2],
        status=row[3],
        created_at=row[4],
        updated_at=row[5],
    )
