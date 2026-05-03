"""Tests for GeminiTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.gemini import GeminiTarget


# --- User scope tests ---


def test_gemini_command_path_user_scope():
    target = GeminiTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".gemini" / "commands"


def test_gemini_instructions_path_user_scope():
    target = GeminiTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / "GEMINI.md"


def test_gemini_mcp_path_user_scope():
    target = GeminiTarget()
    path = target.get_mcp_path("/home/user/project", "user")
    assert path == Path.home() / ".gemini" / "settings.json"


def test_gemini_skill_path_user_scope_from_managed_section():
    """GeminiTarget inherits from ManagedSectionTarget which has get_skill_path."""
    target = GeminiTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / "GEMINI.md"


# --- Project scope tests ---


def test_gemini_command_path_project_scope():
    target = GeminiTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.gemini/commands")


def test_gemini_instructions_path_project_scope():
    target = GeminiTarget()
    path = target.get_instructions_path("/home/user/project", "project")
    assert path == Path("/home/user/project/GEMINI.md")


def test_gemini_mcp_path_project_scope():
    target = GeminiTarget()
    path = target.get_mcp_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.gemini/settings.json")


def test_gemini_skill_path_project_scope():
    target = GeminiTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/GEMINI.md")


# --- Default scope tests (no explicit scope argument) ---


def test_gemini_command_path_default_scope():
    target = GeminiTarget()
    result = target.get_command_path("/home/user/project")
    assert result == Path("/home/user/project/.gemini/commands")


def test_gemini_instructions_path_default_scope():
    target = GeminiTarget()
    result = target.get_instructions_path("/home/user/project")
    assert result == Path("/home/user/project/GEMINI.md")


def test_gemini_mcp_path_default_scope():
    target = GeminiTarget()
    result = target.get_mcp_path("/home/user/project")
    assert result == Path("/home/user/project/.gemini/settings.json")


def test_gemini_skill_path_default_scope():
    target = GeminiTarget()
    result = target.get_skill_path("/home/user/project")
    assert result == Path("/home/user/project/GEMINI.md")
