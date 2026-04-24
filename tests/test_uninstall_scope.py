"""Tests for uninstall --scope filter functionality."""

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from lola.cli.install import uninstall_cmd
from lola.models import Installation, InstallationRegistry


class TestUninstallScopeFilter:
    """Test --scope filter for uninstall command."""

    def test_scope_option_exists(self):
        """Verify --scope option is registered on uninstall_cmd."""
        runner = CliRunner()
        result = runner.invoke(uninstall_cmd, ["--help"])
        assert result.exit_code == 0
        assert "--scope" in result.output

    def test_uninstall_filters_by_scope_user(self, mock_lola_home, tmp_path):
        """Uninstall with --scope user should only remove user-scoped installations."""
        project_path = str(tmp_path / "project")
        Path(project_path).mkdir(parents=True)

        registry = InstallationRegistry(mock_lola_home["installed"])
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
                assistant="claude-code",
                scope="project",
                project_path=project_path,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with patch("lola.cli.install.get_registry", return_value=registry):
            result = runner.invoke(
                uninstall_cmd,
                ["test-module", "--scope", "user", "-f"],
            )

        assert result.exit_code == 0

        # Verify only user-scoped installation was removed
        remaining = registry.all()
        assert len(remaining) == 1
        assert remaining[0].scope == "project"
        assert remaining[0].project_path == project_path

    def test_uninstall_filters_by_scope_project(self, mock_lola_home, tmp_path):
        """Uninstall with --scope project should only remove project-scoped installations."""
        project_path = str(tmp_path / "project")
        Path(project_path).mkdir(parents=True)

        registry = InstallationRegistry(mock_lola_home["installed"])
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
                assistant="claude-code",
                scope="project",
                project_path=project_path,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with patch("lola.cli.install.get_registry", return_value=registry):
            result = runner.invoke(
                uninstall_cmd,
                ["test-module", "--scope", "project", "-f"],
            )

        assert result.exit_code == 0

        # Verify only project-scoped installation was removed
        remaining = registry.all()
        assert len(remaining) == 1
        assert remaining[0].scope == "user"
        assert remaining[0].project_path is None

    def test_uninstall_no_scope_filter_removes_all(self, mock_lola_home, tmp_path):
        """Uninstall without --scope should remove all matching installations."""
        project_path = str(tmp_path / "project")
        Path(project_path).mkdir(parents=True)

        registry = InstallationRegistry(mock_lola_home["installed"])
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
                assistant="claude-code",
                scope="project",
                project_path=project_path,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with patch("lola.cli.install.get_registry", return_value=registry):
            result = runner.invoke(
                uninstall_cmd,
                ["test-module", "-f"],
            )

        assert result.exit_code == 0

        # Verify all installations were removed
        remaining = registry.all()
        assert len(remaining) == 0

    def test_uninstall_user_scope_not_skipped(self, mock_lola_home):
        """User scope installations (project_path=None) should NOT be skipped."""
        registry = InstallationRegistry(mock_lola_home["installed"])
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
        with patch("lola.cli.install.get_registry", return_value=registry):
            result = runner.invoke(
                uninstall_cmd,
                ["test-module", "-f"],
            )

        assert result.exit_code == 0
        # Should NOT contain "legacy entry" skip message
        assert "legacy entry" not in result.output
        # Should be properly uninstalled
        remaining = registry.all()
        assert len(remaining) == 0

    def test_uninstall_scope_no_matching(self, mock_lola_home, tmp_path):
        """Uninstall with --scope that has no matching installations shows warning."""
        project_path = str(tmp_path / "project")
        Path(project_path).mkdir(parents=True)

        registry = InstallationRegistry(mock_lola_home["installed"])
        registry.add(
            Installation(
                module_name="test-module",
                assistant="claude-code",
                scope="project",
                project_path=project_path,
                skills=["skill1"],
            )
        )

        runner = CliRunner()
        with patch("lola.cli.install.get_registry", return_value=registry):
            result = runner.invoke(
                uninstall_cmd,
                ["test-module", "--scope", "user", "-f"],
            )

        assert result.exit_code == 0
        # New improved error message shows what scope was requested
        assert (
            "not with --scope user" in result.output
            or "Found 1 installation(s)" in result.output
        )

        # Verify project installation was NOT removed
        remaining = registry.all()
        assert len(remaining) == 1
