"""Argument parsing and command execution logic.

This module handles parsing raw sys.argv into structured command arguments
and executing the appropriate handler. Commands receive parsed args as parameters,
not direct access to sys.argv.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CommandArgs:
    """Parsed command arguments."""
    command: str
    args: list[str]  # Remaining positional arguments


def parse_command_line(argv: list[str]) -> CommandArgs:
    """Parse command line arguments from sys.argv format.
    
    Args:
        argv: sys.argv or similar list (e.g., ["prog", "command", "arg1", "arg2"])
    
    Returns:
        CommandArgs with command name and remaining args
    """
    if len(argv) < 2:
        return CommandArgs(command="", args=[])
    
    command = argv[1].strip().lower()
    args = [arg.strip() for arg in argv[2:] if arg.strip()]
    return CommandArgs(command=command, args=args)
