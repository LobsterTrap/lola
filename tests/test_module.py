"""Tests for Module model including hook discovery."""

from lola.models import Module


def test_module_with_lola_yaml_hooks(tmp_path):
    """Test that hooks are discovered from lola.yaml."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with hooks
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/pre.sh
  post-install: scripts/post.sh
"""
    )

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\n# Test")

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook == "scripts/pre.sh"
    assert module.post_install_hook == "scripts/post.sh"


def test_module_without_lola_yaml(tmp_path):
    """Test that modules without lola.yaml have None hooks."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\n# Test")

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook is None
    assert module.post_install_hook is None


def test_module_with_partial_hooks(tmp_path):
    """Test that only specified hooks are set."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with only pre-install hook
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/check.sh
"""
    )

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\n# Test")

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook == "scripts/check.sh"
    assert module.post_install_hook is None


def test_module_with_malformed_lola_yaml(tmp_path):
    """Test that malformed lola.yaml is ignored."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create malformed lola.yaml
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text("invalid: yaml: content: [")

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\n# Test")

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook is None
    assert module.post_install_hook is None


def test_module_with_module_subdir_hooks(tmp_path):
    """Test that hooks work with module/ subdirectory."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create module/ subdirectory
    content_dir = module_dir / "module"
    content_dir.mkdir()

    # Create lola.yaml in module/ subdirectory
    lola_yaml = content_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/setup.sh
  post-install: scripts/cleanup.sh
"""
    )

    # Create a minimal skill so module is valid
    skills_dir = content_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text("---\nname: test\n---\n# Test")

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook == "scripts/setup.sh"
    assert module.post_install_hook == "scripts/cleanup.sh"
