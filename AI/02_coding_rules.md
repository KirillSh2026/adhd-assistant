# Стандарты кода для ADHD Assistant

## Python

### Общие требования

- **Python 3.10+** для type hints и match/case синтаксиса.
- **UTF-8 encoding** (особенно важно для русского текста).
- **Type hints** для всех функций и методов.
- **Документация** для публичных методов (docstrings в стиле Google).

### Структура модулей

```
app/
├── main.py              # CLI entry point
├── commands/            # Подкоманды (add, list, clear)
├── parsers/             # Парсинг пользовательского ввода
└── output/              # Форматирование вывода

models/
├── item.py              # Доменная модель Item
├── dependency.py        # Модель Dependency
└── user_state.py        # Состояние пользователя

services/
├── item_service.py      # Логика работы с Item
├── dependency_service.py # Логика зависимостей
└── organization_service.py # Предложения по организации

storage/
├── json_storage.py      # Текущая реализация (JSON)
├── sqlite_storage.py    # SQLite реализация (для миграции)
└── database.py          # Общий интерфейс
```

### Примеры кода

**Типы и документация:**
```python
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class ItemType(str, Enum):
    TASK = "task"
    NOTE = "note"
    IDEA = "idea"

@dataclass
class Item:
    """Элемент для захвата и организации информации."""
    
    id: str
    type: ItemType
    text: str
    project_id: Optional[str] = None
    priority: Optional[str] = None
    energy_level: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Валидация и инициализация."""
        if not self.text or not self.text.strip():
            raise ValueError("text не может быть пустым")
        if self.created_at is None:
            self.created_at = datetime.now()

class ItemService:
    """Координатор операций с Item."""
    
    def __init__(self, storage):
        self.storage = storage
    
    def add_item(self, item: Item) -> str:
        """Добавить новый элемент.
        
        Args:
            item: Элемент для добавления
            
        Returns:
            str: ID добавленного элемента
            
        Raises:
            ValueError: Если элемент невалиден
        """
        if not item.id:
            item.id = str(uuid.uuid4())
        
        self.storage.save(item)
        return item.id
```

**JSON сохранение с Cyrillic:**
```python
import json

def save_items(items: List[Item], path: str):
    """Сохранить элементы в JSON (сохранить кириллицу)."""
    data = [item.to_dict() for item in items]
    
    with open(path, 'w', encoding='utf-8') as f:
        # ВАЖНО: ensure_ascii=False, indent=2
        json.dump(data, f, ensure_ascii=False, indent=2)
```

### Обработка ошибок

```python
class ItemError(Exception):
    """Базовое исключение для Item."""
    pass

class ItemNotFoundError(ItemError):
    """Элемент не найден."""
    pass

class DependencyError(ItemError):
    """Ошибка с зависимостями."""
    pass

# Использование:
try:
    item = service.get_item(item_id)
except ItemNotFoundError:
    print(f"Элемент {item_id} не найден")
except ItemError as e:
    print(f"Ошибка: {e}")
```

## SQL

### Типы данных

- **id**: `UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- **текст**: `TEXT` для большого объема, `VARCHAR(n)` для ограниченного
- **datetime**: `TIMESTAMP DEFAULT CURRENT_TIMESTAMP`
- **enum**: `VARCHAR(50)` с CONSTRAINT CHECK для допустимых значений (или типы ENUM в PostgreSQL)
- **JSON**: `JSONB` для PostgreSQL (индексируется)

### Индексы

Создавать индексы для:
- **Внешние ключи** (FK уже индексируются в большинстве СУБД)
- **WHERE условия** частых запросов
- **Сортировка** частых операций (ORDER BY)
- **Уникальные комбинации** (UNIQUE constraints)

```sql
-- Хорошо (индексирует частый поиск)
CREATE INDEX idx_item_by_project_status ON item(project_id, status);

