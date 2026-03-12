"""Tests for shell completion support."""

from unittest.mock import patch

from lola.__main__ import main
from lola.cli.completions import (
    complete_module_names,
    complete_marketplace_names,
    complete_installed_module_names,
)


class TestCompletionsCommand:
    """Tests for the 'lola completions' command."""

    def test_completions_bash(self, cli_runner):
        """Generate bash completion script."""
        result = cli_runner.invoke(main, ["completions", "bash"])
        assert result.exit_code == 0
        assert "_LOLA_COMPLETE" in result.output
        assert "bash" in result.output.lower()

    def test_completions_zsh(self, cli_runner):
        """Generate zsh completion script."""
        result = cli_runner.invoke(main, ["completions", "zsh"])
        assert result.exit_code == 0
        assert "_LOLA_COMPLETE" in result.output
        assert "zsh" in result.output.lower()

    def test_completions_fish(self, cli_runner):
        """Generate fish completion script."""
        result = cli_runner.invoke(main, ["completions", "fish"])
        assert result.exit_code == 0
        assert "lola" in result.output

    def test_completions_invalid_shell(self, cli_runner):
        """Reject invalid shell argument."""
        result = cli_runner.invoke(main, ["completions", "powershell"])
        assert result.exit_code != 0
        assert (
            "Invalid value" in result.output
            or "invalid choice" in result.output.lower()
        )

    def test_completions_help(self, cli_runner):
        """Show completions help."""
        result = cli_runner.invoke(main, ["completions", "--help"])
        assert result.exit_code == 0
        assert "Generate shell completion script" in result.output
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output


