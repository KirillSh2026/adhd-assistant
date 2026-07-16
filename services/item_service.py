"""
DEPRECATED: Legacy ItemService for backwards compatibility.

This class is DEPRECATED and will be removed in a future version.
Use ItemServiceRegistry instead, which provides access to specialized services:
  - service.capture for item creation
  - service.list for item listing
  - service.relation for relation operations
  - service.merge for merge operations

All methods now delegate to ItemServiceRegistry.
"""

from __future__ import annotations

import warnings
from datetime import datetime
from typing import TYPE_CHECKING

from interfaces.storage import Storage
from services.item_service_registry import ItemServiceRegistry
from services.item_type_classifier import ItemTypeClassifier
from services.relation_analysis_service import RelationAnalysisService

if TYPE_CHECKING:
    from models.item import Item


class ItemService(ItemServiceRegistry):
    """
    DEPRECATED: Backwards-compatible wrapper around ItemServiceRegistry.
    
    All methods delegate to the registry's specialized services.
    This class will be removed in a future version.
    
    Use ItemServiceRegistry directly instead:
        from services.item_service_registry import ItemServiceRegistry
        service = ItemServiceRegistry(storage, classifier, relation_analyzer)
    """

    def __init__(
        self,
        storage: Storage,
        classifier: ItemTypeClassifier | None = None,
        relation_analyzer: RelationAnalysisService | None = None,
    ):
        warnings.warn(
            "ItemService is DEPRECATED and will be removed in a future version. "
            "Use ItemServiceRegistry instead for better separation of concerns. "
            "See: services/item_service_registry.py",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(storage, classifier, relation_analyzer)
