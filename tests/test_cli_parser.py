"""Tests for CLI parser module."""

from cli.parser import parse_command_line


def test_parse_command_line_with_command_and_args():
    """Test parsing command line with command and arguments."""
    argv = ["prog", "task", "Buy", "groceries"]
    result = parse_command_line(argv)
    
    assert result.command == "task"
    assert result.args == ["Buy", "groceries"]


def test_parse_command_line_command_only():
    """Test parsing command line with only command."""
    argv = ["prog", "list"]
    result = parse_command_line(argv)
    
    assert result.command == "list"
    assert result.args == []


def test_parse_command_line_empty():
    """Test parsing empty command line."""
    argv = ["prog"]
    result = parse_command_line(argv)
    
    assert result.command == ""
    assert result.args == []


def test_parse_command_line_lowercases_command():
    """Test that command is converted to lowercase."""
    argv = ["prog", "TASK", "something"]
    result = parse_command_line(argv)
    
    assert result.command == "task"
    assert result.args == ["something"]


def test_parse_command_line_strips_whitespace():
    """Test that arguments are stripped of whitespace."""
    argv = ["prog", "task", "  Buy  ", " milk "]
    result = parse_command_line(argv)
    
    assert result.command == "task"
    assert result.args == ["Buy", "milk"]


def test_parse_command_line_skips_empty_args():
    """Test that empty arguments are skipped."""
    argv = ["prog", "task", "", "Buy", "  ", "milk"]
    result = parse_command_line(argv)
    
    assert result.command == "task"
    assert result.args == ["Buy", "milk"]
