"""Snapshot service for merge rollback support.

Handles creation and restoration of snapshots when merging items.
Snapshots allow safe rollback of merge operations.

A snapshot captures the full state of merged items before the merge,
so we can restore them if the merge needs to be undone.
"""

import json
from datetime import datetime
from typing import Optional

from core.exceptions import StorageError


class MergeSnapshot:
    """Represents a snapshot of items being merged."""

    def __init__(
        self,
        source_item: dict,
        target_item: dict,
        timestamp: datetime,
        source_relations: list[dict] | None = None,
        target_relations: list[dict] | None = None,
    ):
        """Initialize snapshot.

        Args:
            source_item: Original state of source item (as dict)
            target_item: Original state of target item (as dict)
            timestamp: When snapshot was taken
            source_relations: Original relations involving source item
            target_relations: Original relations involving target item
        """
        self.source_item = source_item
        self.target_item = target_item
        self.timestamp = timestamp
        self.source_relations = source_relations or []
        self.target_relations = target_relations or []

    def to_dict(self) -> dict:
        """Convert snapshot to serializable dictionary.

        Returns:
            Dictionary representation suitable for JSON storage
        """
        return {
            "source_item": self.source_item,
            "target_item": self.target_item,
            "timestamp": self.timestamp.isoformat(),
            "source_relations": self.source_relations,
            "target_relations": self.target_relations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MergeSnapshot":
        """Reconstruct snapshot from dictionary.

        Args:
            data: Dictionary with snapshot data

        Returns:
            MergeSnapshot instance

        Raises:
            StorageError: If data is incomplete or invalid
        """
        required_fields = ["source_item", "target_item", "timestamp"]
        missing = [f for f in required_fields if f not in data]

        if missing:
            raise StorageError(
                f"Snapshot incomplete (missing: {missing}). Cannot restore merge."
            )

        try:
            timestamp = datetime.fromisoformat(data["timestamp"])
        except (ValueError, TypeError) as e:
            raise StorageError(f"Invalid timestamp in snapshot: {e}")

        return cls(
            source_item=data["source_item"],
            target_item=data["target_item"],
            timestamp=timestamp,
            source_relations=data.get("source_relations", []),
            target_relations=data.get("target_relations", []),
        )


class SnapshotService:
    """Service for managing merge snapshots."""

    @staticmethod
    def create_snapshot(
        source_item: dict,
        target_item: dict,
        source_relations: list[dict] | None = None,
        target_relations: list[dict] | None = None,
    ) -> dict:
        """Create a merge snapshot.

        Args:
            source_item: Source item state (as dict from DTO)
            target_item: Target item state (as dict from DTO)
            source_relations: Relations involving source item
            target_relations: Relations involving target item

        Returns:
            Snapshot dictionary ready for JSON storage

        Raises:
            StorageError: If snapshot creation fails
        """
        try:
            snapshot = MergeSnapshot(
                source_item=source_item,
                target_item=target_item,
                timestamp=datetime.now(),
                source_relations=source_relations,
                target_relations=target_relations,
            )
            return snapshot.to_dict()
        except Exception as e:
            raise StorageError(f"Failed to create snapshot: {e}")

    @staticmethod
    def validate_snapshot(snapshot_data: dict | None) -> bool:
        """Validate that snapshot is complete and can be restored.

        Args:
            snapshot_data: Snapshot data

        Returns:
            True if snapshot is valid

        Raises:
            StorageError: If snapshot is invalid
        """
        if not snapshot_data:
            raise StorageError("Snapshot is empty (None)")

        if not isinstance(snapshot_data, dict):
            raise StorageError(f"Snapshot must be dict, got {type(snapshot_data)}")

        required_fields = ["source_item", "target_item", "timestamp"]
        missing = [f for f in required_fields if f not in snapshot_data]

        if missing:
            raise StorageError(f"Snapshot missing fields: {missing}")

        return True

    @staticmethod
    def serialize_snapshot(snapshot_data: dict) -> str:
        """Serialize snapshot to JSON string.

        Args:
            snapshot_data: Snapshot dictionary

        Returns:
            JSON string representation

        Raises:
            StorageError: If serialization fails
        """
        try:
            return json.dumps(snapshot_data, default=str, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to serialize snapshot: {e}")

    @staticmethod
    def deserialize_snapshot(json_str: str) -> dict:
        """Deserialize snapshot from JSON string.

        Args:
            json_str: JSON string representation

        Returns:
            Snapshot dictionary

        Raises:
            StorageError: If deserialization fails
        """
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to deserialize snapshot: {e}")
        except Exception as e:
            raise StorageError(f"Unexpected error deserializing snapshot: {e}")

    @staticmethod
    def get_rollback_instructions(snapshot_data: dict) -> str:
        """Generate human-readable instructions for rolling back a merge.

        Args:
            snapshot_data: Snapshot data

        Returns:
            Instructions text

        Raises:
            StorageError: If snapshot is invalid
        """
        SnapshotService.validate_snapshot(snapshot_data)

        source = snapshot_data.get("source_item", {})
        target = snapshot_data.get("target_item", {})

        instructions = f"""
To rollback this merge, the system will:

1. Restore source item:
   ID: {source.get('id', 'unknown')}
   Type: {source.get('type', 'unknown')}
   Text: {source.get('text', 'unknown')[:50]}...

2. Restore target item:
   ID: {target.get('id', 'unknown')}
   Type: {target.get('type', 'unknown')}
   Text: {target.get('text', 'unknown')[:50]}...

3. Restore {len(snapshot_data.get('source_relations', []))} relations from source
4. Restore {len(snapshot_data.get('target_relations', []))} relations from target

This operation is atomic and safe.
        """.strip()

        return instructions
