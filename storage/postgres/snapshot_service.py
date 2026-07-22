from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict

from core.exceptions import StorageError


class SnapshotService:
    @staticmethod
    def create_snapshot(source_item: dict, target_item: dict) -> dict:
        return {
            "source_item": source_item,
            "target_item": target_item,
            "timestamp": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _validate_snapshot_raises(snapshot: dict) -> None:
        if not isinstance(snapshot, dict):
            raise StorageError("Snapshot must be a dictionary")
        required = ("source_item", "target_item", "timestamp")
        for field in required:
            if field not in snapshot or snapshot[field] is None:
                raise StorageError(f"Snapshot missing required field: {field}")
        if not isinstance(snapshot.get("source_item"), dict):
            raise StorageError("snapshot['source_item'] must be a dict")
        if not isinstance(snapshot.get("target_item"), dict):
            raise StorageError("snapshot['target_item'] must be a dict")

    @staticmethod
    def validate_snapshot(snapshot: dict) -> bool:
        SnapshotService._validate_snapshot_raises(snapshot)
        return True

    @staticmethod
    def serialize_snapshot(snapshot: dict) -> str:
        SnapshotService._validate_snapshot_raises(snapshot)
        return json.dumps(snapshot, sort_keys=True)

    @staticmethod
    def deserialize_snapshot(json_str: str) -> dict:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            raise StorageError("Serialized snapshot is not a JSON object")
        SnapshotService._validate_snapshot_raises(data)
        return data

    @staticmethod
    def get_rollback_instructions(snapshot: dict) -> str:
        SnapshotService._validate_snapshot_raises(snapshot)
        source_id = snapshot.get("source_item", {}).get("id", "??")
        target_id = snapshot.get("target_item", {}).get("id", "??")
        return (
            f"To rollback merge, restore item {source_id} and item {target_id} "
            f"from backup. This operation should be performed atomically."
        )
