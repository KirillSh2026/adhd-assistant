"""Utilities for CLI command parsing and validation."""

from core.exceptions import CliInputError


def parse_int(value: str, argument_name: str) -> int:
    """Parse string argument as integer with validation."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise CliInputError(f"{argument_name} must be an integer, got: {value}") from exc
