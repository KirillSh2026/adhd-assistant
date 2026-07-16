"""
Legacy ItemService for backwards compatibility.

DEPRECATED: Use ItemServiceRegistry instead, which provides access to specialized services:
  - service.capture for item creation
  - service.list for item listing
  - service.relation for relation operations
  - service.merge for merge operations

This class now delegates to ItemServiceRegistry and will be removed in a future version.
"""

from __future__ import annotations

from datetime import datetime

from interfaces.storage import Storage
from models.item import Item
from services.item_service_registry import ItemServiceRegistry
from services.item_type_classifier import ItemTypeClassifier
from services.relation_analysis_service import RelationAnalysisService


class ItemService(ItemServiceRegistry):
    """
    Backwards-compatible wrapper around ItemServiceRegistry.
    All methods delegate to the registry's specialized services.
    """

    def __init__(
        self,
        storage: Storage,
        classifier: ItemTypeClassifier | None = None,
        relation_analyzer: RelationAnalysisService | None = None,
    ):
        super().__init__(storage, classifier, relation_analyzer)
