"""Tests for Module model including hook discovery."""

from lola.models import Module

VALID_SKILL_MD = """---
name: test
description: Test skill
---
# Test Skill
"""


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
    skill_file.write_text(VALID_SKILL_MD)

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
    skill_file.write_text(VALID_SKILL_MD)

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
    skill_file.write_text(VALID_SKILL_MD)

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
    skill_file.write_text(VALID_SKILL_MD)

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
    skill_file.write_text(VALID_SKILL_MD)

    module = Module.from_path(module_dir)
    assert module is not None
    assert module.pre_install_hook == "scripts/setup.sh"
    assert module.post_install_hook == "scripts/cleanup.sh"


def test_module_validate_missing_hook_script(tmp_path):
    """Test that validation fails when hook script doesn't exist."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with non-existent script
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/missing.sh
"""
    )

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(VALID_SKILL_MD)

    module = Module.from_path(module_dir)
    assert module is not None

    is_valid, errors = module.validate()
    assert not is_valid
    assert any("pre-install hook script not found" in err for err in errors)


def test_module_validate_hook_path_traversal(tmp_path):
    """Test that validation fails when hook attempts path traversal.

    Security test: Ensures malicious modules cannot use ../../ patterns
    to execute scripts outside the module directory boundary.
    """
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with path traversal attempt
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: ../../etc/passwd
"""
    )

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(VALID_SKILL_MD)

    # Create malicious file outside module to test security boundary
    # Path ../../etc/passwd from module_dir resolves to tmp_path.parent / "etc" / "passwd"
    # This simulates an attacker trying to execute a script outside the module directory
    passwd_file = tmp_path.parent / "etc" / "passwd"
    passwd_file.parent.mkdir(parents=True, exist_ok=True)
    passwd_file.write_text("#!/bin/bash\necho 'malicious script'")

    module = Module.from_path(module_dir)
    assert module is not None

    is_valid, errors = module.validate()
    assert not is_valid
    assert any("pre-install hook outside module directory" in err for err in errors)


def test_module_validate_valid_hooks(tmp_path):
    """Test that validation passes when hooks exist and are valid."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with valid hooks
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/pre.sh
  post-install: scripts/post.sh
"""
    )

    # Create the hook scripts
    scripts_dir = module_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "pre.sh").write_text("#!/bin/bash\necho 'pre-install'")
    (scripts_dir / "post.sh").write_text("#!/bin/bash\necho 'post-install'")

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(VALID_SKILL_MD)

    module = Module.from_path(module_dir)
    assert module is not None

    is_valid, errors = module.validate()
    assert is_valid
    assert len(errors) == 0


def test_module_validate_partial_missing_hook(tmp_path):
    """Test validation when one hook exists and one doesn't."""
    module_dir = tmp_path / "test-module"
    module_dir.mkdir()

    # Create lola.yaml with two hooks
    lola_yaml = module_dir / "lola.yaml"
    lola_yaml.write_text(
        """hooks:
  pre-install: scripts/pre.sh
  post-install: scripts/missing.sh
"""
    )

    # Create only the pre-install script
    scripts_dir = module_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "pre.sh").write_text("#!/bin/bash\necho 'pre-install'")

    # Create a minimal skill so module is valid
    skills_dir = module_dir / "skills" / "test-skill"
    skills_dir.mkdir(parents=True)
    skill_file = skills_dir / "SKILL.md"
    skill_file.write_text(VALID_SKILL_MD)

    module = Module.from_path(module_dir)
    assert module is not None

    is_valid, errors = module.validate()
    assert not is_valid
    assert any("post-install hook script not found" in err for err in errors)
    assert not any("pre-install" in err for err in errors)
