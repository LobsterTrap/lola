"""Tests for _skill_source_dir() function with single skill support."""

from lola.targets.base import _skill_source_dir


class TestSkillSourceDir:
    """Tests for _skill_source_dir() with single skill and bundle patterns."""

    def test_single_skill_at_root(self, tmp_path):
        """_skill_source_dir() returns content_path for single skill at root."""
        module_dir = tmp_path / "single-skill"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: test-skill
description: Test
---
""")

        source_dir = _skill_source_dir(module_dir, "test-skill")
        assert source_dir == module_dir

    def test_single_skill_in_module_subdirectory(self, tmp_path):
        """_skill_source_dir() returns module/ for single skill in module/."""
        module_dir = tmp_path / "wrapped-skill"
        module_dir.mkdir()

        content_dir = module_dir / "module"
        content_dir.mkdir()
        (content_dir / "SKILL.md").write_text("""---
name: wrapped
description: Test
---
""")

        source_dir = _skill_source_dir(module_dir, "wrapped")
        assert source_dir == content_dir

    def test_skill_bundle_returns_skills_subdirectory(self, tmp_path):
        """_skill_source_dir() returns skills/skill-name for bundle."""
        module_dir = tmp_path / "bundle-module"
        module_dir.mkdir()

        skills_dir = module_dir / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Bundle skill
---
""")

        source_dir = _skill_source_dir(module_dir, "my-skill")
        assert source_dir == skill_dir

    def test_skill_bundle_in_module_subdirectory(self, tmp_path):
        """_skill_source_dir() handles bundle in module/ subdirectory."""
        module_dir = tmp_path / "wrapped-bundle"
        module_dir.mkdir()

        content_dir = module_dir / "module"
        content_dir.mkdir()

        skills_dir = content_dir / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "bundle-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Test
---
""")

        source_dir = _skill_source_dir(module_dir, "bundle-skill")
        assert source_dir == skill_dir

    def test_legacy_fallback(self, tmp_path):
        """_skill_source_dir() falls back to module_path/skill_name for legacy."""
        module_dir = tmp_path / "legacy-module"
        module_dir.mkdir()

        # No SKILL.md at root, no skills/ subdirectory
        # Should fall back to legacy structure
        source_dir = _skill_source_dir(module_dir, "legacy-skill")
        assert source_dir == module_dir / "legacy-skill"
