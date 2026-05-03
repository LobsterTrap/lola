"""Tests for OpenCodeTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.opencode import OpenCodeTarget


# --- User scope tests ---


def test_opencode_command_path_user_scope():
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".opencode" / "commands"


def test_opencode_agent_path_user_scope():
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path.home() / ".opencode" / "agents"


def test_opencode_instructions_path_user_scope():
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / "AGENTS.md"


def test_opencode_mcp_path_user_scope():
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / "opencode.json"


def test_opencode_skill_path_user_scope_from_managed_section():
    """OpenCodeTarget inherits from ManagedSectionTarget which has get_skill_path."""
    target = OpenCodeTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / "AGENTS.md"


# --- Project scope tests ---


def test_opencode_command_path_project_scope():
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.opencode/commands")


def test_opencode_agent_path_project_scope():
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.opencode/agents")


def test_opencode_instructions_path_project_scope():
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "project")
    assert path == Path("/home/user/project/AGENTS.md")


def test_opencode_mcp_path_project_scope():
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "project")
    assert path == Path("/home/user/project/opencode.json")


def test_opencode_skill_path_project_scope():
    target = OpenCodeTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/AGENTS.md")


# --- Default scope tests (no explicit scope argument) ---


def test_opencode_command_path_default_scope():
    target = OpenCodeTarget()
    result = target.get_command_path("/home/user/project")
    assert result == Path("/home/user/project/.opencode/commands")


def test_opencode_agent_path_default_scope():
    target = OpenCodeTarget()
    result = target.get_agent_path("/home/user/project")
    assert result == Path("/home/user/project/.opencode/agents")


def test_opencode_instructions_path_default_scope():
    target = OpenCodeTarget()
    result = target.get_instructions_path("/home/user/project")
    assert result == Path("/home/user/project/AGENTS.md")


def test_opencode_mcp_path_default_scope():
    target = OpenCodeTarget()
    result = target.get_mcp_path("/home/user/project")
    assert result == Path("/home/user/project/opencode.json")


def test_opencode_skill_path_default_scope():
    target = OpenCodeTarget()
    result = target.get_skill_path("/home/user/project")
    assert result == Path("/home/user/project/AGENTS.md")
