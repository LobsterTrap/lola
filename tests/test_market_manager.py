"""Tests for the MarketplaceRegistry manager."""

from unittest.mock import patch, mock_open

import yaml

from lola.models import Marketplace
from lola.market.manager import MarketplaceRegistry, parse_ref_suffix


class TestMarketplaceRegistryAdd:
    """Tests for MarketplaceRegistry.add()."""

    def test_registry_add_success(self, tmp_path):
        """Add marketplace successfully."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        yaml_content = (
            "name: Test Marketplace\n"
            "description: Test catalog\n"
            "version: 1.0.0\n"
            "modules:\n"
            "  - name: test-module\n"
            "    description: A test module\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/module.git\n"
        )
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            registry.add("official", "https://example.com/market.yml")

            # Verify reference file created
            ref_file = market_dir / "official.yml"
            assert ref_file.exists()

            # Verify cache file created
            cache_file = cache_dir / "official.yml"
            assert cache_file.exists()

            # Verify reference content
            marketplace = Marketplace.from_reference(ref_file)
            assert marketplace.name == "official"
            assert marketplace.url == "https://example.com/market.yml"
            assert marketplace.enabled is True

            # Verify cache content
            cached = Marketplace.from_cache(cache_file)
            assert cached.description == "Test catalog"
            assert cached.version == "1.0.0"
            assert len(cached.modules) == 1

    def test_registry_add_duplicate(self, tmp_path, capsys):
        """Adding duplicate marketplace shows warning."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        yaml_content = "name: Test\ndescription: Test\nversion: 1.0.0\nmodules: []\n"
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)

            # Add first time
            registry.add("test", "https://example.com/market.yml")

            # Add second time - should warn
            registry.add("test", "https://example.com/market.yml")

            # Verify warning message was printed
            captured = capsys.readouterr()
            assert "already exists" in captured.out

    def test_registry_add_invalid_yaml(self, tmp_path, capsys):
        """Adding marketplace with invalid YAML shows errors."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        # Has modules but missing version (should fail validation)
        yaml_content = (
            "name: Test\nmodules:\n  - name: test-module\n    description: Test\n"
        )
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            registry.add("invalid", "https://example.com/bad.yml")

            # Verify validation failure message was printed
            captured = capsys.readouterr()
            assert "Validation failed" in captured.out

    def test_registry_add_network_error(self, tmp_path, capsys):
        """Handle network error when adding marketplace."""
        from urllib.error import URLError

        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        with patch(
            "urllib.request.urlopen",
            side_effect=URLError("Connection failed"),
        ):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            registry.add("test", "https://invalid.com/market.yml")

            # Verify error message was printed
            captured = capsys.readouterr()
            assert "Error:" in captured.out


class TestMarketplaceRegistrySearchModule:
    """Tests for MarketplaceRegistry.search_module()."""

    def test_search_module_success(self, marketplace_with_modules):
        """Search module in marketplace successfully."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        result = registry.search_module("git-tools")

        assert result is not None
        module, marketplace_name = result
        assert module["name"] == "git-tools"
        assert module["repository"] == "https://github.com/test/git-tools.git"
        assert marketplace_name == "official"

    def test_search_module_not_found(self, marketplace_with_modules):
        """Module not found in any marketplace."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        result = registry.search_module("nonexistent-module")

        assert result is None

    def test_search_module_disabled_marketplace(self, marketplace_disabled):
        """Skip disabled marketplaces when searching."""
        market_dir = marketplace_disabled["market_dir"]
        cache_dir = marketplace_disabled["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        result = registry.search_module("test-module")

        # Should not find module in disabled marketplace
        assert result is None


class TestMarketplaceRegistryList:
    """Tests for MarketplaceRegistry.list()."""

    def test_list_empty(self, tmp_path, capsys):
        """List when no marketplaces registered."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.list()

        captured = capsys.readouterr()
        assert "No marketplaces registered" in captured.out

    def test_list_with_marketplaces(self, marketplace_with_modules, capsys):
        """List registered marketplaces."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.list()

        captured = capsys.readouterr()
        assert "official" in captured.out
        assert "2" in captured.out  # Module count
        assert "enabled" in captured.out


class TestMarketplaceRegistryShow:
    """Tests for MarketplaceRegistry.show()."""

    def test_show_marketplace_modules(self, marketplace_with_modules, capsys):
        """Show modules in a marketplace."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("official")

        captured = capsys.readouterr()
        # Verify marketplace header
        assert "Official Marketplace" in captured.out
        assert "enabled" in captured.out
        assert "Official catalog" in captured.out
        assert "Version 1.0.0" in captured.out
        # Verify modules listed
        assert "git-tools" in captured.out
        assert "python-utils" in captured.out
        assert "Git utilities" in captured.out
        assert "Python utilities" in captured.out

    def test_show_marketplace_not_found(self, tmp_path, capsys):
        """Show non-existent marketplace shows error."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_show_marketplace_empty(self, tmp_path, capsys):
        """Show marketplace with no modules."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        ref = {"name": "empty", "url": "https://example.com/empty.yml", "enabled": True}
        cache = {
            "name": "Empty Marketplace",
            "description": "No modules here",
            "version": "1.0.0",
            "url": "https://example.com/empty.yml",
            "modules": [],
        }

        with open(market_dir / "empty.yml", "w") as f:
            yaml.dump(ref, f)
        with open(cache_dir / "empty.yml", "w") as f:
            yaml.dump(cache, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("empty")

        captured = capsys.readouterr()
        assert "Empty Marketplace" in captured.out
        assert "No modules in this marketplace" in captured.out

    def test_show_disabled_marketplace(self, marketplace_disabled, capsys):
        """Show disabled marketplace displays disabled status."""
        market_dir = marketplace_disabled["market_dir"]
        cache_dir = marketplace_disabled["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("disabled-market")

        captured = capsys.readouterr()
        assert "disabled" in captured.out

    def test_show_with_tags(self, tmp_path, capsys):
        """Show marketplace displays module tags."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        ref = {
            "name": "tagged",
            "url": "https://example.com/tagged.yml",
            "enabled": True,
        }
        cache = {
            "name": "Tagged Marketplace",
            "version": "1.0.0",
            "url": "https://example.com/tagged.yml",
            "modules": [
                {
                    "name": "tagged-module",
                    "description": "A tagged module",
                    "version": "1.0.0",
                    "repository": "https://github.com/test/tagged.git",
                    "tags": ["cli", "productivity", "git"],
                }
            ],
        }

        with open(market_dir / "tagged.yml", "w") as f:
            yaml.dump(ref, f)
        with open(cache_dir / "tagged.yml", "w") as f:
            yaml.dump(cache, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("tagged")

        captured = capsys.readouterr()
        assert "tagged-module" in captured.out
        assert "cli" in captured.out
        assert "productivity" in captured.out
        assert "git" in captured.out

    def test_show_missing_cache_recovers(self, tmp_path, capsys):
        """Show recovers when cache is missing by fetching from URL."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        # Create only reference file, no cache
        ref = {
            "name": "no-cache",
            "url": "https://example.com/nocache.yml",
            "enabled": True,
        }
        with open(market_dir / "no-cache.yml", "w") as f:
            yaml.dump(ref, f)

        # Mock the URL fetch
        yaml_content = (
            "name: Recovered Marketplace\n"
            "description: Fetched from URL\n"
            "version: 1.0.0\n"
            "modules:\n"
            "  - name: recovered-module\n"
            "    description: A recovered module\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/recovered.git\n"
        )
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            registry.show("no-cache")

        captured = capsys.readouterr()
        # Verify cache recovery message and module content
        assert "Cache missing" in captured.out
        assert "recovered-module" in captured.out
        assert "A recovered module" in captured.out

    def test_show_displays_ref_column_when_modules_have_ref(self, tmp_path, capsys):
        """show() includes Ref column when at least one module has a ref."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        ref_data = {
            "name": "pinned-market",
            "url": "https://example.com/m.yml",
            "enabled": True,
        }
        cache_data = {
            "name": "Pinned Market",
            "description": "Test",
            "version": "1.0.0",
            "url": "https://example.com/m.yml",
            "enabled": True,
            "modules": [
                {
                    "name": "stable-tool",
                    "description": "Stable",
                    "version": "2.0.0",
                    "repository": "https://github.com/org/tool",
                    "ref": "v2.0.0",
                },
                {
                    "name": "plain-tool",
                    "description": "No ref",
                    "version": "1.0.0",
                    "repository": "https://github.com/org/plain",
                },
            ],
        }
        with open(market_dir / "pinned-market.yml", "w") as f:
            yaml.dump(ref_data, f)
        with open(cache_dir / "pinned-market.yml", "w") as f:
            yaml.dump(cache_data, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("pinned-market")

        captured = capsys.readouterr()
        assert "Ref" in captured.out
        assert "v2.0.0" in captured.out
        assert "stable-tool" in captured.out
        assert "plain-tool" in captured.out

    def test_show_hides_ref_column_when_no_refs(self, tmp_path, capsys):
        """show() omits Ref column when no modules have a ref."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        ref_data = {
            "name": "plain-market",
            "url": "https://example.com/m.yml",
            "enabled": True,
        }
        cache_data = {
            "name": "Plain Market",
            "description": "Test",
            "version": "1.0.0",
            "url": "https://example.com/m.yml",
            "enabled": True,
            "modules": [
                {
                    "name": "tool-a",
                    "description": "No ref",
                    "version": "1.0.0",
                    "repository": "https://github.com/org/a",
                },
            ],
        }
        with open(market_dir / "plain-market.yml", "w") as f:
            yaml.dump(ref_data, f)
        with open(cache_dir / "plain-market.yml", "w") as f:
            yaml.dump(cache_data, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.show("plain-market")

        captured = capsys.readouterr()
        assert "Ref" not in captured.out
        assert "tool-a" in captured.out


class TestMarketplaceRegistryEnableDisable:
    """Tests for MarketplaceRegistry enable/disable."""

    def test_enable_marketplace(self, marketplace_disabled, capsys):
        """Enable a disabled marketplace."""
        market_dir = marketplace_disabled["market_dir"]
        cache_dir = marketplace_disabled["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.enable("disabled-market")

        captured = capsys.readouterr()
        assert "enabled" in captured.out

        # Verify enabled status persisted
        from lola.models import Marketplace

        ref_file = market_dir / "disabled-market.yml"
        marketplace = Marketplace.from_reference(ref_file)
        assert marketplace.enabled is True

    def test_disable_marketplace(self, marketplace_with_modules, capsys):
        """Disable an enabled marketplace."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.disable("official")

        captured = capsys.readouterr()
        assert "disabled" in captured.out

        # Verify disabled status persisted
        from lola.models import Marketplace

        ref_file = market_dir / "official.yml"
        marketplace = Marketplace.from_reference(ref_file)
        assert marketplace.enabled is False

    def test_enable_not_found(self, tmp_path, capsys):
        """Enable non-existent marketplace shows error."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.enable("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestMarketplaceRegistryRemove:
    """Tests for MarketplaceRegistry.remove()."""

    def test_remove_marketplace(self, marketplace_with_modules, capsys):
        """Remove a marketplace successfully."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.remove("official")

        captured = capsys.readouterr()
        assert "Removed marketplace" in captured.out

        # Verify files removed
        ref_file = market_dir / "official.yml"
        cache_file = cache_dir / "official.yml"
        assert not ref_file.exists()
        assert not cache_file.exists()

    def test_remove_not_found(self, tmp_path, capsys):
        """Remove non-existent marketplace shows error."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.remove("nonexistent")

        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestMarketplaceRegistrySearch:
    """Tests for MarketplaceRegistry.search()."""

    def test_search_with_results(self, marketplace_with_modules, capsys):
        """Search displays results when matches found."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.search("git")

        captured = capsys.readouterr()
        assert "Found 1 module" in captured.out
        assert "git-tools" in captured.out
        assert "Git utilities" in captured.out

    def test_search_no_results(self, marketplace_with_modules, capsys):
        """Search displays message when no matches."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.search("nonexistent")

        captured = capsys.readouterr()
        assert "No modules found matching 'nonexistent'" in captured.out

    def test_search_no_marketplaces(self, tmp_path, capsys):
        """Search displays message when no marketplaces registered."""
        market_dir = tmp_path / "market"
        cache_dir = tmp_path / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.search("git")

        captured = capsys.readouterr()
        assert "No marketplaces registered" in captured.out
        assert "lola market add" in captured.out


class TestMarketplaceRegistryUpdate:
    """Tests for MarketplaceRegistry update methods."""

    def test_update_one_success(self, marketplace_with_modules, capsys):
        """Update a single marketplace and verify cache changes."""
        from lola.models import Marketplace

        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        # Verify initial cache state
        cache_file = cache_dir / "official.yml"
        initial_marketplace = Marketplace.from_cache(cache_file)
        assert len(initial_marketplace.modules) == 2
        assert initial_marketplace.modules[0]["name"] == "git-tools"

        # Updated YAML with different modules
        yaml_content = (
            "name: Updated Marketplace\n"
            "description: Updated catalog\n"
            "version: 2.0.0\n"
            "modules:\n"
            "  - name: new-module\n"
            "    description: A new module\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/new-module.git\n"
            "  - name: another-module\n"
            "    description: Another new module\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/another-module.git\n"
            "  - name: third-module\n"
            "    description: Third module\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/third-module.git\n"
        )
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            result = registry.update_one("official")

            assert result is True

            captured = capsys.readouterr()
            assert "Updated 'official' with 3 modules" in captured.out

            # Verify cache was updated with new content
            updated_marketplace = Marketplace.from_cache(cache_file)
            assert len(updated_marketplace.modules) == 3
            assert updated_marketplace.modules[0]["name"] == "new-module"
            assert (
                updated_marketplace.modules[0]["repository"]
                == "https://github.com/test/new-module.git"
            )
            assert updated_marketplace.modules[1]["name"] == "another-module"
            assert updated_marketplace.modules[2]["name"] == "third-module"

    def test_update_one_not_found(self, tmp_path, capsys):
        """Update non-existent marketplace returns False."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        result = registry.update_one("nonexistent")

        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_update_one_validation_failure(self, marketplace_with_modules, capsys):
        """Update with invalid data returns False."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        # Missing version field (validation will fail)
        yaml_content = "name: Test\nmodules:\n  - name: test\n    description: Test\n"
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            result = registry.update_one("official")

            assert result is False
            captured = capsys.readouterr()
            assert "Validation failed" in captured.out

    def test_update_all(self, marketplace_with_modules, capsys):
        """Update all marketplaces."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        yaml_content = (
            "name: Updated\n"
            "description: Updated\n"
            "version: 2.0.0\n"
            "modules:\n"
            "  - name: new-module\n"
            "    description: New\n"
            "    version: 1.0.0\n"
            "    repository: https://github.com/test/new.git\n"
        )
        mock_response = mock_open(read_data=yaml_content.encode())()

        with patch("urllib.request.urlopen", return_value=mock_response):
            registry = MarketplaceRegistry(market_dir, cache_dir)
            registry.update()

            captured = capsys.readouterr()
            assert "Updated 1/1 marketplaces" in captured.out

    def test_update_all_empty(self, tmp_path, capsys):
        """Update with no marketplaces registered."""
        market_dir = tmp_path / "market"
        cache_dir = market_dir / "cache"

        registry = MarketplaceRegistry(market_dir, cache_dir)
        registry.update()

        captured = capsys.readouterr()
        assert "No marketplaces registered" in captured.out


class TestMarketplaceRegistrySearchModuleAll:
    """Tests for MarketplaceRegistry.search_module_all()."""

    def test_search_module_all_single_match(self, marketplace_with_modules):
        """Find module in single marketplace."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        matches = registry.search_module_all("git-tools")

        assert len(matches) == 1
        module, marketplace_name = matches[0]
        assert module["name"] == "git-tools"
        assert marketplace_name == "official"

    def test_search_module_all_multiple_matches(self, tmp_path):
        """Find module in multiple marketplaces."""
        market_dir = tmp_path / "market"
        cache_dir = tmp_path / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        # Create two marketplaces with the same module
        for idx, name in enumerate(["market-a", "market-b"]):
            ref = {
                "name": name,
                "url": f"https://example.com/{name}.yml",
                "enabled": True,
            }
            cache = {
                "name": f"Marketplace {name.upper()}",
                "version": "1.0.0",
                "url": f"https://example.com/{name}.yml",
                "modules": [
                    {
                        "name": "shared-module",
                        "description": f"Module from {name}",
                        "version": f"1.{idx}.0",
                        "repository": f"https://github.com/{name}/shared.git",
                    }
                ],
            }

            with open(market_dir / f"{name}.yml", "w") as f:
                yaml.dump(ref, f)
            with open(cache_dir / f"{name}.yml", "w") as f:
                yaml.dump(cache, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        matches = registry.search_module_all("shared-module")

        assert len(matches) == 2
        marketplaces = {m[1] for m in matches}
        assert marketplaces == {"market-a", "market-b"}

    def test_search_module_all_no_matches(self, marketplace_with_modules):
        """Return empty list when module not found."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        matches = registry.search_module_all("nonexistent")

        assert matches == []

    def test_search_module_all_skips_disabled(self, tmp_path):
        """Skip disabled marketplaces."""
        market_dir = tmp_path / "market"
        cache_dir = tmp_path / "cache"
        market_dir.mkdir(parents=True)
        cache_dir.mkdir(parents=True)

        # Create enabled marketplace
        enabled_ref = {
            "name": "enabled",
            "url": "https://example.com/enabled.yml",
            "enabled": True,
        }
        enabled_cache = {
            "name": "Enabled",
            "version": "1.0.0",
            "url": "https://example.com/enabled.yml",
            "modules": [{"name": "test-module", "description": "Test"}],
        }

        # Create disabled marketplace with same module
        disabled_ref = {
            "name": "disabled",
            "url": "https://example.com/disabled.yml",
            "enabled": False,
        }
        disabled_cache = {
            "name": "Disabled",
            "version": "1.0.0",
            "url": "https://example.com/disabled.yml",
            "modules": [{"name": "test-module", "description": "Test"}],
        }

        with open(market_dir / "enabled.yml", "w") as f:
            yaml.dump(enabled_ref, f)
        with open(cache_dir / "enabled.yml", "w") as f:
            yaml.dump(enabled_cache, f)
        with open(market_dir / "disabled.yml", "w") as f:
            yaml.dump(disabled_ref, f)
        with open(cache_dir / "disabled.yml", "w") as f:
            yaml.dump(disabled_cache, f)

        registry = MarketplaceRegistry(market_dir, cache_dir)
        matches = registry.search_module_all("test-module")

        # Should only find in enabled marketplace
        assert len(matches) == 1
        assert matches[0][1] == "enabled"


class TestMarketplaceRegistrySelectMarketplace:
    """Tests for MarketplaceRegistry.select_marketplace()."""

    def test_select_single_match(self, marketplace_with_modules):
        """Return marketplace name when only one match."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        matches = [({"name": "test", "description": "Test"}, "official")]

        result = registry.select_marketplace("test", matches)

        assert result == "official"

    def test_select_no_matches(self, marketplace_with_modules):
        """Return None when no matches."""
        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        result = registry.select_marketplace("test", [])

        assert result is None

    def test_select_multiple_matches_with_version(self, marketplace_with_modules):
        """Prompt user to select when multiple matches — delegates to prompts.select_marketplace."""
        from unittest.mock import patch

        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        matches = [
            (
                {
                    "name": "test",
                    "description": "From market A",
                    "version": "1.0.0",
                },
                "market-a",
            ),
            (
                {
                    "name": "test",
                    "description": "From market B",
                    "version": "2.0.0",
                },
                "market-b",
            ),
        ]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        with patch(
            "lola.market.manager.prompt_select_marketplace", return_value="market-b"
        ) as mock_prompt:
            result = registry.select_marketplace("test", matches, show_version=True)

        assert result == "market-b"
        # Verify display includes marketplace name, version, and description
        call_args = mock_prompt.call_args[0][0]
        assert any(m[1] == "market-a" for m in call_args)
        assert any(m[1] == "market-b" for m in call_args)

    def test_select_multiple_matches_without_version(self, marketplace_with_modules):
        """show_version flag is accepted (backwards-compatible) but ignored by InquirerPy prompt."""
        from unittest.mock import patch

        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        matches = [
            (
                {
                    "name": "test",
                    "description": "From market A",
                    "version": "1.0.0",
                },
                "market-a",
            ),
            (
                {
                    "name": "test",
                    "description": "From market B",
                    "version": "2.0.0",
                },
                "market-b",
            ),
        ]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        with patch(
            "lola.market.manager.prompt_select_marketplace", return_value="market-a"
        ):
            result = registry.select_marketplace("test", matches, show_version=False)

        assert result == "market-a"

    def test_select_multiple_matches_cancelled(self, marketplace_with_modules):
        """User cancels the interactive prompt → return None."""
        from unittest.mock import patch

        market_dir = marketplace_with_modules["market_dir"]
        cache_dir = marketplace_with_modules["cache_dir"]

        matches = [
            ({"name": "test", "description": "desc", "version": "1.0"}, "market-a"),
            ({"name": "test", "description": "desc", "version": "1.0"}, "market-b"),
        ]

        registry = MarketplaceRegistry(market_dir, cache_dir)
        with patch("lola.market.manager.prompt_select_marketplace", return_value=None):
            result = registry.select_marketplace("test", matches)

        assert result is None


class TestParseRefSuffix:
    """Tests for parse_ref_suffix()."""

    def test_no_ref(self):
        """Module name without @ returns (name, None)."""
        name, ref = parse_ref_suffix("my-module")
        assert name == "my-module"
        assert ref is None

    def test_tag_ref(self):
        """module@v1.0.0 splits correctly."""
        name, ref = parse_ref_suffix("my-module@v1.0.0")
        assert name == "my-module"
        assert ref == "v1.0.0"

    def test_branch_ref(self):
        """module@develop splits correctly."""
        name, ref = parse_ref_suffix("tools@develop")
        assert name == "tools"
        assert ref == "develop"

    def test_commit_sha_ref(self):
        """module@sha splits on rightmost @ so full SHA is preserved."""
        name, ref = parse_ref_suffix("tools@abc1234")
        assert name == "tools"
        assert ref == "abc1234"

    def test_empty_ref_after_at(self):
        """module@ with empty suffix returns None for ref."""
        name, ref = parse_ref_suffix("my-module@")
        assert name == "my-module"
        assert ref is None

    def test_rsplit_takes_rightmost_at(self):
        """When multiple @ present, splits on the rightmost one."""
        name, ref = parse_ref_suffix("my-module@v1@v2")
        assert name == "my-module@v1"
        assert ref == "v2"


class TestMarketplaceValidateRef:
    """Tests for ref field validation in Marketplace.validate()."""

    def _make_marketplace(self, modules):
        return Marketplace(
            name="Test",
            url="https://example.com/market.yml",
            version="1.0.0",
            modules=modules,
        )

    def test_validate_accepts_valid_refs(self):
        """Tags, branches, and SHAs are all accepted."""
        for ref in ("v1.0.0", "main", "abc1234def5678"):
            market = self._make_marketplace(
                [
                    {
                        "name": "mod",
                        "description": "d",
                        "version": "1.0",
                        "repository": "https://r.git",
                        "ref": ref,
                    }
                ]
            )
            ok, errors = market.validate()
            assert ok, f"Expected valid for ref={ref!r}, got errors: {errors}"

    def test_validate_rejects_empty_ref(self):
        """ref: '' must produce a validation error."""
        market = self._make_marketplace(
            [
                {
                    "name": "mod",
                    "description": "d",
                    "version": "1.0",
                    "repository": "https://r.git",
                    "ref": "",
                }
            ]
        )
        ok, errors = market.validate()
        assert not ok
        assert any("'ref' must be a non-empty string" in e for e in errors)

    def test_validate_rejects_whitespace_only_ref(self):
        """ref: '   ' (only spaces) must produce a validation error."""
        market = self._make_marketplace(
            [
                {
                    "name": "mod",
                    "description": "d",
                    "version": "1.0",
                    "repository": "https://r.git",
                    "ref": "   ",
                }
            ]
        )
        ok, errors = market.validate()
        assert not ok
        assert any("'ref' must be a non-empty string" in e for e in errors)

    def test_validate_rejects_control_char_ref(self):
        """ref containing control characters must produce a validation error."""
        market = self._make_marketplace(
            [
                {
                    "name": "mod",
                    "description": "d",
                    "version": "1.0",
                    "repository": "https://r.git",
                    "ref": "v1\x00bad",
                }
            ]
        )
        ok, errors = market.validate()
        assert not ok
        assert any("control characters" in e for e in errors)

    def test_validate_none_ref_is_allowed(self):
        """Omitting ref entirely (None) is fine — ref is optional."""
        market = self._make_marketplace(
            [
                {
                    "name": "mod",
                    "description": "d",
                    "version": "1.0",
                    "repository": "https://r.git",
                }
            ]
        )
        ok, errors = market.validate()
        assert ok, f"Expected valid when ref is absent, got errors: {errors}"
