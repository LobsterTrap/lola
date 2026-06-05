"""Tests for OpenCodeTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.opencode import OpenCodeTarget
from lola.config import get_user_config_dir


# --- User config directory tests ---


def test_get_user_config_dir_with_xdg_env_set(monkeypatch):
    """Test get_user_config_dir when XDG_CONFIG_HOME is set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    assert get_user_config_dir() == Path("/custom/config/opencode")


def test_get_user_config_dir_without_env(monkeypatch):
    """Test get_user_config_dir falls back to ~/.config when XDG unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert get_user_config_dir() == Path.home() / ".config" / "opencode"


# --- User scope tests with custom XDG_CONFIG_HOME ---


def test_opencode_command_path_user_scope_custom_config(monkeypatch):
    """Test command path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/commands")


def test_opencode_agent_path_user_scope_custom_config(monkeypatch):
    """Test agent path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/agents")


def test_opencode_instructions_path_user_scope_custom_config(monkeypatch):
    """Test instructions path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/AGENTS.md")


def test_opencode_mcp_path_user_scope_custom_config(monkeypatch):
    """Test MCP path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/opencode.json")


def test_opencode_command_path_user_scope_platform_default(monkeypatch):
    """Test command path falls back to ~/.config when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".config" / "opencode" / "commands"


def test_opencode_agent_path_user_scope_platform_default(monkeypatch):
    """Test agent path falls back to ~/.config when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path.home() / ".config" / "opencode" / "agents"


def test_opencode_instructions_path_user_scope_platform_default(monkeypatch):
    """Test instructions path falls back to ~/.config when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / ".config" / "opencode" / "AGENTS.md"


def test_opencode_mcp_path_user_scope_platform_default(monkeypatch):
    """Test MCP path falls back to ~/.config when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / ".config" / "opencode" / "opencode.json"


def test_opencode_skill_path_user_scope():
    """OpenCodeTarget uses file-based skills at .opencode/skills/."""
    target = OpenCodeTarget()
    path = target.get_skill_path("/home/user/project")
    assert path == Path("/home/user/project/.opencode/skills")


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
    path = target.get_skill_path("/home/user/project")
    assert path == Path("/home/user/project/.opencode/skills")


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
    assert result == Path("/home/user/project/.opencode/skills")
