"""Integration tests for no-prefix install behavior.

Tests the full install → verify files → uninstall / update workflow
without mocking file operations or target/helper functions.

Scenarios covered:
1. Install creates files with no prefix (all four assistants)
2. Agent frontmatter uses bare agent name in `name` field
3. MCP config keys are bare server names
4. Uninstall removes files and deletes empty MCP configs
5. Uninstall legacy fallback cleans up old `module.cmd.md` files
6. `lola update` removes orphans, adds new items, updates registry
7. Registry YAML stores unprefixed names for commands, agents, and MCPs
"""

import json
from pathlib import Path

import frontmatter as pyfrontmatter
import yaml

from lola.cli.install import install_cmd, uninstall_cmd, update_cmd


# =============================================================================
# Helpers
# =============================================================================


def _install(env: dict, assistant: str) -> None:
    """Install test-module to the given assistant; assert success."""
    result = env["runner"].invoke(
        install_cmd,
        [env["module_name"], str(env["project"]), "-a", assistant, "-f"],
    )
    assert result.exit_code == 0, f"install to {assistant} failed:\n{result.output}"


def _uninstall(env: dict, assistant: str) -> None:
    """Uninstall test-module from the given assistant; assert success."""
    result = env["runner"].invoke(
        uninstall_cmd,
        [env["module_name"], "-a", assistant, "-f"],
    )
    assert result.exit_code == 0, f"uninstall from {assistant} failed:\n{result.output}"


def _update(env: dict) -> None:
    """Run `lola update test-module`; assert success."""
    result = env["runner"].invoke(update_cmd, [env["module_name"]])
    assert result.exit_code == 0, f"update failed:\n{result.output}"


