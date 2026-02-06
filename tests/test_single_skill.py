"""Tests for single skill (agentskills.io standard) functionality."""

from lola.models import Module


class TestSingleSkillDetection:
    """Tests for single skill detection at module root."""

    def test_single_skill_with_name_from_frontmatter(self, tmp_path):
        """Single skill uses name from SKILL.md frontmatter."""
        module_dir = tmp_path / "test-module"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: my-awesome-skill
description: Test single skill
---

Skill content.
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.name == "test-module"
        assert module.skills == ["my-awesome-skill"]
        assert module.is_single_skill is True
        assert module.content_path == module_dir

    def test_single_skill_fallback_to_module_name(self, tmp_path):
        """Single skill without name field uses module directory name."""
        module_dir = tmp_path / "fallback-skill"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
description: Skill without name field
---

Content.
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["fallback-skill"]
        assert module.is_single_skill is True

    def test_single_skill_name_not_string(self, tmp_path):
        """Single skill with non-string name falls back to module name."""
        module_dir = tmp_path / "weird-name"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: 123
description: Name is not a string
---

Content.
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["weird-name"]
        assert module.is_single_skill is True

    def test_single_skill_empty_name(self, tmp_path):
        """Single skill with empty name falls back to module name."""
        module_dir = tmp_path / "empty-name"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: ""
description: Empty name field
---

Content.
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["empty-name"]
        assert module.is_single_skill is True


class TestSingleSkillPaths:
    """Tests for single skill path resolution."""

    def test_get_skill_paths_returns_content_path(self, tmp_path):
        """get_skill_paths() returns content_path for single skill."""
        module_dir = tmp_path / "single-skill"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: test
description: Test
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        paths = module.get_skill_paths()
        assert len(paths) == 1
        assert paths[0] == module_dir

    def test_skills_root_dir_returns_content_path(self, tmp_path):
        """_skills_root_dir() returns content_path for single skill."""
        module_dir = tmp_path / "single-skill"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: test
description: Test
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module._skills_root_dir() == module_dir

    def test_single_skill_in_module_subdirectory(self, tmp_path):
        """Single skill works with module/ subdirectory structure."""
        module_dir = tmp_path / "wrapped-skill"
        module_dir.mkdir()

        content_dir = module_dir / "module"
        content_dir.mkdir()
        (content_dir / "SKILL.md").write_text("""---
name: wrapped
description: Single skill in module/ subdirectory
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["wrapped"]
        assert module.is_single_skill is True
        assert module.content_path == content_dir
        assert module.uses_module_subdir is True

        # Verify paths are correct
        paths = module.get_skill_paths()
        assert len(paths) == 1
        assert paths[0] == content_dir


class TestSingleSkillValidation:
    """Tests for single skill validation."""

    def test_single_skill_validates_successfully(self, tmp_path):
        """Valid single skill passes validation."""
        module_dir = tmp_path / "valid-single"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: valid-skill
description: Valid single skill
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        is_valid, errors = module.validate()
        assert is_valid
        assert errors == []

    def test_single_skill_validation_missing_description(self, tmp_path):
        """Single skill without description fails validation."""
        module_dir = tmp_path / "invalid-single"
        module_dir.mkdir()
        (module_dir / "SKILL.md").write_text("""---
name: invalid-skill
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        is_valid, errors = module.validate()
        assert not is_valid
        assert len(errors) > 0
        assert "description" in errors[0].lower()


class TestSkillBundlePrecedence:
    """Tests for skill bundle vs single skill precedence."""

    def test_skill_bundle_takes_precedence_over_root_skill(self, tmp_path):
        """Skill bundle detected even if SKILL.md exists at root."""
        module_dir = tmp_path / "bundle-module"
        module_dir.mkdir()

        # Create SKILL.md at root (should be ignored)
        (module_dir / "SKILL.md").write_text("""---
name: root-skill
description: Should be ignored when bundle exists
---
""")

        # Create skill bundle
        skills_dir = module_dir / "skills"
        skills_dir.mkdir()
        skill_dir = skills_dir / "bundle-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
description: Bundle skill
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["bundle-skill"]
        assert module.is_single_skill is False

    def test_empty_skills_dir_falls_back_to_single_skill(self, tmp_path):
        """Empty skills/ directory falls back to single skill at root."""
        module_dir = tmp_path / "fallback-module"
        module_dir.mkdir()

        # Create empty skills/ directory
        skills_dir = module_dir / "skills"
        skills_dir.mkdir()

        # Create SKILL.md at root
        (module_dir / "SKILL.md").write_text("""---
name: fallback
description: Single skill after empty bundle
---
""")

        module = Module.from_path(module_dir)
        assert module is not None
        assert module.skills == ["fallback"]
        assert module.is_single_skill is True


class TestSingleSkillWithCustomContentPath:
    """Tests for single skill with custom content directory."""

    def test_single_skill_with_custom_content_dirname(self, tmp_path):
        """Single skill works with custom content dirname."""
        module_dir = tmp_path / "custom-module"
        module_dir.mkdir()

        custom_dir = module_dir / "custom-content"
        custom_dir.mkdir()
        (custom_dir / "SKILL.md").write_text("""---
name: custom-skill
description: Single skill in custom directory
---
""")

        module = Module.from_path(module_dir, content_dirname="custom-content")
        assert module is not None
        assert module.skills == ["custom-skill"]
        assert module.is_single_skill is True
        assert module.content_path == custom_dir

    def test_single_skill_with_root_content_dirname(self, tmp_path):
        """Single skill works with root content dirname (/)."""
        module_dir = tmp_path / "root-module"
        module_dir.mkdir()

        (module_dir / "SKILL.md").write_text("""---
name: root-skill
description: Single skill at root with explicit flag
---
""")

        module = Module.from_path(module_dir, content_dirname="/")
        assert module is not None
        assert module.skills == ["root-skill"]
        assert module.is_single_skill is True
        assert module.content_path == module_dir
