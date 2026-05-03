"""Tests for scope display in the list command."""

from unittest.mock import patch

from click.testing import CliRunner

from lola.cli.install import list_installed_cmd
from lola.models import Installation, InstallationRegistry


class TestListShowsScope:
    """Tests that list command displays scope information."""

    def test_list_shows_user_scope(self, tmp_path):
        """List command should display 'scope: user' for user-scoped installations."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        assert "test-module" in result.output
        assert "scope:" in result.output
        assert "user" in result.output
        assert "claude-code" in result.output

    def test_list_shows_project_scope_with_path(self, tmp_path):
        """List command should display scope and path for project-scoped installations."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        project_path = "/home/user/project"
        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="test-module",
                assistant="cursor",
                scope="project",
                project_path=project_path,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        assert "test-module" in result.output
        assert "scope:" in result.output
        assert "project" in result.output
        assert "path:" in result.output
        assert project_path in result.output
        assert "cursor" in result.output

    def test_list_user_scope_no_path_shown(self, tmp_path):
        """User scope installations should not show path."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        assert "path:" not in result.output

    def test_list_groups_by_scope_and_path(self, tmp_path):
        """List groups installations by (scope, project_path) and consolidates assistants."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        registry = InstallationRegistry(installed_file)
        # Two user-scope installations for different assistants
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )
        registry.add(
            Installation(
                module_name="test-module",
                assistant="cursor",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )
        # One project-scope installation
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="project",
                project_path="/home/user/project",
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        # Should show one module header
        assert "Installed (1 module)" in result.output
        # Should show both scopes
        assert "user" in result.output
        assert "project" in result.output
        # User scope should consolidate both assistants
        assert "claude-code, cursor" in result.output

    def test_list_assistants_sorted_alphabetically(self, tmp_path):
        """Assistants within a scope group should be sorted alphabetically."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        registry = InstallationRegistry(installed_file)
        # Add in reverse alphabetical order
        registry.add(
            Installation(
                module_name="test-module",
                assistant="cursor",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        # claude-code should come before cursor alphabetically
        assert "claude-code, cursor" in result.output

    def test_list_multiple_modules_with_mixed_scopes(self, tmp_path):
        """Multiple modules with different scopes display correctly."""
        installed_file = tmp_path / ".lola" / "installed.yml"
        installed_file.parent.mkdir(parents=True)

        registry = InstallationRegistry(installed_file)
        registry.add(
            Installation(
                module_name="module-a",
                assistant="claude-code",
                scope="user",
                project_path=None,
                skills=["skill1"],
            )
        )
        registry.add(
            Installation(
                module_name="module-b",
                assistant="cursor",
                scope="project",
                project_path="/home/user/myapp",
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with (
            patch("lola.cli.install.ensure_lola_dirs"),
            patch("lola.cli.install.get_registry", return_value=registry),
        ):
            result = runner.invoke(list_installed_cmd, [])

        assert result.exit_code == 0
        assert "Installed (2 modules)" in result.output
        assert "module-a" in result.output
        assert "module-b" in result.output
        assert "/home/user/myapp" in result.output
