"""Integration tests for scoped installation flow.

These tests verify the end-to-end install workflow for both user and project
scopes, including file creation in the correct locations and registry records.
"""

import os
import shutil
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from lola.cli.install import install_cmd, uninstall_cmd, update_cmd
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


def test_user_scope_install_records_cache_path(
    isolated_lola_home, sample_module, tmp_path
):
    """User-scope install records the cwd-based cache path for later cleanup."""
    runner = CliRunner()
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    install_cwd = tmp_path / "install-cwd"
    install_cwd.mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(install_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            result = runner.invoke(
                install_cmd,
                ["test-module", "--scope", "user", "-a", "claude-code"],
                catch_exceptions=False,
            )
    finally:
        os.chdir(old_cwd)

    assert result.exit_code == 0

    registry = InstallationRegistry(isolated_lola_home / "installed.yml")
    insts = registry.all()
    assert len(insts) == 1
    expected_cache = install_cwd.resolve() / ".lola" / "modules" / "test-module"
    assert insts[0].cache_key is not None
    assert [cache.path for cache in registry.module_caches()] == [str(expected_cache)]

    # Local module copy actually exists at the recorded location.
    assert expected_cache.exists()


def test_user_scope_uninstall_removes_cache_from_different_cwd(
    isolated_lola_home, sample_module, tmp_path
):
    """Bug #1 regression: uninstall run from a different cwd than the install
    must still find and remove the original cache via the v2 cache record."""
    runner = CliRunner()
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    install_cwd = tmp_path / "install-cwd"
    install_cwd.mkdir()
    uninstall_cwd = tmp_path / "elsewhere"
    uninstall_cwd.mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(install_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            install_result = runner.invoke(
                install_cmd,
                ["test-module", "--scope", "user", "-a", "claude-code"],
                catch_exceptions=False,
            )
        assert install_result.exit_code == 0

        original_copy = install_cwd / ".lola" / "modules" / "test-module"
        assert original_copy.exists()

        # Now run uninstall from a totally different directory.
        os.chdir(uninstall_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            uninstall_result = runner.invoke(
                uninstall_cmd,
                ["test-module", "-f"],
                catch_exceptions=False,
            )
    finally:
        os.chdir(old_cwd)

    assert uninstall_result.exit_code == 0
    # Original local copy is gone (the fix).
    assert not original_copy.exists()


def test_user_scope_uninstall_from_different_cwd_does_not_touch_unrelated_symlink(
    isolated_lola_home, sample_module, tmp_path
):
    """A same-named symlink in the uninstall cwd must NOT be deleted — the old
    code did exactly that. Verify the recorded path is used instead."""
    runner = CliRunner()
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    install_cwd = tmp_path / "install-cwd"
    install_cwd.mkdir()
    uninstall_cwd = tmp_path / "elsewhere"
    uninstall_cwd.mkdir()

    # Plant an unrelated same-named symlink at uninstall_cwd/.lola/modules/.
    decoy_target = tmp_path / "decoy-target"
    decoy_target.mkdir()
    decoy_modules = uninstall_cwd / ".lola" / "modules"
    decoy_modules.mkdir(parents=True)
    decoy_symlink = decoy_modules / "test-module"
    decoy_symlink.symlink_to(decoy_target)

    old_cwd = os.getcwd()
    try:
        os.chdir(install_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            runner.invoke(
                install_cmd,
                ["test-module", "--scope", "user", "-a", "claude-code"],
                catch_exceptions=False,
            )

        os.chdir(uninstall_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            runner.invoke(
                uninstall_cmd,
                ["test-module", "-f"],
                catch_exceptions=False,
            )
    finally:
        os.chdir(old_cwd)

    # Decoy is untouched.
    assert decoy_symlink.is_symlink()
    assert decoy_symlink.resolve() == decoy_target.resolve()
    # Original is gone.
    original_symlink = install_cwd / ".lola" / "modules" / "test-module"
    assert not original_symlink.exists()


def test_user_scope_update_reuses_recorded_cache_from_different_cwd(
    isolated_lola_home, sample_module, tmp_path
):
    """User-scope update refreshes the install-time cache, not the current cwd."""
    runner = CliRunner()
    registered = isolated_lola_home / "modules" / "test-module"
    shutil.copytree(sample_module, registered)

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    install_cwd = tmp_path / "install-cwd"
    install_cwd.mkdir()
    update_cwd = tmp_path / "update-cwd"
    update_cwd.mkdir()

    old_cwd = os.getcwd()
    try:
        os.chdir(install_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            install_result = runner.invoke(
                install_cmd,
                ["test-module", "--scope", "user", "-a", "claude-code"],
                catch_exceptions=False,
            )
        assert install_result.exit_code == 0

        registered_skill = registered / "skills" / "test-skill" / "SKILL.md"
        registered_skill.write_text(
            "---\n"
            "name: test-skill\n"
            "description: A changed test skill\n"
            "---\n"
            "\n"
            "# Changed\n"
        )

        os.chdir(update_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            update_result = runner.invoke(
                update_cmd,
                ["test-module"],
                catch_exceptions=False,
            )
    finally:
        os.chdir(old_cwd)

    assert update_result.exit_code == 0, update_result.output
    original_cache_skill = (
        install_cwd
        / ".lola"
        / "modules"
        / "test-module"
        / "skills"
        / "test-skill"
        / "SKILL.md"
    )
    assert "# Changed" in original_cache_skill.read_text()
    assert not (update_cwd / ".lola" / "modules" / "test-module").exists()


def test_filtered_uninstall_keeps_cache_when_other_assistant_references_it(
    isolated_lola_home, sample_module, tmp_path
):
    """Uninstalling one assistant leaves the shared project cache in place."""
    runner = CliRunner()
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    for assistant in ("claude-code", "cursor"):
        result = runner.invoke(
            install_cmd,
            ["test-module", str(project_dir), "-a", assistant],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

    cache_path = project_dir / ".lola" / "modules" / "test-module"
    assert cache_path.exists()

    uninstall_result = runner.invoke(
        uninstall_cmd,
        ["test-module", str(project_dir), "-a", "claude-code", "-f"],
        catch_exceptions=False,
    )

    assert uninstall_result.exit_code == 0, uninstall_result.output
    assert cache_path.exists()
    registry = InstallationRegistry(isolated_lola_home / "installed.yml")
    remaining = registry.all()
    assert len(remaining) == 1
    assert remaining[0].assistant == "cursor"
    assert [cache.path for cache in registry.module_caches()] == [str(cache_path)]


def test_uninstall_legacy_record_without_user_symlink_dir_does_not_crash(
    isolated_lola_home, sample_module, tmp_path
):
    """Old user records without cache path metadata uninstall without guessing."""
    runner = CliRunner()
    shutil.copytree(sample_module, isolated_lola_home / "modules" / "test-module")

    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    registry_path = isolated_lola_home / "installed.yml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "installations": [
                    {
                        "module": "test-module",
                        "assistant": "claude-code",
                        "scope": "user",
                        "skills": ["test-skill"],
                    }
                ],
            }
        )
    )
    skill_dest = fake_home / ".claude" / "skills" / "test-skill"
    skill_dest.mkdir(parents=True)
    (skill_dest / "SKILL.md").write_text("content")

    old_cwd = os.getcwd()
    try:
        # Plant a decoy symlink in a fresh uninstall cwd — the legacy path
        # must NOT delete it (the old bug would).
        uninstall_cwd = tmp_path / "elsewhere"
        uninstall_cwd.mkdir()
        decoy_target = tmp_path / "decoy-target"
        decoy_target.mkdir()
        decoy_modules = uninstall_cwd / ".lola" / "modules"
        decoy_modules.mkdir(parents=True)
        decoy_symlink = decoy_modules / "test-module"
        decoy_symlink.symlink_to(decoy_target)

        os.chdir(uninstall_cwd)
        with patch("pathlib.Path.home", return_value=fake_home):
            uninstall_result = runner.invoke(
                uninstall_cmd,
                ["test-module", "-f"],
                catch_exceptions=False,
            )
    finally:
        os.chdir(old_cwd)

    assert uninstall_result.exit_code == 0
    # Decoy untouched.
    assert decoy_symlink.is_symlink()
    assert decoy_symlink.resolve() == decoy_target.resolve()
