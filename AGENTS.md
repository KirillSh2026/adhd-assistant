# Repository Guidelines

## Project Structure & Module Organization

- `app/`: Entry points for the application (Telegram bot and CLI).
- `cli/`: Command-line interface implementation.
- `config/`: Configuration loading and factory for storage backends.
- `core/`: Core exceptions and shared utilities.
- `data/`: Default JSON storage location (notes.json).
- `interfaces/`: Abstract interfaces (e.g., storage).
- `migrations/`: Database schema migrations for PostgreSQL.
- `models/`: Data models (Item, Relation, etc.).
- `services/`: Business logic services (item capture, listing, relations, merging).
- `storage/`: Concrete storage implementations (JSON and PostgreSQL).
- `telegram_bot/`: Telegram-specific handler and formatter.
- `tests/`: Unit and integration tests.

## Build, Test, and Development Commands

- `make` or `make help`: Show available Makefile targets.
- `make test`: Run the test suite with pytest.
- `make lint`: Run code linting (if configured).
- `make format`: Format code (if configured).
- `docker-compose up`: Start the application with PostgreSQL (see docker-compose.yml).
- `python app/telegram_main.py`: Run the Telegram bot (requires ADHD_TELEGRAM_TOKEN).
- `python -m cli.main`: Run the CLI assistant.

## Coding Style & Naming Conventions

- Follow PEP 8 for Python code.
- Use 4 spaces per indentation level.
- Module names: lowercase_with_underscores.
- Variable and function names: lowercase_with_underscores.
- Class names: CapWords.
- Constants: UPPERCASE_WITH_UNDERSCORES.
- Type hints are encouraged (using `typing` module).
- Docstrings follow Google or NumPy style (see existing code).

## Testing Guidelines

- Testing framework: `pytest`.
- Tests are located in the `tests/` directory.
- Test naming: `test_*.py` files and `test_*` functions.
- Aim for high coverage; new features should include tests.
- Run tests with `make test` or `pytest`.
- Mock external services (Telegram API, storage) in unit tests.

## Commit & Pull Request Guidelines

- Commit messages: Use imperative mood, short summary (50 chars or less), optional body.
- Reference issues: `gh-123` or fix `gh-123` if applicable.
- Pull requests should:
  - Include a clear description of changes.
  - Link to any related issues.
  - Pass all tests and linting checks.
  - Be reviewed by at least one contributor.
  - Include screenshots or examples for UI/UX changes (if relevant).

## Additional Notes

- Environment variables are configured via `.env` (not in repo) or OS environment.
  - Key variables: `ADHD_TELEGRAM_TOKEN`, `ADHD_STORAGE_BACKEND`, `ADHD_NOTES_PATH`, `DATABASE_URL`.
- The project uses `pydantic-settings` for configuration management.
- For development, consider using a virtual environment and installing dependencies with `pip install -r requirements.txt`.
