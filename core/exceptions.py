from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class ConfigurationError(AppError):
    """Raised when configuration is invalid or incomplete."""


class CliInputError(AppError, ValueError):
    """Raised when CLI arguments are invalid."""


class StorageError(AppError):
    """Base storage error - includes context about what failed."""


class UnsupportedStorageCapabilityError(StorageError, RuntimeError):
    """Raised when backend does not support requested capability.
    
    Includes helpful migration guide (e.g., suggesting to use PostgreSQL backend).
    """


class StorageEntityNotFoundError(StorageError):
    """Raised when expected storage entity is not found."""


class StorageCorruptionError(StorageError):
    """Raised when storage file/database is corrupted."""
