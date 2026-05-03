"""Integration tests for scoped installation flow.

These tests verify the end-to-end install workflow for both user and project
scopes, including file creation in the correct locations and registry records.
"""

import shutil
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from lola.cli.install import install_cmd
from lola.models import InstallationRegistry


@pytest.fixture
def isolated_lola_home(monkeypatch, tmp_path):
    """Create isolated lola home for testing."""
    lola_home = tmp_path / ".lola"
    lola_home.mkdir()
    (lola_home / "modules").mkdir()

    monkeypatch.setattr("lola.config.LOLA_HOME", lola_home)
    monkeypatch.setattr("lola.config.MODULES_DIR", lola_home / "modules")
    monkeypatch.setattr("lola.config.INSTALLED_FILE", lola_home / "installed.yml")

    # Patch from-imports in modules that use them
    monkeypatch.setattr("lola.cli.install.MODULES_DIR", lola_home / "modules")
    monkeypatch.setattr("lola.utils.LOLA_HOME", lola_home)
    monkeypatch.setattr("lola.utils.MODULES_DIR", lola_home / "modules")

    return lola_home


@pytest.fixture
def sample_module(tmp_path):
    """Create a sample module with a skill."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)

    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        "name: test-skill\n"
        "description: A test skill\n"
        "---\n"
        "\n"
        "# Test Skill\n"
        "\n"
        "This is a test skill.\n"
    )

    return module_dir


def test_install_user_scope_creates_files_in_home(
    isolated_lola_home, sample_module, tmp_path
):
    """Installing with user scope should create files in home directory."""
    runner = CliRunner()

    # Register the module first
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    # Use a fake home directory to avoid polluting real home
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()

    with patch("pathlib.Path.home", return_value=fake_home):
        result = runner.invoke(
            install_cmd,
            ["test-module", "--scope", "user", "-a", "claude-code"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0

    # Verify files created in fake home directory
    skill_file = fake_home / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert skill_file.exists(), (
        f"Expected skill file at {skill_file}, but it does not exist"
    )

    # Verify installation record has scope=user, project_path=None
    registry = InstallationRegistry(isolated_lola_home / "installed.yml")
    installations = registry.all()
    assert len(installations) == 1
    assert installations[0].scope == "user"
    assert installations[0].project_path is None
    assert installations[0].module_name == "test-module"
    assert installations[0].assistant == "claude-code"
    assert "test-skill" in installations[0].skills


def test_install_project_scope_creates_files_in_project(
    isolated_lola_home, sample_module, tmp_path
):
    """Installing with project scope should create files in project directory."""
    runner = CliRunner()

    # Register the module
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    result = runner.invoke(
        install_cmd,
        [
            "test-module",
            "--scope",
            "project",
            "-a",
            "claude-code",
            str(project_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0

    # Verify files created in project directory
    skill_file = project_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert skill_file.exists(), (
        f"Expected skill file at {skill_file}, but it does not exist"
    )

    # Verify installation record
    registry = InstallationRegistry(isolated_lola_home / "installed.yml")
    installations = registry.all()
    assert len(installations) == 1
    assert installations[0].scope == "project"
    assert installations[0].project_path == str(project_dir)
    assert installations[0].module_name == "test-module"
    assert installations[0].assistant == "claude-code"
    assert "test-skill" in installations[0].skills


def test_install_user_scope_with_explicit_path_fails(
    isolated_lola_home, sample_module, tmp_path
):
    """User scope with explicit path should fail validation."""
    runner = CliRunner()

    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    result = runner.invoke(
        install_cmd,
        [
            "test-module",
            "--scope",
            "user",
            "-a",
            "claude-code",
            str(project_dir),
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "cannot be used with a project path argument" in result.output


def test_install_both_scopes_coexist(isolated_lola_home, sample_module, tmp_path):
    """Installing same module in both scopes should work."""
    runner = CliRunner()

    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    # Use a fake home directory to avoid polluting real home
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()

    # Install user scope
    with patch("pathlib.Path.home", return_value=fake_home):
        result1 = runner.invoke(
            install_cmd,
            ["test-module", "--scope", "user", "-a", "claude-code"],
            catch_exceptions=False,
        )
    assert result1.exit_code == 0

    # Install project scope
    project_dir = tmp_path / "my-project"
    project_dir.mkdir()

    result2 = runner.invoke(
        install_cmd,
        [
            "test-module",
            "--scope",
            "project",
            "-a",
            "claude-code",
            str(project_dir),
        ],
        catch_exceptions=False,
    )
    assert result2.exit_code == 0

    # Verify both installations exist in registry
    registry = InstallationRegistry(isolated_lola_home / "installed.yml")
    installations = registry.all()
    assert len(installations) == 2

    scopes = {inst.scope for inst in installations}
    assert scopes == {"user", "project"}

    # Verify user scope record
    user_insts = [inst for inst in installations if inst.scope == "user"]
    assert len(user_insts) == 1
    assert user_insts[0].project_path is None
    assert user_insts[0].module_name == "test-module"

    # Verify project scope record
    project_insts = [inst for inst in installations if inst.scope == "project"]
    assert len(project_insts) == 1
    assert project_insts[0].project_path == str(project_dir)
    assert project_insts[0].module_name == "test-module"

    # Verify files exist in both locations
    user_skill = fake_home / ".claude" / "skills" / "test-skill" / "SKILL.md"
    project_skill = project_dir / ".claude" / "skills" / "test-skill" / "SKILL.md"
    assert user_skill.exists(), f"Expected user scope skill file at {user_skill}"
    assert project_skill.exists(), (
        f"Expected project scope skill file at {project_skill}"
    )