-- Плохо (индекс на всех ITEM - не помогает)
CREATE INDEX idx_item_id ON item(id); -- уже PRIMARY KEY
```

### Именование

- **Таблицы**: snake_case, единственное число (item, не items)
- **Столбцы**: snake_case, описательное имя
- **FK**: `{table_name}_id` (item_id, project_id)
- **Индексы**: `idx_{table}_{columns}` или `idx_{table}_{purpose}`
- **Constraints**: `ck_{table}_{purpose}`, `uq_{table}_{columns}`

### Запросы

```sql
-- Хорошо: явное указание столбцов
SELECT id, text, status, priority 
FROM item 
WHERE project_id = $1 AND status != 'archived'
ORDER BY priority DESC, deadline ASC
LIMIT 50;

-- Плохо: SELECT * (мешает оптимизации)
SELECT * FROM item;

-- Плохо: неэффективный вложенный запрос
SELECT * FROM item 
WHERE id IN (SELECT item_id FROM item_dependency WHERE ...);

-- Хорошо: используется JOIN
SELECT DISTINCT i.* 
FROM item i
JOIN item_dependency d ON i.id = d.from_item_id
WHERE d.relationship_type = 'blocks';
```

## Комментирование

**Писать комментарии для:**
- Нетривиальной логики (почему, а не что)
- Сложных запросов SQL
- Обхода ограничений системы
- Исторических причин (если другой вариант невозможен)

**НЕ писать комментарии для:**
- Очевидного кода (`x = x + 1` не нужен комментарий)
- Простых циклов и условий
- Кода, который делает то же самое, что название функции

```python
# Плохо
x = x + 1  # Увеличить x на 1

# Хорошо
def merge_duplicate_items(duplicate_ids: List[str], primary_id: str):
    """Объединить дублирующиеся элементы в один.
    
    Сохраняем историю в ITEM_MERGE для возможности отката.
    Исходные данные не удаляются (архивируются в audit).
    """
    # ...
```

## Тестирование

Когда тесты будут добавлены:

```python
# tests/test_item_service.py
import pytest
from models.item import Item
from services.item_service import ItemService

class TestItemService:
    
    @pytest.fixture
    def service(self):
        """Инициализировать сервис с пустым хранилищем."""
        return ItemService(InMemoryStorage())
    
    def test_add_item_success(self, service):
        """Успешно добавить элемент."""
        item = Item(id="1", type="task", text="Купить хлеб")
        item_id = service.add_item(item)
        
        assert item_id == "1"
        retrieved = service.get_item(item_id)
        assert retrieved.text == "Купить хлеб"
    
    def test_add_empty_text_fails(self, service):
        """Нельзя добавить элемент с пустым текстом."""
        item = Item(id="1", type="task", text="")
        
        with pytest.raises(ValueError):
            service.add_item(item)
```

## Git Commits

**Формат:**
```
[TYPE] Краткое описание (максимум 60 символов)

Подробное описание (если необходимо):
- Почему изменение нужно
- Как оно влияет на архитектуру/API
- Ссылки на issues

Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>
```

**Types:**
- `feat` — новая функция
- `fix` — исправление ошибки
- `refactor` — переструктурирование без функциональных изменений
- `perf` — оптимизация производительности
- `docs` — обновление документации
- `test` — добавление/изменение тестов
- `chore` — обслуживание (зависимости, конфиг)
- `migrate` — изменение структуры БД или формата данных

**Примеры:**
```
feat: Add dependency detection between items

- Implement ITEM_DEPENDENCY table in DB schema
- Add relationship types: blocks, relates_to, duplicate_of
- Create dependency_service for finding and validating dependencies
- Update item_service to check for dependencies before deletion

Implements feature from AI/05_product_vision.md (Выявление связей)

fix: Preserve item order in list output

- Restore original array position when filtering empty texts
- Fixes breaking change from commit abc123
- Tests: list_task now maintains original numbering

migrate: Prepare migration from JSON to SQLite

- Create migration script with pre-flight checks
- Detect potential duplicates using string similarity
- Generate audit trail for all migrated items
```

## Версионирование

На данном этапе проекта используется **semver** подхода:

- **Major** (1.0.0 → 2.0.0): Breaking changes в CLI контракте или API
- **Minor** (1.0.0 → 1.1.0): Новые функции (backward-compatible)
- **Patch** (1.0.0 → 1.0.1): Исправления ошибок

Версия хранится в:
- `VERSION` файл в корне
- `__version__` в `app/main.py`
- `setup.py` если будет packaging