class TestModuleNamesCompletion:
    """Tests for complete_module_names callback."""

    def test_complete_module_names_no_modules_dir(self):
        """Return empty list when MODULES_DIR doesn't exist."""
        with patch("lola.cli.completions.MODULES_DIR") as mock_dir:
            mock_dir.exists.return_value = False
            result = complete_module_names(None, None, "")
            assert result == []

    def test_complete_module_names_with_modules(self, tmp_path):
        """Return module names from MODULES_DIR."""
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        (modules_dir / "module-one").mkdir()
        (modules_dir / "module-two").mkdir()
        (modules_dir / "other-module").mkdir()
        # Create a file to ensure only directories are returned
        (modules_dir / "file.txt").write_text("not a module")

        with patch("lola.cli.completions.MODULES_DIR", modules_dir):
            result = complete_module_names(None, None, "")
            assert len(result) == 3
            names = [item.value for item in result]
            assert "module-one" in names
            assert "module-two" in names
            assert "other-module" in names

    def test_complete_module_names_with_prefix(self, tmp_path):
        """Filter module names by prefix."""
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        (modules_dir / "module-one").mkdir()
        (modules_dir / "module-two").mkdir()
        (modules_dir / "other-module").mkdir()

        with patch("lola.cli.completions.MODULES_DIR", modules_dir):
            result = complete_module_names(None, None, "module-")
            assert len(result) == 2
            names = [item.value for item in result]
            assert "module-one" in names
            assert "module-two" in names
            assert "other-module" not in names

    def test_complete_module_names_handles_exception(self):
        """Return empty list when MODULES_DIR iteration raises an exception."""
        with patch("lola.cli.completions.MODULES_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.iterdir.side_effect = PermissionError("Access denied")
            result = complete_module_names(None, None, "")
            assert result == []


class TestMarketplaceNamesCompletion:
    """Tests for complete_marketplace_names callback."""

    def test_complete_marketplace_names_no_market_dir(self):
        """Return empty list when MARKET_DIR doesn't exist."""
        with patch("lola.cli.completions.MARKET_DIR") as mock_dir:
            mock_dir.exists.return_value = False
            result = complete_marketplace_names(None, None, "")
            assert result == []

    def test_complete_marketplace_names_with_marketplaces(self, tmp_path):
        """Return marketplace names from MARKET_DIR/*.yml files."""
        market_dir = tmp_path / "market"
        market_dir.mkdir()
        (market_dir / "official.yml").write_text(
            "enabled: true\nurl: http://example.com"
        )
        (market_dir / "community.yml").write_text(
            "enabled: true\nurl: http://example.com"
        )
        (market_dir / "test.yml").write_text("enabled: false\nurl: http://example.com")
        # Create a non-yml file to ensure only .yml files are returned
        (market_dir / "readme.txt").write_text("not a marketplace")

        with patch("lola.cli.completions.MARKET_DIR", market_dir):
            result = complete_marketplace_names(None, None, "")
            assert len(result) == 3
            names = [item.value for item in result]
            assert "official" in names
            assert "community" in names
            assert "test" in names

    def test_complete_marketplace_names_with_prefix(self, tmp_path):
        """Filter marketplace names by prefix."""
        market_dir = tmp_path / "market"
        market_dir.mkdir()
        (market_dir / "official.yml").write_text(
            "enabled: true\nurl: http://example.com"
        )
        (market_dir / "community.yml").write_text(
            "enabled: true\nurl: http://example.com"
        )

        with patch("lola.cli.completions.MARKET_DIR", market_dir):
            result = complete_marketplace_names(None, None, "off")
            assert len(result) == 1
            assert result[0].value == "official"

    def test_complete_marketplace_names_handles_exception(self):
        """Return empty list when MARKET_DIR glob raises an exception."""
        with patch("lola.cli.completions.MARKET_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.glob.side_effect = PermissionError("Access denied")
            result = complete_marketplace_names(None, None, "")
            assert result == []


class TestInstalledModuleNamesCompletion:
    """Tests for complete_installed_module_names callback."""

    def test_complete_installed_module_names_no_file(self):
        """Return empty list when INSTALLED_FILE doesn't exist."""
        with patch("lola.cli.completions.INSTALLED_FILE") as mock_file:
            mock_file.exists.return_value = False
            result = complete_installed_module_names(None, None, "")
            assert result == []

    def test_complete_installed_module_names_with_modules(self, tmp_path):
        """Return installed module names from InstallationRegistry."""
        installed_file = tmp_path / "installed.yml"
        installed_file.write_text("""version: "1.0"
installations:
  - module: module-one
    assistant: claude-code
    scope: user
    project_path: /tmp/project
    skills: []
    commands: []
    agents: []
    mcps: []
    has_instructions: false
  - module: module-two
    assistant: cursor
    scope: user
    project_path: /tmp/project
    skills: []
    commands: []
    agents: []
    mcps: []
    has_instructions: false
""")

        with patch("lola.cli.completions.INSTALLED_FILE", installed_file):
            result = complete_installed_module_names(None, None, "")
            assert len(result) == 2
            names = [item.value for item in result]
            assert "module-one" in names
            assert "module-two" in names

    def test_complete_installed_module_names_with_prefix(self, tmp_path):
        """Filter installed module names by prefix."""
        installed_file = tmp_path / "installed.yml"
        installed_file.write_text("""version: "1.0"
installations:
  - module: module-one
    assistant: claude-code
    scope: user
    project_path: /tmp/project
    skills: []
    commands: []
    agents: []
    mcps: []
    has_instructions: false
  - module: module-two
    assistant: cursor
    scope: user
    project_path: /tmp/project
    skills: []
    commands: []
    agents: []
    mcps: []
    has_instructions: false
  - module: other-module
    assistant: gemini-cli
    scope: user
    project_path: /tmp/project
    skills: []
    commands: []
    agents: []
    mcps: []
    has_instructions: false
""")

        with patch("lola.cli.completions.INSTALLED_FILE", installed_file):
            result = complete_installed_module_names(None, None, "module-")
            assert len(result) == 2
            names = [item.value for item in result]
            assert "module-one" in names
            assert "module-two" in names
            assert "other-module" not in names

    def test_complete_installed_module_names_invalid_file(self, tmp_path):
        """Return empty list when InstallationRegistry can't be loaded."""
        installed_file = tmp_path / "installed.yml"
        installed_file.write_text("invalid yaml content: [")

        with patch("lola.cli.completions.INSTALLED_FILE", installed_file):
            result = complete_installed_module_names(None, None, "")
            # Should handle exception gracefully
            assert result == []
