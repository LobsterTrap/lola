"""Tests for OpenCodeTarget scope-aware path resolution."""

from pathlib import Path
import pytest
from unittest.mock import Mock, patch

from lola.targets.opencode import OpenCodeTarget
from lola.config import get_user_config_dir


# --- User config directory tests ---


def test_get_user_config_dir_with_xdg_env_set(monkeypatch):
    """Test get_user_config_dir when XDG_CONFIG_HOME is set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    # Force reload the platformdirs instance
    import importlib
    import lola.config

    importlib.reload(lola.config)
    assert get_user_config_dir() == Path("/custom/config/opencode")


def test_get_user_config_dir_without_env(monkeypatch):
    """Test get_user_config_dir falls back to platform defaults."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    # Force reload the platformdirs instance
    import importlib
    import lola.config

    importlib.reload(lola.config)
    result = get_user_config_dir()
    # On Unix systems, this should be ~/.config
    # On other platforms, platformdirs will return appropriate paths
    assert result.is_absolute()


# --- User scope tests with platformdirs ---


@pytest.fixture
def reload_config():
    """Fixture to reload config module after environment changes."""

    def _reload():
        import importlib
        import lola.config

        importlib.reload(lola.config)

    return _reload


def test_opencode_command_path_user_scope_custom_config(monkeypatch, reload_config):
    """Test command path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    reload_config()
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/commands")


def test_opencode_agent_path_user_scope_custom_config(monkeypatch, reload_config):
    """Test agent path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    reload_config()
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/agents")


def test_opencode_instructions_path_user_scope_custom_config(
    monkeypatch, reload_config
):
    """Test instructions path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    reload_config()
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/AGENTS.md")


def test_opencode_mcp_path_user_scope_custom_config(monkeypatch, reload_config):
    """Test MCP path uses custom XDG_CONFIG_HOME when set."""
    monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")
    reload_config()
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path("/custom/config/opencode/opencode.json")


def test_opencode_command_path_user_scope_platform_default(monkeypatch, reload_config):
    """Test command path uses platform defaults when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    reload_config()
    target = OpenCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    # Should use platformdirs default - ends with opencode/commands
    assert path.parts[-2:] == ("opencode", "commands")
    assert path.is_absolute()


def test_opencode_agent_path_user_scope_platform_default(monkeypatch, reload_config):
    """Test agent path uses platform defaults when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    reload_config()
    target = OpenCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    # Should use platformdirs default - ends with opencode/agents
    assert path.parts[-2:] == ("opencode", "agents")
    assert path.is_absolute()


def test_opencode_instructions_path_user_scope_platform_default(
    monkeypatch, reload_config
):
    """Test instructions path uses platform defaults when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    reload_config()
    target = OpenCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    # Should use platformdirs default - ends with opencode/AGENTS.md
    assert path.parts[-2:] == ("opencode", "AGENTS.md")
    assert path.is_absolute()


def test_opencode_mcp_path_user_scope_platform_default(monkeypatch, reload_config):
    """Test MCP path uses platform defaults when XDG_CONFIG_HOME unset."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    reload_config()
    target = OpenCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    # Should use platformdirs default - ends with opencode/opencode.json
    assert path.parts[-2:] == ("opencode", "opencode.json")
    assert path.is_absolute()


# --- Cross-platform path tests with mocked platformdirs ---


@pytest.mark.parametrize(
    "platform_config_dir,platform_name",
    [
        ("/home/user/.config/opencode", "Linux/Unix"),
        ("/Users/user/Library/Application Support/opencode", "macOS"),
        (r"C:\Users\user\AppData\Roaming\opencode", "Windows"),
    ],
)
def test_opencode_paths_cross_platform(platform_config_dir, platform_name):
    """Test OpenCode paths work correctly on different platforms."""
    mock_platform_dirs = Mock()
    mock_platform_dirs.user_config_dir = platform_config_dir

    with patch("lola.config._PLATFORM_DIRS", mock_platform_dirs):
        target = OpenCodeTarget()

        # Test all path types
        command_path = target.get_command_path("/project", "user")
        agent_path = target.get_agent_path("/project", "user")
        instructions_path = target.get_instructions_path("/project", "user")
        mcp_path = target.get_mcp_path("/project", "user")

        # Expected base path (platformdirs already includes opencode)
        base = Path(platform_config_dir)

        assert command_path == base / "commands"
        assert agent_path == base / "agents"
        assert instructions_path == base / "AGENTS.md"
        assert mcp_path == base / "opencode.json"


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
