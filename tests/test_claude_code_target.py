"""Tests for ClaudeCodeTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.claude_code import ClaudeCodeTarget


def test_claude_code_skill_path_project_scope():
    target = ClaudeCodeTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.claude/skills")


def test_claude_code_skill_path_user_scope():
    target = ClaudeCodeTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / ".claude" / "skills"


def test_claude_code_command_path_user_scope():
    target = ClaudeCodeTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".claude" / "commands"


def test_claude_code_agent_path_user_scope():
    target = ClaudeCodeTarget()
    path = target.get_agent_path("/home/user/project", "user")
    assert path == Path.home() / ".claude" / "agents"


def test_claude_code_instructions_path_user_scope():
    target = ClaudeCodeTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / ".claude" / "CLAUDE.md"


def test_claude_code_mcp_path_user_scope():
    target = ClaudeCodeTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / ".mcp.json"


# --- Project scope tests for remaining methods ---


def test_claude_code_command_path_project_scope():
    target = ClaudeCodeTarget()
    result = target.get_command_path("/home/user/project", scope="project")
    assert result == Path("/home/user/project/.claude/commands")


def test_claude_code_agent_path_project_scope():
    target = ClaudeCodeTarget()
    result = target.get_agent_path("/home/user/project", scope="project")
    assert result == Path("/home/user/project/.claude/agents")


def test_claude_code_instructions_path_project_scope():
    target = ClaudeCodeTarget()
    result = target.get_instructions_path("/home/user/project", scope="project")
    assert result == Path("/home/user/project/CLAUDE.md")


def test_claude_code_mcp_path_project_scope():
    target = ClaudeCodeTarget()
    result = target.get_mcp_path("/home/user/project", scope="project")
    assert result == Path("/home/user/project/.mcp.json")


# --- Default scope tests (no explicit scope argument) ---


def test_claude_code_skill_path_default_scope():
    target = ClaudeCodeTarget()
    result = target.get_skill_path("/home/user/project")
    assert result == Path("/home/user/project/.claude/skills")


def test_claude_code_command_path_default_scope():
    target = ClaudeCodeTarget()
    result = target.get_command_path("/home/user/project")
    assert result == Path("/home/user/project/.claude/commands")


def test_claude_code_agent_path_default_scope():
    target = ClaudeCodeTarget()
    result = target.get_agent_path("/home/user/project")
    assert result == Path("/home/user/project/.claude/agents")


def test_claude_code_instructions_path_default_scope():
    target = ClaudeCodeTarget()
    result = target.get_instructions_path("/home/user/project")
    assert result == Path("/home/user/project/CLAUDE.md")


def test_claude_code_mcp_path_default_scope():
    target = ClaudeCodeTarget()
    result = target.get_mcp_path("/home/user/project")
    assert result == Path("/home/user/project/.mcp.json")
