"""Tests for OpenClawTarget scope-aware path resolution."""

from pathlib import Path

from lola.targets.openclaw import OpenClawTarget


# --- User scope tests ---


def test_openclaw_skill_path_user_scope():
    target = OpenClawTarget()
    path = target.get_skill_path("/home/user/project", "user")
    assert path == Path.home() / ".openclaw" / "workspace" / "skills"


def test_openclaw_command_path_user_scope():
    target = OpenClawTarget()
    path = target.get_command_path("/home/user/project", "user")
    assert path == Path.home() / ".openclaw" / "workspace" / "commands"


def test_openclaw_instructions_path_user_scope():
    target = OpenClawTarget()
    path = target.get_instructions_path("/home/user/project", "user")
    assert path == Path.home() / ".openclaw" / "workspace" / "instructions.md"


# --- Project scope tests ---


def test_openclaw_skill_path_project_scope():
    target = OpenClawTarget()
    path = target.get_skill_path("/home/user/project", "project")
    assert path == Path("/home/user/project/skills")


def test_openclaw_command_path_project_scope():
    target = OpenClawTarget()
    path = target.get_command_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.openclaw/commands")


def test_openclaw_instructions_path_project_scope():
    target = OpenClawTarget()
    path = target.get_instructions_path("/home/user/project", "project")
    assert path == Path("/home/user/project/.openclaw/instructions.md")


# --- Default scope tests (no explicit scope argument) ---


def test_openclaw_skill_path_default_scope():
    target = OpenClawTarget()
    result = target.get_skill_path("/home/user/project")
    assert result == Path("/home/user/project/skills")


def test_openclaw_command_path_default_scope():
    target = OpenClawTarget()
    result = target.get_command_path("/home/user/project")
    assert result == Path("/home/user/project/.openclaw/commands")


def test_openclaw_instructions_path_default_scope():
    target = OpenClawTarget()
    result = target.get_instructions_path("/home/user/project")
    assert result == Path("/home/user/project/.openclaw/instructions.md")
