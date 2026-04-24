"""Tests for CursorTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.cursor import CursorTarget


# --- User scope tests ---


def test_cursor_skill_path_user_scope():
    target = CursorTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / ".cursor" / "skills"


def test_cursor_command_path_user_scope():
    target = CursorTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".cursor" / "commands"


def test_cursor_agent_path_user_scope():
    target = CursorTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path.home() / ".cursor" / "agents"


def test_cursor_instructions_path_user_scope():
    target = CursorTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / ".cursor" / "rules"


def test_cursor_mcp_path_user_scope():
    target = CursorTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / ".cursor" / "mcp.json"


# --- Project scope tests ---


def test_cursor_skill_path_project_scope():
    target = CursorTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.cursor/skills")


def test_cursor_command_path_project_scope():
    target = CursorTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.cursor/commands")


def test_cursor_agent_path_project_scope():
    target = CursorTarget()
    path = target.get_agent_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.cursor/agents")


def test_cursor_instructions_path_project_scope():
    target = CursorTarget()
    path = target.get_instructions_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.cursor/rules")


def test_cursor_mcp_path_project_scope():
    target = CursorTarget()
    path = target.get_mcp_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.cursor/mcp.json")


# --- Default scope tests (no explicit scope argument) ---


def test_cursor_skill_path_default_scope():
    target = CursorTarget()
    result = target.get_skill_path("/home/user/project")
    assert result == Path("/home/user/project/.cursor/skills")


def test_cursor_command_path_default_scope():
    target = CursorTarget()
    result = target.get_command_path("/home/user/project")
    assert result == Path("/home/user/project/.cursor/commands")


def test_cursor_agent_path_default_scope():
    target = CursorTarget()
    result = target.get_agent_path("/home/user/project")
    assert result == Path("/home/user/project/.cursor/agents")


def test_cursor_instructions_path_default_scope():
    target = CursorTarget()
    result = target.get_instructions_path("/home/user/project")
    assert result == Path("/home/user/project/.cursor/rules")


def test_cursor_mcp_path_default_scope():
    target = CursorTarget()
    result = target.get_mcp_path("/home/user/project")
    assert result == Path("/home/user/project/.cursor/mcp.json")
