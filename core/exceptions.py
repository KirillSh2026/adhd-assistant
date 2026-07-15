from __future__ import annotations


class AppError(Exception):
    """Base application error."""


class ConfigurationError(AppError):
    """Raised when configuration is invalid or incomplete."""


class CliInputError(AppError, ValueError):
    """Raised when CLI arguments are invalid."""


class StorageError(AppError):
    """Base storage error."""


class UnsupportedStorageCapabilityError(StorageError, RuntimeError):
    """Raised when backend does not support requested capability."""


class StorageEntityNotFoundError(StorageError):
    """Raised when expected storage entity is not found."""
