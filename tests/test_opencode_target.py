"""Tests for OpenCodeTarget scope-aware path resolution and agent generation."""

from pathlib import Path

import yaml

from lola.targets.opencode import (
    KNOWN_OPENCODE_TOOLS,
    OpenCodeTarget,
    _transform_agent_frontmatter,
)
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


# --- Agent tools transform tests ---


def test_transform_agent_frontmatter_comma_string():
    """Comma-separated tools string is converted to OpenCode dict format."""
    fm = {"description": "Test", "tools": "Read, Write, Bash, Grep"}
    result = _transform_agent_frontmatter(fm)
    tools = result["tools"]
    assert tools["read"] is True
    assert tools["write"] is True
    assert tools["bash"] is True
    assert tools["grep"] is True
    # Unlisted known tools must be explicitly denied
    for t in KNOWN_OPENCODE_TOOLS - {"read", "write", "bash", "grep"}:
        assert tools[t] is False, f"expected {t} to be denied"


def test_transform_agent_frontmatter_no_tools():
    """Frontmatter without tools is passed through unchanged."""
    fm = {"description": "Test", "mode": "subagent"}
    result = _transform_agent_frontmatter(fm)
    assert "tools" not in result
    assert result["description"] == "Test"


def test_transform_agent_frontmatter_dict_tools_unchanged():
    """Tools already in dict format are left alone."""
    tools_dict = {"read": True, "write": True}
    fm = {"description": "Test", "tools": tools_dict}
    result = _transform_agent_frontmatter(fm)
    assert result["tools"] is tools_dict


def test_transform_agent_frontmatter_list_tools():
    """Tools list is converted to OpenCode dict format."""
    fm = {"tools": ["Read", "Write", "Bash"]}
    result = _transform_agent_frontmatter(fm)
    tools = result["tools"]
    assert tools["read"] is True
    assert tools["write"] is True
    assert tools["bash"] is True
    for t in KNOWN_OPENCODE_TOOLS - {"read", "write", "bash"}:
        assert tools[t] is False, f"expected {t} to be denied"


def test_transform_agent_frontmatter_wildcard_string():
    """Wildcard '*' enables all tools without denying any."""
    fm = {"tools": "*"}
    result = _transform_agent_frontmatter(fm)
    assert result["tools"] == {"*": True}
    # No False entries — wildcard means "all tools"
    assert all(v is True for v in result["tools"].values())


def test_generate_agent_transforms_tools(tmp_path):
    """Full generate_agent converts Claude-format tools to OpenCode format."""
    source = tmp_path / "source" / "myagent.md"
    source.parent.mkdir()
    source.write_text(
        "---\n"
        "description: Test agent\n"
        "tools: Read, Write, Bash\n"
        "---\n\n"
        "Instructions.\n"
    )

    target = OpenCodeTarget()
    dest_dir = tmp_path / "dest"
    success = target.generate_agent(source, dest_dir, "myagent", "mymodule")

    assert success
    output_file = dest_dir / "myagent.md"
    content = output_file.read_text()

    assert "mode: subagent" in content
    assert "Instructions." in content

    # Parse the output frontmatter and verify tools dict
    parts = content.split("---")
    fm = yaml.safe_load(parts[1])
    assert fm["tools"]["read"] is True
    assert fm["tools"]["write"] is True
    assert fm["tools"]["bash"] is True
    # Unlisted known tools should be denied
    for t in KNOWN_OPENCODE_TOOLS - {"read", "write", "bash"}:
        assert fm["tools"][t] is False


def test_transform_agent_frontmatter_read_only_denies_writes():
    """A read-only allowlist must deny write-capable tools."""
    fm = {"tools": "Read, Grep, Glob"}
    result = _transform_agent_frontmatter(fm)
    tools = result["tools"]
    assert tools["read"] is True
    assert tools["grep"] is True
    assert tools["glob"] is True
    assert tools["write"] is False
    assert tools["edit"] is False
    assert tools["bash"] is False
    assert tools["patch"] is False


def test_generate_agent_without_tools_unchanged(tmp_path):
    """generate_agent with no tools field still works normally."""
    source = tmp_path / "source" / "simple.md"
    source.parent.mkdir()
    source.write_text(
        "---\n"
        "description: Simple agent\n"
        "---\n\n"
        "Body.\n"
    )

    target = OpenCodeTarget()
    dest_dir = tmp_path / "dest"
    success = target.generate_agent(source, dest_dir, "simple", "mymodule")

    assert success
    output_file = dest_dir / "simple.md"
    content = output_file.read_text()
    parts = content.split("---")
    fm = yaml.safe_load(parts[1])
    assert "tools" not in fm
    assert fm["mode"] == "subagent"