def _read_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a generated markdown file."""
    post = pyfrontmatter.load(str(path))
    return dict(post.metadata)


def _read_registry(env: dict) -> list[dict]:
    """Load all installation entries from installed.yml."""
    installed_file = env["installed_file"]
    if not installed_file.exists():
        return []
    data = yaml.safe_load(installed_file.read_text()) or {}
    return data.get("installations", [])


def _find_inst(env: dict, assistant: str) -> dict:
    """Return the registry entry for the given assistant; fail if missing."""
    installations = _read_registry(env)
    matches = [i for i in installations if i["assistant"] == assistant]
    assert matches, f"No registry entry found for assistant={assistant}"
    return matches[0]


# =============================================================================
# TestInstallFileNaming
# =============================================================================


class TestInstallFileNaming:
    """Install creates files without the module-name prefix."""

    def test_claude_command_no_prefix(self, integration_env):
        _install(integration_env, "claude-code")
        project = integration_env["project"]
        assert (project / ".claude" / "commands" / "review-pr.md").exists()
        assert not (
            project / ".claude" / "commands" / "test-module.review-pr.md"
        ).exists()

    def test_claude_agent_no_prefix(self, integration_env):
        _install(integration_env, "claude-code")
        project = integration_env["project"]
        assert (project / ".claude" / "agents" / "code-reviewer.md").exists()
        assert not (
            project / ".claude" / "agents" / "test-module.code-reviewer.md"
        ).exists()

    def test_cursor_command_no_prefix(self, integration_env):
        _install(integration_env, "cursor")
        assert (
            integration_env["project"] / ".cursor" / "commands" / "review-pr.md"
        ).exists()

    def test_cursor_agent_no_prefix(self, integration_env):
        _install(integration_env, "cursor")
        assert (
            integration_env["project"] / ".cursor" / "agents" / "code-reviewer.md"
        ).exists()

    def test_gemini_command_is_toml_no_prefix(self, integration_env):
        _install(integration_env, "gemini-cli")
        project = integration_env["project"]
        assert (project / ".gemini" / "commands" / "review-pr.toml").exists()
        assert not (
            project / ".gemini" / "commands" / "test-module.review-pr.toml"
        ).exists()

    def test_opencode_command_no_prefix(self, integration_env):
        _install(integration_env, "opencode")
        assert (
            integration_env["project"] / ".opencode" / "command" / "review-pr.md"
        ).exists()

    def test_opencode_agent_no_prefix(self, integration_env):
        _install(integration_env, "opencode")
        assert (
            integration_env["project"] / ".opencode" / "agent" / "code-reviewer.md"
        ).exists()


# =============================================================================
# TestInstallAgentFrontmatter
# =============================================================================


class TestInstallAgentFrontmatter:
    """Generated agent files carry correct frontmatter."""

    def test_claude_agent_name_is_bare(self, integration_env):
        _install(integration_env, "claude-code")
        fm = _read_frontmatter(
            integration_env["project"] / ".claude" / "agents" / "code-reviewer.md"
        )
        assert fm["name"] == "code-reviewer"

    def test_claude_agent_has_model_inherit(self, integration_env):
        _install(integration_env, "claude-code")
        fm = _read_frontmatter(
            integration_env["project"] / ".claude" / "agents" / "code-reviewer.md"
        )
        assert fm["model"] == "inherit"

    def test_cursor_agent_name_is_bare(self, integration_env):
        _install(integration_env, "cursor")
        fm = _read_frontmatter(
            integration_env["project"] / ".cursor" / "agents" / "code-reviewer.md"
        )
        assert fm["name"] == "code-reviewer"

    def test_opencode_agent_has_mode_subagent(self, integration_env):
        _install(integration_env, "opencode")
        fm = _read_frontmatter(
            integration_env["project"] / ".opencode" / "agent" / "code-reviewer.md"
        )
        assert fm["mode"] == "subagent"
        assert "model" not in fm


# =============================================================================
# TestInstallMCP
# =============================================================================


class TestInstallMCP:
    """MCP servers are installed with bare (unprefixed) key names."""

    def test_claude_mcp_keys_are_bare(self, integration_env):
        _install(integration_env, "claude-code")
        mcp_file = integration_env["project"] / ".mcp.json"
        assert mcp_file.exists()
        cfg = json.loads(mcp_file.read_text())
        assert "github" in cfg["mcpServers"]
        assert "memory" in cfg["mcpServers"]
        assert not any(k.startswith("test-module") for k in cfg["mcpServers"])

    def test_opencode_mcp_keys_are_bare(self, integration_env):
        _install(integration_env, "opencode")
        mcp_file = integration_env["project"] / "opencode.json"
        assert mcp_file.exists()
        cfg = json.loads(mcp_file.read_text())
        assert "github" in cfg["mcp"]
        assert "memory" in cfg["mcp"]

    def test_registry_stores_bare_mcp_names(self, integration_env):
        _install(integration_env, "claude-code")
        inst = _find_inst(integration_env, "claude-code")
        assert sorted(inst["mcps"]) == ["github", "memory"]


# =============================================================================
# TestUninstall
# =============================================================================


class TestUninstall:
    """Uninstall removes generated files and cleans up correctly."""

    def test_command_file_removed(self, integration_env):
        _install(integration_env, "claude-code")
        cmd_file = integration_env["project"] / ".claude" / "commands" / "review-pr.md"
        assert cmd_file.exists()
        _uninstall(integration_env, "claude-code")
        assert not cmd_file.exists()

    def test_agent_file_removed(self, integration_env):
        _install(integration_env, "claude-code")
        agent_file = (
            integration_env["project"] / ".claude" / "agents" / "code-reviewer.md"
        )
        assert agent_file.exists()
        _uninstall(integration_env, "claude-code")
        assert not agent_file.exists()

    def test_mcp_config_deleted_when_all_removed(self, integration_env):
        _install(integration_env, "claude-code")
        mcp_file = integration_env["project"] / ".mcp.json"
        assert mcp_file.exists()
        _uninstall(integration_env, "claude-code")
        assert not mcp_file.exists()

    def test_partial_mcp_removal(self, integration_env):
        """Pre-remove one MCP from the config file; uninstall clears the rest."""
        _install(integration_env, "claude-code")
        mcp_file = integration_env["project"] / ".mcp.json"
        cfg = json.loads(mcp_file.read_text())
        del cfg["mcpServers"]["github"]
        mcp_file.write_text(json.dumps(cfg, indent=2))

        _uninstall(integration_env, "claude-code")
        # File should be deleted since memory was the last entry
        assert not mcp_file.exists()

    def test_registry_entry_removed(self, integration_env):
        _install(integration_env, "claude-code")
        _uninstall(integration_env, "claude-code")
        names = [i["module"] for i in _read_registry(integration_env)]
        assert "test-module" not in names


# =============================================================================
# TestUninstallLegacyFallback
# =============================================================================


class TestUninstallLegacyFallback:
    """Uninstall handles old prefixed filenames from pre-prefix-removal installs."""

    def test_removes_legacy_command_md(self, integration_env):
        _install(integration_env, "claude-code")
        cmd_dir = integration_env["project"] / ".claude" / "commands"
        # Simulate old install: rename to legacy prefixed name
        (cmd_dir / "review-pr.md").rename(cmd_dir / "test-module.review-pr.md")

        _uninstall(integration_env, "claude-code")
        assert not (cmd_dir / "test-module.review-pr.md").exists()

    def test_removes_legacy_agent_md(self, integration_env):
        _install(integration_env, "claude-code")
        agent_dir = integration_env["project"] / ".claude" / "agents"
        (agent_dir / "code-reviewer.md").rename(
            agent_dir / "test-module.code-reviewer.md"
        )

        _uninstall(integration_env, "claude-code")
        assert not (agent_dir / "test-module.code-reviewer.md").exists()

    def test_removes_legacy_gemini_toml(self, integration_env):
        _install(integration_env, "gemini-cli")
        cmd_dir = integration_env["project"] / ".gemini" / "commands"
        (cmd_dir / "review-pr.toml").rename(cmd_dir / "test-module.review-pr.toml")

        _uninstall(integration_env, "gemini-cli")
        assert not (cmd_dir / "test-module.review-pr.toml").exists()

    def test_new_style_preferred_when_both_exist(self, integration_env):
        """When both new-style and legacy files exist, new-style is removed; legacy survives."""
        _install(integration_env, "claude-code")
        cmd_dir = integration_env["project"] / ".claude" / "commands"
        # Create the legacy file alongside the new-style file
        (cmd_dir / "test-module.review-pr.md").write_text("legacy content")

        _uninstall(integration_env, "claude-code")
        assert not (cmd_dir / "review-pr.md").exists()
        assert (cmd_dir / "test-module.review-pr.md").exists()


# =============================================================================
# TestUpdateOrphans
# =============================================================================


class TestUpdateOrphans:
    """lola update removes orphaned files and installs newly added items."""

    def test_orphaned_command_removed(self, integration_env):
        _install(integration_env, "claude-code")
        (
            integration_env["modules"] / "test-module" / "commands" / "quick-commit.md"
        ).unlink()

        _update(integration_env)

        project = integration_env["project"]
        assert not (project / ".claude" / "commands" / "quick-commit.md").exists()
        assert (project / ".claude" / "commands" / "review-pr.md").exists()

    def test_orphaned_agent_removed(self, integration_env):
        _install(integration_env, "claude-code")
        (
            integration_env["modules"] / "test-module" / "agents" / "code-reviewer.md"
        ).unlink()

        _update(integration_env)

        assert not (
            integration_env["project"] / ".claude" / "agents" / "code-reviewer.md"
        ).exists()

    def test_new_command_added(self, integration_env):
        _install(integration_env, "claude-code")
        (
            integration_env["modules"] / "test-module" / "commands" / "deploy.md"
        ).write_text(
            "---\ndescription: Deploy the project\n---\n\nDeploy to: $ARGUMENTS\n"
        )

        _update(integration_env)

        assert (
            integration_env["project"] / ".claude" / "commands" / "deploy.md"
        ).exists()

    def test_new_agent_added(self, integration_env):
        _install(integration_env, "claude-code")
        (
            integration_env["modules"] / "test-module" / "agents" / "deploy-agent.md"
        ).write_text(
            "---\ndescription: Deployment agent\n---\n\nYou are a deployment expert.\n"
        )

        _update(integration_env)

        assert (
            integration_env["project"] / ".claude" / "agents" / "deploy-agent.md"
        ).exists()

    def test_registry_updated_after_orphan_removal(self, integration_env):
        _install(integration_env, "claude-code")
        (
            integration_env["modules"] / "test-module" / "agents" / "code-reviewer.md"
        ).unlink()

        _update(integration_env)

        inst = _find_inst(integration_env, "claude-code")
        assert inst["agents"] == []

    def test_orphaned_mcp_removed_from_config(self, integration_env):
        _install(integration_env, "claude-code")
        # Remove memory from source mcps.json
        mcps_file = integration_env["modules"] / "test-module" / "mcps.json"
        mcps_data = json.loads(mcps_file.read_text())
        del mcps_data["mcpServers"]["memory"]
        mcps_file.write_text(json.dumps(mcps_data, indent=2))

        _update(integration_env)

        mcp_file = integration_env["project"] / ".mcp.json"
        assert mcp_file.exists()
        cfg = json.loads(mcp_file.read_text())
        assert "github" in cfg["mcpServers"]
        assert "memory" not in cfg["mcpServers"]


# =============================================================================
# TestRegistryState
# =============================================================================


class TestRegistryState:
    """Registry YAML stores correct unprefixed names immediately after install."""

    def test_commands_stored_without_prefix(self, integration_env):
        _install(integration_env, "claude-code")
        inst = _find_inst(integration_env, "claude-code")
        assert sorted(inst["commands"]) == ["quick-commit", "review-pr"]

    def test_agents_stored_without_prefix(self, integration_env):
        _install(integration_env, "claude-code")
        inst = _find_inst(integration_env, "claude-code")
        assert inst["agents"] == ["code-reviewer"]

    def test_mcps_stored_without_prefix(self, integration_env):
        _install(integration_env, "claude-code")
        inst = _find_inst(integration_env, "claude-code")
        assert sorted(inst["mcps"]) == ["github", "memory"]
