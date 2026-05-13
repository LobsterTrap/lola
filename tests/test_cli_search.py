"""Tests for the top-level `lola search` CLI command."""

import pytest
import yaml

from lola.cli.search import search_cmd


@pytest.fixture
def search_env(tmp_path, monkeypatch):
    """Patch MARKET_DIR/CACHE_DIR for `lola search` and yield the dirs."""
    market_dir = tmp_path / "market"
    cache_dir = market_dir / "cache"
    market_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)

    monkeypatch.setattr("lola.cli.search.MARKET_DIR", market_dir)
    monkeypatch.setattr("lola.cli.search.CACHE_DIR", cache_dir)

    return market_dir, cache_dir


def _write_marketplace(market_dir, cache_dir, name="official", modules=None):
    """Create a minimal enabled marketplace with the given modules."""
    if modules is None:
        modules = [
            {
                "name": "git-tools",
                "description": "Git utilities",
                "version": "1.0.0",
                "repository": "https://github.com/test/git-tools.git",
                "tags": ["git", "vcs"],
            },
            {
                "name": "python-utils",
                "description": "Python helpers",
                "version": "1.2.0",
                "repository": "https://github.com/test/python-utils.git",
                "tags": ["python"],
            },
        ]

    ref = {
        "name": name,
        "url": f"https://example.com/{name}.yml",
        "enabled": True,
    }
    cache = {
        "name": name.title(),
        "description": f"{name} catalog",
        "version": "1.0.0",
        "url": f"https://example.com/{name}.yml",
        "enabled": True,
        "modules": modules,
    }

    with open(market_dir / f"{name}.yml", "w") as f:
        yaml.dump(ref, f)
    with open(cache_dir / f"{name}.yml", "w") as f:
        yaml.dump(cache, f)


class TestSearchHelp:
    """Tests for the search command help/registration."""

    def test_search_help(self, cli_runner):
        """Show search help."""
        result = cli_runner.invoke(search_cmd, ["--help"])
        assert result.exit_code == 0
        assert "Search modules" in result.output
        assert "--local" in result.output
        assert "--remote" in result.output

    def test_search_requires_query(self, cli_runner, mock_lola_home):
        """Fail when query argument missing."""
        result = cli_runner.invoke(search_cmd, [])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage" in result.output

    def test_search_registered_on_main(self):
        """Top-level `lola search` is wired up via __main__."""
        from lola.__main__ import main

        assert "search" in main.commands


class TestSearchLocal:
    """Tests for local registry search."""

    def test_finds_module_by_name(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """Match a local module by its name."""
        result = cli_runner.invoke(search_cmd, ["sample"])

        assert result.exit_code == 0
        assert "Local registry" in result.output
        assert "sample-module" in result.output
        assert "1 skill" in result.output
        assert "1 command" in result.output
        assert "1 agent" in result.output

    def test_finds_module_by_skill_name(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """Match a local module by the name of one of its skills."""
        result = cli_runner.invoke(search_cmd, ["skill1"])

        assert result.exit_code == 0
        assert "sample-module" in result.output

    def test_finds_module_by_command_name(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """Match a local module by the name of one of its commands."""
        result = cli_runner.invoke(search_cmd, ["cmd1"])

        assert result.exit_code == 0
        assert "sample-module" in result.output

    def test_finds_module_by_agent_name(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """Match a local module by the name of one of its agents."""
        result = cli_runner.invoke(search_cmd, ["agent1"])

        assert result.exit_code == 0
        assert "sample-module" in result.output

    def test_local_match_is_case_insensitive(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """Local search matches case-insensitively."""
        result = cli_runner.invoke(search_cmd, ["SAMPLE"])

        assert result.exit_code == 0
        assert "sample-module" in result.output


class TestSearchRemote:
    """Tests for marketplace (remote) search."""

    def test_finds_remote_module(self, cli_runner, mock_lola_home, search_env):
        """Match a marketplace module by name."""
        market_dir, cache_dir = search_env
        _write_marketplace(market_dir, cache_dir)

        result = cli_runner.invoke(search_cmd, ["git"])

        assert result.exit_code == 0
        assert "Marketplaces" in result.output
        assert "git-tools" in result.output
        assert "official" in result.output

    def test_remote_match_by_tag(self, cli_runner, mock_lola_home, search_env):
        """Match a marketplace module by tag."""
        market_dir, cache_dir = search_env
        _write_marketplace(market_dir, cache_dir)

        result = cli_runner.invoke(search_cmd, ["vcs"])

        assert result.exit_code == 0
        assert "git-tools" in result.output


class TestSearchScopeFlags:
    """Tests for --local and --remote flags."""

    def test_local_flag_skips_marketplaces(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """--local restricts search to the local registry."""
        market_dir, cache_dir = search_env
        _write_marketplace(market_dir, cache_dir)

        # "git" only matches the marketplace module; --local must filter it out
        result = cli_runner.invoke(search_cmd, ["git", "--local"])

        assert result.exit_code == 0
        assert "Marketplaces" not in result.output
        assert "git-tools" not in result.output

    def test_remote_flag_skips_local(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """--remote restricts search to enabled marketplaces."""
        market_dir, cache_dir = search_env
        _write_marketplace(market_dir, cache_dir)

        # "sample" only matches the local module; --remote must filter it out
        result = cli_runner.invoke(search_cmd, ["sample", "--remote"])

        assert result.exit_code == 0
        assert "Local registry" not in result.output
        assert "sample-module" not in result.output

    def test_default_searches_both_scopes(
        self, cli_runner, mock_lola_home, registered_module, search_env
    ):
        """With no flag, both local and remote are searched."""
        market_dir, cache_dir = search_env
        _write_marketplace(
            market_dir,
            cache_dir,
            modules=[
                {
                    "name": "sample-remote",
                    "description": "Sample remote",
                    "version": "1.0.0",
                    "repository": "https://example.com/sample.git",
                }
            ],
        )

        result = cli_runner.invoke(search_cmd, ["sample"])

        assert result.exit_code == 0
        assert "Local registry" in result.output
        assert "sample-module" in result.output
        assert "Marketplaces" in result.output
        assert "sample-remote" in result.output


class TestSearchNoMatches:
    """Tests for the empty-results path."""

    def test_no_match_default_scope(self, cli_runner, mock_lola_home, search_env):
        """Show generic tip when neither scope matches."""
        result = cli_runner.invoke(search_cmd, ["definitely-not-a-module"])

        assert result.exit_code == 0
        assert "No modules found" in result.output
        assert "definitely-not-a-module" in result.output
        assert "check spelling" in result.output

    def test_no_match_local_only_tip(self, cli_runner, mock_lola_home, search_env):
        """Show 'drop --local' hint when --local yields nothing."""
        result = cli_runner.invoke(search_cmd, ["anything", "--local"])

        assert result.exit_code == 0
        assert "No modules found" in result.output
        assert "drop --local" in result.output

    def test_no_match_remote_only_tip(self, cli_runner, mock_lola_home, search_env):
        """Show 'drop --remote' hint when --remote yields nothing."""
        result = cli_runner.invoke(search_cmd, ["anything", "--remote"])

        assert result.exit_code == 0
        assert "No modules found" in result.output
        assert "drop --remote" in result.output


class TestSearchRemoved:
    """Tests for behavior that the refactor removed."""

    def test_mod_search_subcommand_removed(self, cli_runner, mock_lola_home):
        """`lola mod search` is no longer a registered subcommand."""
        from lola.cli.mod import mod

        assert "search" not in mod.commands

        result = cli_runner.invoke(mod, ["search", "anything"])
        assert result.exit_code != 0
