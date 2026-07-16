"""Shared fixtures and test utilities for entire test suite.

This module provides:
- Reusable fixtures for storage backends
- Seed data generators
- Test helper functions
- Common setup/teardown patterns
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from models.item import Item, ItemType, ItemStatus
from storage.json_storage import JsonStorage


# ============================================================================
# STORAGE FIXTURES
# ============================================================================


@pytest.fixture
def temp_json_path():
    """Create temporary JSON file path with empty array initialized."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        # Initialize with empty array so JSON is valid
        f.write('[]')
        path = f.name
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def empty_json_storage(temp_json_path):
    """Create empty JSON storage."""
    return JsonStorage(temp_json_path)


@pytest.fixture
def json_storage_with_sample_data(temp_json_path):
    """Create JSON storage with sample data.
    
    Items added:
    - Item 1: task, "Buy groceries"
    - Item 2: note, "Meeting notes"
    - Item 3: idea, "New feature"
    """
    storage = JsonStorage(temp_json_path)
    
    storage.add_item(Item(type=ItemType.TASK, text="Buy groceries"))
    storage.add_item(Item(type=ItemType.NOTE, text="Meeting notes"))
    storage.add_item(Item(type=ItemType.IDEA, text="New feature"))
    
    return storage


@pytest.fixture
def json_storage_with_many_items(temp_json_path):
    """Create JSON storage with 10 items of mixed types."""
    storage = JsonStorage(temp_json_path)
    
    tasks = ["Buy milk", "Call John", "Fix bug", "Write docs", "Review PR"]
    notes = ["Ideas for Q3", "Budget notes", "Meeting summary"]
    ideas = ["AI integration", "Mobile app"]
    
    for text in tasks:
        storage.add_item(Item(type=ItemType.TASK, text=text))
    for text in notes:
        storage.add_item(Item(type=ItemType.NOTE, text=text))
    for text in ideas:
        storage.add_item(Item(type=ItemType.IDEA, text=text))
    
    return storage


# ============================================================================
# SERVICE FIXTURES
# ============================================================================


@pytest.fixture
def capture_service(json_storage_with_sample_data):
    """Create CaptureService with sample data."""
    from services.capture_service import CaptureService
    return CaptureService(json_storage_with_sample_data)


@pytest.fixture
def list_service(json_storage_with_sample_data):
    """Create ListService with sample data."""
    from services.list_service import ListService
    return ListService(json_storage_with_sample_data)


@pytest.fixture
def relation_service(json_storage_with_sample_data):
    """Create RelationService with sample data."""
    from services.relation_service import RelationService
    return RelationService(json_storage_with_sample_data)


@pytest.fixture
def merge_service(json_storage_with_sample_data):
    """Create MergeService with sample data."""
    from services.merge_service import MergeService
    return MergeService(json_storage_with_sample_data)


@pytest.fixture
def item_service_registry(json_storage_with_sample_data):
    """Create ItemServiceRegistry with all services."""
    from services.item_service_registry import ItemServiceRegistry
    return ItemServiceRegistry(json_storage_with_sample_data)


# ============================================================================
# DATA GENERATORS
# ============================================================================


def create_sample_item(
    item_type: ItemType = ItemType.TASK,
    text: str = "Sample item",
    status: ItemStatus = ItemStatus.ACTIVE,
) -> Item:
    """Create a sample item for testing.
    
    Args:
        item_type: Type of item (task/note/idea)
        text: Item text content
        status: Item status (active/archived/deleted)
    
    Returns:
        Item instance with specified properties
    """
    return Item(
        type=item_type,
        text=text,
        status=status,
        created_at=datetime.now(),
    )


def create_items_of_type(
    item_type: ItemType,
    count: int = 3,
) -> list[Item]:
    """Create multiple items of same type.
    
    Args:
        item_type: Type of items to create
        count: Number of items
    
    Returns:
        List of Item instances
    """
    return [
        create_sample_item(
            item_type=item_type,
            text=f"{item_type.value.title()} #{i+1}",
        )
        for i in range(count)
    ]


def populate_storage_with_items(
    storage,
    tasks: int = 3,
    notes: int = 3,
    ideas: int = 3,
) -> None:
    """Populate storage with specified number of each item type.
    
    Args:
        storage: Storage instance to populate
        tasks: Number of tasks to add
        notes: Number of notes to add
        ideas: Number of ideas to add
    """
    for item in create_items_of_type(ItemType.TASK, tasks):
        storage.add_item(item)
    for item in create_items_of_type(ItemType.NOTE, notes):
        storage.add_item(item)
    for item in create_items_of_type(ItemType.IDEA, ideas):
        storage.add_item(item)


# ============================================================================
# ASSERTION HELPERS
# ============================================================================


def assert_item_has_required_fields(item: Item) -> None:
    """Assert that item has all required fields.
    
    Args:
        item: Item to validate
    
    Raises:
        AssertionError: If item is missing required fields
    """
    assert item.id is not None, "Item must have id"
    assert item.type in {ItemType.TASK, ItemType.NOTE, ItemType.IDEA}, \
        "Item must have valid type"
    assert item.text, "Item must have non-empty text"
    assert item.status in {ItemStatus.ACTIVE, ItemStatus.ARCHIVED, ItemStatus.DELETED}, \
        "Item must have valid status"


def assert_items_equal_by_content(item1: Item, item2: Item) -> None:
    """Assert that two items have equal content (ignoring IDs/timestamps).
    
    Args:
        item1: First item
        item2: Second item
    
    Raises:
        AssertionError: If items differ in content
    """
    assert item1.type == item2.type, "Items must have same type"
    assert item1.text == item2.text, "Items must have same text"
    assert item1.status == item2.status, "Items must have same status"


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@pytest.fixture
def storage_with_cleanup(temp_json_path):
    """Context manager for storage with automatic cleanup.
    
    Ensures temp files are cleaned up even if test fails.
    """
    storage = JsonStorage(temp_json_path)
    yield storage
    if os.path.exists(temp_json_path):
        os.unlink(temp_json_path)


# ============================================================================
# TEST DATA CONSTANTS
# ============================================================================


# Sample item texts for consistent test data
SAMPLE_TASK_TEXTS = [
    "Buy groceries",
    "Call customer",
    "Fix critical bug",
    "Write documentation",
    "Review code changes",
]

SAMPLE_NOTE_TEXTS = [
    "Meeting summary from Q3 planning",
    "Ideas for new feature",
    "Architecture notes",
    "Budget tracking notes",
    "Team discussions",
]

SAMPLE_IDEA_TEXTS = [
    "AI-powered recommendations",
    "Mobile app version",
    "Integration with Slack",
    "Dashboard redesign",
    "Automation workflow",
]

# Valid relationship types
VALID_RELATIONSHIP_TYPES = ["depends_on", "blocked_by", "related_to", "duplicate_of"]

# ============================================================================
# MARKERS
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    )
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests",
    )
    config.addinivalue_line(
        "markers",
        "contract: marks tests as contract tests for Storage interface",
    )
